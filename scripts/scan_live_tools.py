"""One-time live-API scan for every registered MCP tool.

Invokes each of the 30 tools against the *real* upstream MLB Stats API /
pybaseball services (no mocks) and records pass/fail + the top-level return
type. The type column is what surfaces bare (non-dict) return values, which
violate the MCP spec's requirement that structured tool output be a dict.

Run from the repo root with the project venv active:

    python scripts/scan_live_tools.py

A JSON report is written to scripts/live_scan_report.json and a human-readable
summary is printed to stdout. This is a manual verification pass, not part of
the automated (mocked) test suite.
"""

import json
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

# Make repo root importable so `import mlb_api` / `import generic_api` work.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import generic_api  # noqa: E402
import mlb_api  # noqa: E402


def _type_name(obj: Any) -> str:
    """Return a short human-readable type name for a tool result."""
    if isinstance(obj, list):
        inner = _type_name(obj[0]) if obj else "empty"
        return f"list[{inner}]"
    if isinstance(obj, dict):
        keys = ", ".join(list(obj.keys())[:5])
        return f"dict({{{keys}}})"
    return type(obj).__name__


def _serialize(obj: Any) -> Any:
    """Best-effort conversion of a tool result to JSON-serializable data."""
    if isinstance(obj, list):
        return [_serialize(x) for x in obj[:3]]  # cap to 3 sample items
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in list(obj.items())[:10]}
    if hasattr(obj, "model_dump"):
        try:
            return _serialize(obj.model_dump(by_alias=True))
        except Exception:
            return f"<{type(obj).__name__}>"
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return f"<{type(obj).__name__}>"


def main() -> int:
    # Register tools into a fake mcp that captures the decorated functions.
    captured: dict[str, Any] = {}

    def tool_decorator(*args, **kwargs):
        def wrapper(func):
            captured[func.__name__] = func
            return func

        return wrapper

    mcp = MagicMock()
    mcp.tool = tool_decorator
    mlb_api.setup_mlb_tools(mcp)
    generic_api.setup_generic_tools(mcp)

    # Pick a recent date known to have games (use yesterday/last week to be safe).
    today = datetime.now().date()
    recent = today - timedelta(days=2)
    recent_str = recent.strftime("%Y-%m-%d")
    # A small known-good window for schedule/statcast scans.
    start = (recent - timedelta(days=3)).strftime("%Y-%m-%d")
    end = recent_str
    # Statcast data is ingested with a delay, so use a window a few weeks back
    # to avoid spurious "no data" failures from upstream lag rather than bugs.
    statcast_end = (today - timedelta(days=14)).strftime("%Y-%m-%d")
    statcast_start = (today - timedelta(days=21)).strftime("%Y-%m-%d")

    # Representative arguments for each tool. Keyed by tool name.
    # These target real, stable entities: Yankees (team 147), Aaron Judge
    # (player 592450), a known recent game (looked up at runtime below).
    invokes: dict[str, dict] = {
        # --- mlb_api.py (28 tools) ---
        "get_mlb_standings": {"season": 2024},
        "get_mlb_schedule": {"start_date": start, "end_date": end},
        "get_mlb_team_info": {"team": "147"},
        "get_mlb_player_info": {"player_id": 592450},  # Aaron Judge
        "get_mlb_boxscore": {},  # filled in after schedule lookup
        "get_multiple_mlb_player_stats": {
            "player_ids": "592450",  # Aaron Judge
            "group": "hitting",
            "type": "season",
            "season": 2024,
        },
        "get_mlb_sabermetrics": {
            "player_ids": "592450",
            "season": 2024,
            "stat_name": "war",
        },
        "get_mlb_game_highlights": {},  # filled in after schedule lookup
        "get_mlb_game_pace": {"season": 2024},
        "get_mlb_game_scoring_plays": {},  # filled in after schedule lookup
        "get_mlb_linescore": {},  # filled in after schedule lookup
        "get_mlb_roster": {"team": "147", "season": "2024"},
        "get_mlb_search_players": {"fullname": "Judge"},
        "get_mlb_players": {"sport_id": 1, "season": 2024},
        "get_mlb_draft": {"year_id": 2024},
        "get_mlb_awards": {"award_id": "MVP"},  # award_id is typed int in tool but lib takes str
        "get_mlb_search_teams": {"team_name": "Yankees"},
        "get_mlb_teams": {"sport_id": 1, "season": 2024},
        "get_mlb_game_lineup": {},  # filled in after schedule lookup
        "get_statcast_pitcher": {  # Gerrit Cole 543037
            "player_id": 543037,
            "start_date": statcast_start,
            "end_date": statcast_end,
        },
        "get_statcast_batter": {
            "player_id": 592450,  # Aaron Judge
            "start_date": statcast_start,
            "end_date": statcast_end,
        },
        "get_statcast_team": {
            "team": "Yankees",
            "start_date": statcast_start,
            "end_date": statcast_end,
            "fields": ["launch_speed", "launch_angle"],
        },
        # --- generic_api.py (2 tools) ---
        "get_current_date": {},
        "get_current_time": {},
    }

    # Resolve a real recent game_id from the schedule to feed the game tools.
    # The Schedule model stores games under `dates[].games[]` and each game's
    # id lives on the `game_pk` attribute (snake_case) — not `games`/`gamepk`.
    game_id = None
    try:
        sched_tool = captured.get("get_mlb_schedule")
        if sched_tool:
            sched_res = sched_tool(start_date=start, end_date=end)
            schedule = sched_res.get("schedule") if isinstance(sched_res, dict) else None
            if schedule and getattr(schedule, "dates", None):
                for date_entry in schedule.dates:
                    for game in getattr(date_entry, "games", []) or []:
                        game_id = getattr(game, "game_pk", None)
                        if game_id:
                            break
                    if game_id:
                        break
    except Exception:
        pass
    if game_id:
        for k in [
            "get_mlb_boxscore",
            "get_mlb_game_highlights",
            "get_mlb_game_scoring_plays",
            "get_mlb_linescore",
            "get_mlb_game_lineup",
        ]:
            invokes.setdefault(k, {})["game_id"] = game_id

    results: list[dict] = []
    # Run in a stable, readable order matching the source file.
    order = [
        "get_mlb_standings",
        "get_mlb_schedule",
        "get_mlb_team_info",
        "get_mlb_player_info",
        "get_mlb_boxscore",
        "get_multiple_mlb_player_stats",
        "get_mlb_sabermetrics",
        "get_mlb_game_highlights",
        "get_mlb_game_pace",
        "get_mlb_game_scoring_plays",
        "get_mlb_linescore",
        "get_mlb_roster",
        "get_mlb_search_players",
        "get_mlb_players",
        "get_mlb_draft",
        "get_mlb_awards",
        "get_mlb_search_teams",
        "get_mlb_teams",
        "get_mlb_game_lineup",
        "get_statcast_pitcher",
        "get_statcast_batter",
        "get_statcast_team",
        "get_current_date",
        "get_current_time",
    ]

    for name in order:
        tool = captured.get(name)
        entry: dict[str, Any] = {"tool": name, "status": "MISSING"}
        if tool is None:
            results.append(entry)
            continue
        kwargs = invokes.get(name, {})
        entry["args"] = {k: v for k, v in kwargs.items() if k != "game_id"} or (
            {"game_id": kwargs["game_id"]} if "game_id" in kwargs else {}
        )
        if "game_id" in kwargs:
            entry["args"]["game_id"] = kwargs["game_id"]
        try:
            result = tool(**kwargs)
        except Exception as exc:  # scan must survive any tool failure
            entry["status"] = "FAIL_EXCEPTION"
            entry["error"] = f"{type(exc).__name__}: {exc}"
            entry["traceback"] = traceback.format_exc().splitlines()[-3:]
            results.append(entry)
            continue

        entry["return_type"] = _type_name(result)
        entry["sample"] = _serialize(result)
        # Determine pass/fail. An "error" key in a dict result = failure.
        if isinstance(result, dict) and "error" in result:
            entry["status"] = "FAIL_ERROR"
            entry["error"] = str(result["error"])[:300]
        elif result is None or (isinstance(result, (list, dict, str)) and len(result) == 0):
            entry["status"] = "FAIL_EMPTY"
            entry["error"] = "empty result"
        else:
            entry["status"] = "PASS"
        results.append(entry)

    # Write report.
    report_path = ROOT / "scripts" / "live_scan_report.json"
    report_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")

    # Print summary table.
    print(f"\n{'TOOL':<32} {'STATUS':<16} {'RETURN TYPE'}")
    print("-" * 80)
    passed = failed = 0
    for r in results:
        status = r["status"]
        if status == "PASS":
            passed += 1
        else:
            failed += 1
        print(f"{r['tool']:<32} {status:<16} {r.get('return_type', '-')}")
    print("-" * 80)
    print(f"{passed} passed, {failed} failed, {len(results)} total")
    print(f"Full report: {report_path}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
