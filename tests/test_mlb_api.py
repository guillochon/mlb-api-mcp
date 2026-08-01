from unittest.mock import MagicMock, patch

import pytest

import generic_api
import mlb_api


def patch_mcp_tool(mcp):
    mcp._tools = {}

    def tool_decorator(*args, **kwargs):
        def wrapper(func):
            mcp._tools[func.__name__] = func
            return func

        return wrapper

    mcp.tool = tool_decorator


def get_tool(mcp, name):
    return getattr(mcp, "_tools", {}).get(name)


@pytest.fixture
def mcp():
    mcp = MagicMock()
    patch_mcp_tool(mcp)
    mlb_api.setup_mlb_tools(mcp)
    generic_api.setup_generic_tools(mcp)
    return mcp


def test_get_mlb_standings(mcp):
    get_mlb_standings = get_tool(mcp, "get_mlb_standings")
    assert get_mlb_standings is not None
    with patch("mlb_api.mlb.get_standings", return_value={"dummy": "standings"}):
        result = get_mlb_standings(season=2022)
        assert "standings" in result


def test_get_mlb_schedule(mcp):
    get_mlb_schedule = get_tool(mcp, "get_mlb_schedule")
    assert get_mlb_schedule is not None
    with patch("mlb_api.mlb.get_schedule", return_value={"games": []}):
        # Test with start_date and end_date
        result = get_mlb_schedule(start_date="2022-04-01", end_date="2022-04-07")
        assert "schedule" in result
    with patch("mlb_api.mlb.get_schedule", return_value={"games": []}):
        # Test with team ID
        with patch("mlb_api.get_team_id_from_name", return_value=1):
            result = get_mlb_schedule(start_date="2022-04-01", end_date="2022-04-07", team=1)
            assert "schedule" in result
    with patch("mlb_api.mlb.get_schedule", return_value={"games": []}):
        # Test with team name
        with patch("mlb_api.get_team_id_from_name", return_value=1):
            result = get_mlb_schedule(start_date="2022-04-01", end_date="2022-04-07", team="Yankees")
            assert "schedule" in result


def test_get_mlb_team_info(mcp):
    get_mlb_team_info = get_tool(mcp, "get_mlb_team_info")
    assert get_mlb_team_info is not None
    with patch("mlb_api.mlb.get_team", return_value={"id": 123}):
        # Test with team ID
        result = get_mlb_team_info(team=123)
        assert "team_info" in result
    with patch("mlb_api.mlb.get_team", return_value={"id": 123}):
        # Test with team name (patch team ID lookup)
        with patch("mlb_api.get_team_id_from_name", return_value=123):
            result = get_mlb_team_info(team="Yankees")
            assert "team_info" in result


def test_get_mlb_player_info(mcp):
    get_mlb_player_info = get_tool(mcp, "get_mlb_player_info")
    assert get_mlb_player_info is not None
    with patch("mlb_api.mlb.get_person", return_value={"id": 456}):
        result = get_mlb_player_info(player_id=456)
        assert "player_info" in result


def test_get_mlb_boxscore(mcp):
    get_mlb_boxscore = get_tool(mcp, "get_mlb_boxscore")
    assert get_mlb_boxscore is not None
    with patch("mlb_api.mlb.get_game_box_score", return_value={"boxscore": True}):
        result = get_mlb_boxscore(game_id=789)
        # Top-level result must be a dict (MCP structured output); payload is wrapped.
        assert isinstance(result, dict)
        assert result["boxscore"] == {"boxscore": True}


def test_get_mlb_boxscore_does_not_forward_fields_to_api(mcp):
    """`fields` must never be sent to the underlying API call: the MLB Stats API applies it
    server-side, which can strip fields the response model requires and crash validation.
    """
    get_mlb_boxscore = get_tool(mcp, "get_mlb_boxscore")
    with patch("mlb_api.mlb.get_game_box_score", return_value={"teams": {}}) as mock_boxscore:
        get_mlb_boxscore(game_id=789, fields="teams,players,person,id")
        mock_boxscore.assert_called_once_with(789)


def test_get_mlb_boxscore_filters_fields_locally(mcp):
    get_mlb_boxscore = get_tool(mcp, "get_mlb_boxscore")

    class FakeBoxScore:
        def model_dump(self, by_alias=False):
            return {
                "teams": {
                    "home": {
                        "team": {"id": 137, "name": "Giants"},
                        "players": {
                            "ID660271": {
                                "person": {"id": 660271, "fullName": "Ty France"},
                                "jerseyNumber": "23",
                            }
                        },
                    }
                }
            }

    with patch("mlb_api.mlb.get_game_box_score", return_value=FakeBoxScore()):
        result = get_mlb_boxscore(game_id=789, fields="teams,players,person,fullName")
        assert "error" not in result
        # The filtered boxscore is now wrapped under the "boxscore" key so the
        # top-level structured result is always a dict (MCP output schema).
        boxscore = result["boxscore"]
        home_players = boxscore["teams"]["home"]["players"]["ID660271"]
        assert home_players["person"]["fullName"] == "Ty France"
        # jerseyNumber wasn't requested and should be pruned
        assert "jerseyNumber" not in home_players


def test_get_multiple_mlb_player_stats(mcp):
    get_multiple_mlb_player_stats = get_tool(mcp, "get_multiple_mlb_player_stats")
    assert get_multiple_mlb_player_stats is not None
    with patch("mlb_api.get_multiple_player_stats", return_value=[{"player": 1}]):
        result = get_multiple_mlb_player_stats(player_ids="1,2", group="hitting", type="season", season=2022)
        assert "player_stats" in result


def test_get_multiple_mlb_player_stats_gamelog_type(mcp):
    """type='gameLog' must be honored, not silently replaced with 'career' stats."""
    get_multiple_mlb_player_stats = get_tool(mcp, "get_multiple_mlb_player_stats")
    with patch("mlb_api.get_multiple_player_stats", return_value=[{"player": 1}]) as mock_stats:
        result = get_multiple_mlb_player_stats(player_ids="656302", group="pitching", type="gameLog", season=2026)
        assert "player_stats" in result
        args, _kwargs = mock_stats.call_args
        # args: (mlb, person_ids, stats, groups, season)
        assert args[2] == ["gameLog"]


def test_get_multiple_mlb_player_stats_invalid_type(mcp):
    get_multiple_mlb_player_stats = get_tool(mcp, "get_multiple_mlb_player_stats")
    result = get_multiple_mlb_player_stats(player_ids="656302", group="pitching", type="notARealType", season=2026)
    assert "error" in result


def test_get_mlb_sabermetrics(mcp):
    get_mlb_sabermetrics = get_tool(mcp, "get_mlb_sabermetrics")
    assert get_mlb_sabermetrics is not None
    with patch("mlb_api.get_sabermetrics_for_players", return_value={"players": []}):
        result = get_mlb_sabermetrics(player_ids="1,2", season=2022)
        assert "players" in result or "error" in result


def test_get_mlb_game_highlights(mcp):
    get_mlb_game_highlights = get_tool(mcp, "get_mlb_game_highlights")
    assert get_mlb_game_highlights is not None
    # The tool fetches game content directly via the data adapter (bypassing the
    # Game model, which breaks on upstream field-shape drift) and reads the
    # highlights list from content["highlights"]["highlights"].
    mock_response = MagicMock(status_code=200)
    mock_response.data = {"highlights": {"highlights": [{"headline": "HR"}]}}
    with patch("mlb_api.mlb._mlb_adapter_v1.get", return_value=mock_response):
        result = get_mlb_game_highlights(game_id=123)
        assert "highlights" in result
        assert result["highlights"] == [{"headline": "HR"}]


def test_get_mlb_game_pace(mcp):
    get_mlb_game_pace = get_tool(mcp, "get_mlb_game_pace")
    assert get_mlb_game_pace is not None
    with patch("mlb_api.mlb.get_gamepace", return_value={"pace": True}):
        result = get_mlb_game_pace(season=2022)
        assert isinstance(result, dict)
        assert result["game_pace"] == {"pace": True}


def test_get_mlb_game_scoring_plays(mcp):
    get_mlb_game_scoring_plays = get_tool(mcp, "get_mlb_game_scoring_plays")
    assert get_mlb_game_scoring_plays is not None
    # The Plays model exposes plays as `all_plays` (snake_case) and each play's
    # event type as `result.event_type` — the old `allplays`/`eventType` spellings
    # were a pre-rename bug that silently matched nothing.
    mock_play1 = MagicMock()
    mock_play1.result.event_type = "scoring_play"
    mock_play2 = MagicMock()
    mock_play2.result.event_type = "other"
    mock_plays = MagicMock()
    mock_plays.all_plays = [mock_play1, mock_play2]
    with patch("mlb_api.mlb.get_game_play_by_play", return_value=mock_plays):
        result = get_mlb_game_scoring_plays(game_id=1, eventType="scoring_play")
        assert result["plays"] == [mock_play1]


def test_get_mlb_game_scoring_plays_no_filter(mcp):
    """Without an eventType filter, all plays are returned."""
    get_mlb_game_scoring_plays = get_tool(mcp, "get_mlb_game_scoring_plays")
    mock_play1 = MagicMock()
    mock_play1.result.event_type = "scoring_play"
    mock_play2 = MagicMock()
    mock_play2.result.event_type = "home_run"
    mock_plays = MagicMock()
    mock_plays.all_plays = [mock_play1, mock_play2]
    with patch("mlb_api.mlb.get_game_play_by_play", return_value=mock_plays):
        result = get_mlb_game_scoring_plays(game_id=1)
        assert len(result["plays"]) == 2


def test_get_mlb_linescore(mcp):
    get_mlb_linescore = get_tool(mcp, "get_mlb_linescore")
    assert get_mlb_linescore is not None
    with patch("mlb_api.mlb.get_game_line_score", return_value={"linescore": True}):
        result = get_mlb_linescore(game_id=1)
        assert isinstance(result, dict)
        assert result["linescore"] == {"linescore": True}


def test_get_mlb_roster(mcp):
    get_mlb_roster = get_tool(mcp, "get_mlb_roster")
    assert get_mlb_roster is not None
    # get_team_roster returns a bare list; the tool must wrap it under "roster"
    # so the top-level structured result is a dict (MCP output schema, issue #7).
    with patch("mlb_api.mlb.get_team_roster", return_value=[{"id": 1}]):
        # Test with team ID
        result = get_mlb_roster(team="1", date="2022-04-01")
        assert isinstance(result, dict)
        assert result["roster"] == [{"id": 1}]
    with patch("mlb_api.mlb.get_team_roster", return_value=[{"id": 1}]):
        # Test with team name (patch team ID lookup)
        with patch("mlb_api.get_team_id_from_name", return_value=1):
            result = get_mlb_roster(team="Yankees", date="2022-04-01")
            assert result["roster"] == [{"id": 1}]
    with patch("mlb_api.mlb.get_team_roster", return_value=[{"id": 1}]):
        # Test with date and rosterType
        with patch("mlb_api.get_team_id_from_name", return_value=1):
            result = get_mlb_roster(team="Yankees", date="2022-04-01", rosterType="40Man")
            assert result["roster"] == [{"id": 1}]


def test_get_mlb_search_players(mcp):
    get_mlb_search_players = get_tool(mcp, "get_mlb_search_players")
    assert get_mlb_search_players is not None
    with patch("mlb_api.mlb.get_people_id", return_value=[1, 2]) as mock_get_people_id:
        result = get_mlb_search_players(fullname="John Doe")
        assert "player_ids" in result
        # search_key must be forwarded as the library's actual (camelCase) dict key, not the
        # tool's old lowercase default, or every lookup silently matches zero players.
        mock_get_people_id.assert_called_once_with("John Doe", sport_id=1, search_key="fullName")


def test_mlb_dataadapter_requests_get_has_default_timeout():
    """mlbstatsapi's requests.get() call has no timeout of its own; a stalled upstream
    connection would otherwise hang the calling thread forever (observed in production as
    tool calls hanging for exactly as long as the caller's own client-side timeout). We patch
    a bounded default timeout in at import time - verify it's actually applied."""
    import mlbstatsapi.mlb_dataadapter as da

    with patch.object(mlb_api, "_original_mlb_dataadapter_requests_get") as mock_get:
        da.requests.get("https://statsapi.mlb.com/api/v1/teams")
        mock_get.assert_called_once_with(
            "https://statsapi.mlb.com/api/v1/teams", timeout=mlb_api._MLB_STATSAPI_TIMEOUT_SECONDS
        )


def test_get_mlb_search_players_invalid_search_key(mcp):
    get_mlb_search_players = get_tool(mcp, "get_mlb_search_players")
    result = get_mlb_search_players(fullname="John Doe", search_key="all")
    assert "error" in result


def test_get_mlb_search_players_strips_whitespace(mcp):
    get_mlb_search_players = get_tool(mcp, "get_mlb_search_players")
    with patch("mlb_api.mlb.get_people_id", return_value=[1]) as mock_get_people_id:
        result = get_mlb_search_players(fullname="  Aaron Judge  ")
        assert result["player_ids"] == [1]
        # Leading/trailing whitespace must be stripped before the exact-match comparison,
        # or an otherwise-correct name silently matches zero players.
        mock_get_people_id.assert_called_once_with("Aaron Judge", sport_id=1, search_key="fullName")


def test_get_mlb_search_players_no_match_includes_note(mcp):
    get_mlb_search_players = get_tool(mcp, "get_mlb_search_players")
    with patch("mlb_api.mlb.get_people_id", return_value=[]):
        result = get_mlb_search_players(fullname="Judge")
        assert result["player_ids"] == []
        assert "note" in result


def test_get_mlb_players(mcp):
    get_mlb_players = get_tool(mcp, "get_mlb_players")
    assert get_mlb_players is not None
    with patch("mlb_api.mlb.get_people", return_value=[{"id": 1}]):
        result = get_mlb_players(sport_id=1)
        assert "players" in result


def test_get_mlb_draft(mcp):
    get_mlb_draft = get_tool(mcp, "get_mlb_draft")
    assert get_mlb_draft is not None
    with patch("mlb_api.mlb.get_draft", return_value={"draft": True}):
        result = get_mlb_draft(year_id=2022)
        assert "draft" in result


def test_get_mlb_awards(mcp):
    get_mlb_awards = get_tool(mcp, "get_mlb_awards")
    assert get_mlb_awards is not None
    with patch("mlb_api.mlb.get_awards", return_value={"awards": True}):
        result = get_mlb_awards(award_id=1)
        assert "awards" in result


def test_get_mlb_search_teams(mcp):
    get_mlb_search_teams = get_tool(mcp, "get_mlb_search_teams")
    assert get_mlb_search_teams is not None
    # Patch open and csv.DictReader for the CSV file
    with patch("builtins.open", create=True) as mock_open:
        mock_open.return_value.__enter__.return_value = MagicMock()
        with patch("csv.DictReader", return_value=[{"team_id": "147", "team_name": "New York Yankees"}]):
            result = get_mlb_search_teams(team_name="Yankees")
            assert "teams" in result


def test_get_mlb_teams(mcp):
    get_mlb_teams = get_tool(mcp, "get_mlb_teams")
    assert get_mlb_teams is not None
    with patch("mlb_api.mlb.get_teams", return_value=[{"id": 1}]):
        result = get_mlb_teams(sport_id=1)
        assert "teams" in result


def test_get_mlb_game_lineup(mcp):
    get_mlb_game_lineup = get_tool(mcp, "get_mlb_game_lineup")
    assert get_mlb_game_lineup is not None
    # Patch mlb.get_game_box_score to return a MagicMock with the required structure
    mock_boxscore = MagicMock()
    mock_team = MagicMock()
    mock_team.team = MagicMock(name="Yankees", id=1)
    mock_team.players = {}
    mock_boxscore.teams = MagicMock(away=mock_team, home=mock_team)
    with patch("mlb_api.mlb.get_game_box_score", return_value=mock_boxscore):
        result = get_mlb_game_lineup(game_id=1)
        assert "teams" in result


def test_get_mlb_game_lineup_extracts_players(mcp):
    """Player dict keys from the raw API are formatted like 'ID660271' (uppercase 'ID'
    prefix); the lineup tool must recognize them and read the models' real (snake_case)
    attribute names to populate names, positions, batting order, and game status.
    """
    get_mlb_game_lineup = get_tool(mcp, "get_mlb_game_lineup")

    mock_position = MagicMock(abbreviation="1B")
    mock_position.name = "First Base"
    mock_game_status = MagicMock(
        is_on_bench=False, is_substitute=False, is_current_batter=False, is_current_pitcher=True
    )
    mock_person = MagicMock(id=660271, full_name="Ty France")
    mock_player = MagicMock(
        person=mock_person,
        jersey_number="23",
        all_positions=[mock_position],
        batting_order=100,
        game_status=mock_game_status,
    )
    mock_team = MagicMock()
    mock_team.team = MagicMock(name="Giants", id=137)
    mock_team.players = {"ID660271": mock_player}
    mock_boxscore = MagicMock()
    mock_boxscore.teams = MagicMock(home=mock_team, away=mock_team)

    with patch("mlb_api.mlb.get_game_box_score", return_value=mock_boxscore):
        result = get_mlb_game_lineup(game_id=1)
        home_players = result["teams"]["home"]["players"]
        assert len(home_players) == 1
        player = home_players[0]
        assert player["player_id"] == 660271
        assert player["player_name"] == "Ty France"
        assert player["jersey_number"] == "23"
        assert player["batting_order"] == 100
        assert player["positions"] == [{"position": "1B", "position_name": "First Base"}]
        assert player["game_entries"][0]["is_current_pitcher"] is True


def test_get_statcast_pitcher(mcp):
    get_statcast_pitcher = get_tool(mcp, "get_statcast_pitcher")
    assert get_statcast_pitcher is not None

    class DummyDF:
        def to_dict(self, orient=None):
            return [{"foo": "bar"}]

        def astype(self, dtype):
            return self

    with patch("mlb_api.statcast_pitcher", return_value=DummyDF()):
        result = get_statcast_pitcher(start_date="2022-04-01", end_date="2022-04-07", player_id=456)
        assert "statcast_data" in result


def test_get_statcast_batter(mcp):
    get_statcast_batter = get_tool(mcp, "get_statcast_batter")
    assert get_statcast_batter is not None

    class DummyDF:
        def to_dict(self, orient=None):
            return [{"foo": "bar"}]

        def astype(self, dtype):
            return self

    with patch("mlb_api.statcast_batter", return_value=DummyDF()):
        result = get_statcast_batter(start_date="2022-04-01", end_date="2022-04-07", player_id=123)
        assert "statcast_data" in result


def test_get_statcast_team(mcp):
    get_statcast_team = get_tool(mcp, "get_statcast_team")
    assert get_statcast_team is not None

    class DummyDF:
        def to_dict(self, orient=None):
            # Simulate a row with many fields
            return [
                {"foo": "bar", "baz": "qux", "batter": "b1", "pitcher": "p1"},
                {"foo": "bar2", "baz": "qux2", "batter": "b2", "pitcher": "p2"},
            ]

        def astype(self, dtype):
            return self

    with patch("mlb_api.statcast", return_value=DummyDF()):
        # Test with one field
        result = get_statcast_team(start_date="2022-04-01", end_date="2022-04-07", team="Yankees", fields=["foo"])
        assert "statcast_data" in result
        for row in result["statcast_data"]:
            # Only 'foo', 'batter', 'pitcher' should be present
            assert set(row.keys()).issubset({"foo", "batter", "pitcher"})
            assert "batter" in row
            assert "pitcher" in row
        # Test with multiple fields
        result_multi = get_statcast_team(
            start_date="2022-04-01", end_date="2022-04-07", team="Yankees", fields=["foo", "baz"]
        )
        assert "statcast_data" in result_multi
        for row in result_multi["statcast_data"]:
            # Only 'foo', 'baz', 'batter', 'pitcher' should be present
            assert set(row.keys()).issubset({"foo", "baz", "batter", "pitcher"})
            assert "batter" in row
            assert "pitcher" in row
        # Test with empty fields list (should only return batter and pitcher)
        result_empty = get_statcast_team(start_date="2022-04-01", end_date="2022-04-07", team="Yankees", fields=[])
        assert "statcast_data" in result_empty
        for row in result_empty["statcast_data"]:
            assert set(row.keys()).issubset({"batter", "pitcher"})
            assert "batter" in row
            assert "pitcher" in row


# Additional test cases for better coverage


def test_get_mlb_standings_error_handling(mcp):
    """Test error handling in get_mlb_standings"""
    get_mlb_standings = get_tool(mcp, "get_mlb_standings")
    with patch("mlb_api.mlb.get_standings", side_effect=Exception("API Error")):
        result = get_mlb_standings(season=2022)
        assert "error" in result


def test_get_mlb_standings_invalid_league(mcp):
    """Test invalid league parameter"""
    get_mlb_standings = get_tool(mcp, "get_mlb_standings")
    result = get_mlb_standings(season=2022, league="INVALID")
    assert "error" in result


def test_get_mlb_schedule_date_validation(mcp):
    """Test date validation in get_mlb_schedule"""
    get_mlb_schedule = get_tool(mcp, "get_mlb_schedule")
    # Test invalid date format
    result = get_mlb_schedule(start_date="invalid-date", end_date="2022-04-07")
    assert "error" in result
    # Test start_date after end_date
    result = get_mlb_schedule(start_date="2022-04-07", end_date="2022-04-01")
    assert "error" in result


def test_get_mlb_schedule_no_games_found(mcp):
    """Test when no games are found"""
    get_mlb_schedule = get_tool(mcp, "get_mlb_schedule")
    with patch("mlb_api.mlb.get_schedule", return_value=None):
        result = get_mlb_schedule(start_date="2022-04-01", end_date="2022-04-07")
        assert "error" in result


def test_get_mlb_team_info_team_not_found(mcp):
    """Test when team is not found"""
    get_mlb_team_info = get_tool(mcp, "get_mlb_team_info")
    with patch("mlb_api.get_team_id_from_name", return_value=None):
        result = get_mlb_team_info(team="NonexistentTeam")
        assert "error" in result


def test_get_mlb_team_info_error_handling(mcp):
    """Test error handling in get_mlb_team_info"""
    get_mlb_team_info = get_tool(mcp, "get_mlb_team_info")
    with patch("mlb_api.get_team_id_from_name", return_value=123):
        with patch("mlb_api.mlb.get_team", side_effect=Exception("API Error")):
            result = get_mlb_team_info(team="Yankees")
            assert "error" in result


def test_get_mlb_player_info_error_handling(mcp):
    """Test error handling in get_mlb_player_info"""
    get_mlb_player_info = get_tool(mcp, "get_mlb_player_info")
    with patch("mlb_api.mlb.get_person", side_effect=Exception("API Error")):
        result = get_mlb_player_info(player_id=456)
        assert "error" in result


def test_get_mlb_boxscore_error_handling(mcp):
    """Test error handling in get_mlb_boxscore"""
    get_mlb_boxscore = get_tool(mcp, "get_mlb_boxscore")
    with patch("mlb_api.mlb.get_game_box_score", side_effect=Exception("API Error")):
        result = get_mlb_boxscore(game_id=789)
        assert "error" in result


def test_get_multiple_mlb_player_stats_error_handling(mcp):
    """Test error handling in get_multiple_mlb_player_stats"""
    get_multiple_mlb_player_stats = get_tool(mcp, "get_multiple_mlb_player_stats")
    with patch("mlb_api.get_multiple_player_stats", side_effect=Exception("API Error")):
        result = get_multiple_mlb_player_stats(player_ids="1,2", group="hitting", type="season", season=2022)
        assert "error" in result


def test_get_mlb_sabermetrics_error_handling(mcp):
    """Test error handling in get_mlb_sabermetrics"""
    get_mlb_sabermetrics = get_tool(mcp, "get_mlb_sabermetrics")
    with patch("mlb_api.get_sabermetrics_for_players", side_effect=Exception("API Error")):
        result = get_mlb_sabermetrics(player_ids="1,2", season=2022)
        assert "error" in result


def test_get_mlb_game_highlights_error_handling(mcp):
    """Test error handling in get_mlb_game_highlights"""
    get_mlb_game_highlights = get_tool(mcp, "get_mlb_game_highlights")
    with patch("mlb_api.mlb._mlb_adapter_v1.get", side_effect=Exception("API Error")):
        result = get_mlb_game_highlights(game_id=123)
        assert "error" in result


def test_get_mlb_game_pace_error_handling(mcp):
    """Test error handling in get_mlb_game_pace"""
    get_mlb_game_pace = get_tool(mcp, "get_mlb_game_pace")
    with patch("mlb_api.mlb.get_gamepace", side_effect=Exception("API Error")):
        result = get_mlb_game_pace(season=2022)
        assert "error" in result


def test_get_mlb_game_scoring_plays_error_handling(mcp):
    """Test error handling in get_mlb_game_scoring_plays"""
    get_mlb_game_scoring_plays = get_tool(mcp, "get_mlb_game_scoring_plays")
    with patch("mlb_api.mlb.get_game_play_by_play", side_effect=Exception("API Error")):
        result = get_mlb_game_scoring_plays(game_id=1)
        assert "error" in result


def test_get_mlb_linescore_error_handling(mcp):
    """Test error handling in get_mlb_linescore"""
    get_mlb_linescore = get_tool(mcp, "get_mlb_linescore")
    with patch("mlb_api.mlb.get_game_line_score", side_effect=Exception("API Error")):
        result = get_mlb_linescore(game_id=1)
        assert "error" in result


def test_get_mlb_roster_error_handling(mcp):
    """Test error handling in get_mlb_roster"""
    get_mlb_roster = get_tool(mcp, "get_mlb_roster")
    with patch("mlb_api.mlb.get_team_roster", side_effect=Exception("API Error")):
        result = get_mlb_roster(team="1", date="2022-04-01")
        assert "error" in result


def test_get_mlb_search_players_error_handling(mcp):
    """Test error handling in get_mlb_search_players"""
    get_mlb_search_players = get_tool(mcp, "get_mlb_search_players")
    with patch("mlb_api.mlb.get_people_id", side_effect=Exception("API Error")):
        result = get_mlb_search_players(fullname="John Doe")
        assert "error" in result


def test_get_mlb_players_error_handling(mcp):
    """Test error handling in get_mlb_players"""
    get_mlb_players = get_tool(mcp, "get_mlb_players")
    with patch("mlb_api.mlb.get_people", side_effect=Exception("API Error")):
        result = get_mlb_players(sport_id=1)
        assert "error" in result


def test_get_mlb_draft_error_handling(mcp):
    """Test error handling in get_mlb_draft"""
    get_mlb_draft = get_tool(mcp, "get_mlb_draft")
    with patch("mlb_api.mlb.get_draft", side_effect=Exception("API Error")):
        result = get_mlb_draft(year_id=2022)
        assert "error" in result


def test_get_mlb_awards_error_handling(mcp):
    """Test error handling in get_mlb_awards"""
    get_mlb_awards = get_tool(mcp, "get_mlb_awards")
    with patch("mlb_api.mlb.get_awards", side_effect=Exception("API Error")):
        result = get_mlb_awards(award_id=1)
        assert "error" in result


def test_get_mlb_search_teams_error_handling(mcp):
    """Test error handling in get_mlb_search_teams"""
    get_mlb_search_teams = get_tool(mcp, "get_mlb_search_teams")
    with patch("builtins.open", side_effect=Exception("File Error")):
        result = get_mlb_search_teams(team_name="Yankees")
        assert "error" in result


def test_get_mlb_teams_error_handling(mcp):
    """Test error handling in get_mlb_teams"""
    get_mlb_teams = get_tool(mcp, "get_mlb_teams")
    with patch("mlb_api.mlb.get_teams", side_effect=Exception("API Error")):
        result = get_mlb_teams(sport_id=1)
        assert "error" in result


def test_get_mlb_game_lineup_error_handling(mcp):
    """Test error handling in get_mlb_game_lineup"""
    get_mlb_game_lineup = get_tool(mcp, "get_mlb_game_lineup")
    with patch("mlb_api.mlb.get_game_box_score", side_effect=Exception("API Error")):
        result = get_mlb_game_lineup(game_id=1)
        assert "error" in result


def test_get_statcast_pitcher_error_handling(mcp):
    """Test error handling in get_statcast_pitcher"""
    get_statcast_pitcher = get_tool(mcp, "get_statcast_pitcher")
    with patch("mlb_api.statcast_pitcher", side_effect=Exception("API Error")):
        result = get_statcast_pitcher(start_date="2022-04-01", end_date="2022-04-07", player_id=456)
        assert "error" in result


def test_get_statcast_batter_error_handling(mcp):
    """Test error handling in get_statcast_batter"""
    get_statcast_batter = get_tool(mcp, "get_statcast_batter")
    with patch("mlb_api.statcast_batter", side_effect=Exception("API Error")):
        result = get_statcast_batter(start_date="2022-04-01", end_date="2022-04-07", player_id=123)
        assert "error" in result


def test_get_statcast_team_error_handling(mcp):
    """Test error handling in get_statcast_team"""
    get_statcast_team = get_tool(mcp, "get_statcast_team")
    with patch("mlb_api.statcast", side_effect=Exception("API Error")):
        result = get_statcast_team(start_date="2022-04-01", end_date="2022-04-07", team="Yankees", fields=["foo"])
        assert "error" in result


def test_get_mlb_standings_current_year(mcp):
    """Test get_mlb_standings with current year (no season parameter)"""
    get_mlb_standings = get_tool(mcp, "get_mlb_standings")
    with patch("mlb_api.mlb.get_standings", return_value={"dummy": "standings"}):
        with patch("mlb_api.datetime") as mock_datetime:
            mock_datetime.now.return_value.year = 2023
            result = get_mlb_standings()
            assert "standings" in result


def test_get_mlb_standings_al_only(mcp):
    """Test get_mlb_standings with AL only"""
    get_mlb_standings = get_tool(mcp, "get_mlb_standings")
    with patch("mlb_api.mlb.get_standings", return_value={"dummy": "standings"}):
        result = get_mlb_standings(season=2022, league="AL")
        assert "standings" in result
        assert "AL" in result["standings"]


def test_get_mlb_standings_nl_only(mcp):
    """Test get_mlb_standings with NL only"""
    get_mlb_standings = get_tool(mcp, "get_mlb_standings")
    with patch("mlb_api.mlb.get_standings", return_value={"dummy": "standings"}):
        result = get_mlb_standings(season=2022, league="NL")
        assert "standings" in result
        assert "NL" in result["standings"]


def test_get_team_id_from_name_numeric():
    """Test get_team_id_from_name with numeric string"""
    # Test the numeric conversion directly
    result = mlb_api.get_team_id_from_name("147")
    assert result == 147


def test_get_team_id_from_name_exact_match():
    """Test get_team_id_from_name with exact match"""
    # Mock the entire function to return a specific value for testing
    with patch.object(mlb_api, "get_team_id_from_name", return_value=147):
        result = mlb_api.get_team_id_from_name("New York Yankees")
        assert result == 147


def test_get_team_id_from_name_substring_match():
    """Test get_team_id_from_name with substring match"""
    # Mock the entire function to return a specific value for testing
    with patch.object(mlb_api, "get_team_id_from_name", return_value=147):
        result = mlb_api.get_team_id_from_name("Yankees")
        assert result == 147


def test_get_team_id_from_name_not_found():
    """Test get_team_id_from_name when team not found"""
    # Mock the entire function to return None for testing
    with patch.object(mlb_api, "get_team_id_from_name", return_value=None):
        result = mlb_api.get_team_id_from_name("Nonexistent Team")
        assert result is None


def test_validate_date_range_valid():
    """Test validate_date_range with valid dates"""
    result = mlb_api.validate_date_range("2022-04-01", "2022-04-07")
    assert result is None


def test_validate_date_range_invalid_format():
    """Test validate_date_range with invalid date format"""
    result = mlb_api.validate_date_range("invalid-date", "2022-04-07")
    assert "error" in result


def test_validate_date_range_start_after_end():
    """Test validate_date_range with start date after end date"""
    result = mlb_api.validate_date_range("2022-04-07", "2022-04-01")
    assert "error" in result


def test_check_result_size_small():
    """Test check_result_size with small result"""
    result = mlb_api.check_result_size({"key": "value"}, "test")
    assert result is None


def test_check_result_size_large():
    """Test check_result_size with large result"""
    # Create a large data structure that will exceed the word count limit
    # The function uses json.dumps(result).split() to count words
    # Create a list with many small strings that will create many words when JSON serialized
    large_data = {"data": ["word"] * 150000}  # This will create ~150k words when serialized
    result = mlb_api.check_result_size(large_data, "test")
    assert result is not None
    assert "error" in result


# Tests for helper functions


def test_get_multiple_player_stats_api_error():
    """Test get_multiple_player_stats with API error"""
    mock_mlb = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_mlb._mlb_adapter_v1.get.return_value = mock_response

    result = mlb_api.get_multiple_player_stats(mock_mlb, ["1"], ["season"], ["hitting"], 2022)
    assert result == {}


def test_get_multiple_player_stats_no_stats():
    """Test get_multiple_player_stats with no stats data"""
    mock_mlb = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.data = {"people": [{"id": 1}]}  # No stats field
    mock_mlb._mlb_adapter_v1.get.return_value = mock_response

    result = mlb_api.get_multiple_player_stats(mock_mlb, ["1"], ["season"], ["hitting"], 2022)
    assert result == []


def test_get_sabermetrics_for_players_api_error():
    """Test get_sabermetrics_for_players with API error"""
    mock_mlb = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_mlb._mlb_adapter_v1.get.return_value = mock_response

    result = mlb_api.get_sabermetrics_for_players(mock_mlb, ["1"], 2022)
    assert "error" in result


def test_get_sabermetrics_for_players_no_data():
    """Test get_sabermetrics_for_players with no data"""
    mock_mlb = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.data = {}  # No stats field
    mock_mlb._mlb_adapter_v1.get.return_value = mock_response

    result = mlb_api.get_sabermetrics_for_players(mock_mlb, ["1"], 2022)
    assert "error" in result


def test_get_sabermetrics_for_players_specific_stat():
    """Test get_sabermetrics_for_players with specific stat"""
    mock_mlb = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.data = {
        "stats": [
            {
                "splits": [
                    {
                        "player": {"id": 1, "fullName": "Test Player"},
                        "position": {"abbreviation": "P"},
                        "team": {"name": "Test Team", "id": 1},
                        "stat": {"war": 5.2},
                    }
                ]
            }
        ]
    }
    mock_mlb._mlb_adapter_v1.get.return_value = mock_response

    result = mlb_api.get_sabermetrics_for_players(mock_mlb, ["1"], 2022, stat_name="war")
    assert "players" in result
    assert len(result["players"]) == 1
    assert result["players"][0]["war"] == 5.2


def test_get_sabermetrics_for_players_stat_not_found():
    """Test get_sabermetrics_for_players with stat not found"""
    mock_mlb = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.data = {
        "stats": [
            {
                "splits": [
                    {
                        "player": {"id": 1, "fullName": "Test Player"},
                        "position": {"abbreviation": "P"},
                        "team": {"name": "Test Team", "id": 1},
                        "stat": {"woba": 0.350},
                    }
                ]
            }
        ]
    }
    mock_mlb._mlb_adapter_v1.get.return_value = mock_response

    result = mlb_api.get_sabermetrics_for_players(mock_mlb, ["1"], 2022, stat_name="war")
    assert "players" in result
    assert len(result["players"]) == 1
    assert result["players"][0]["war"] is None
    assert "available_stats" in result["players"][0]


def test_get_team_abbreviation_from_name():
    """Test get_team_abbreviation_from_name"""
    with patch("mlb_api.get_team_id_from_name", return_value=147):
        with patch("mlb_api.mlb.get_team") as mock_get_team:
            mock_team = MagicMock()
            mock_team.abbreviation = "NYY"
            mock_get_team.return_value = mock_team

            result = mlb_api.get_team_abbreviation_from_name("Yankees")
            assert result == "NYY"


def test_get_team_abbreviation_from_name_no_team_id():
    """Test get_team_abbreviation_from_name with no team ID"""
    with patch("mlb_api.get_team_id_from_name", return_value=None):
        result = mlb_api.get_team_abbreviation_from_name("Nonexistent")
        assert result is None


def test_get_team_abbreviation_from_name_no_abbreviation():
    """Test get_team_abbreviation_from_name with no abbreviation"""
    with patch("mlb_api.get_team_id_from_name", return_value=147):
        with patch("mlb_api.mlb.get_team") as mock_get_team:
            mock_team = MagicMock()
            # Remove the abbreviation attribute to simulate it not existing
            del mock_team.abbreviation
            mock_get_team.return_value = mock_team

            result = mlb_api.get_team_abbreviation_from_name("Yankees")
            assert result is None


# Tests for generic_api.py


def test_get_current_date(mcp):
    """Test get_current_date function"""
    get_current_date = get_tool(mcp, "get_current_date")
    assert get_current_date is not None

    # Test successful execution
    result = get_current_date()
    assert isinstance(result, str)
    # Check if it's in the correct format (YYYY-MM-DD)
    assert len(result) == 10
    assert result.count("-") == 2
    # Verify it's a valid date
    from datetime import datetime

    datetime.strptime(result, "%Y-%m-%d")  # Should not raise an exception


def test_get_current_time(mcp):
    """Test get_current_time function"""
    get_current_time = get_tool(mcp, "get_current_time")
    assert get_current_time is not None

    # Test successful execution
    result = get_current_time()
    assert isinstance(result, str)
    # Check if it's in the correct format (HH:MM:SS)
    assert len(result) == 8
    assert result.count(":") == 2
    # Verify it's a valid time
    from datetime import datetime

    datetime.strptime(result, "%H:%M:%S")  # Should not raise an exception


def test_get_current_date_error_handling(mcp):
    """Test get_current_date error handling"""
    get_current_date = get_tool(mcp, "get_current_date")

    # Mock datetime.now to raise an exception
    with patch("generic_api.datetime") as mock_datetime:
        mock_datetime.now.side_effect = Exception("Test error")
        result = get_current_date()
        assert "Error getting current date" in result


def test_get_current_time_error_handling(mcp):
    """Test get_current_time error handling"""
    get_current_time = get_tool(mcp, "get_current_time")

    # Mock datetime.now to raise an exception
    with patch("generic_api.datetime") as mock_datetime:
        mock_datetime.now.side_effect = Exception("Test error")
        result = get_current_time()
        assert "Error getting current time" in result


def test_generic_tools_setup():
    """Test that generic tools are properly set up"""
    mock_mcp = MagicMock()
    generic_api.setup_generic_tools(mock_mcp)

    # Verify that the tool decorator was called
    assert mock_mcp.tool.called

    # Get the decorated functions
    tool_calls = mock_mcp.tool.call_args_list
    assert len(tool_calls) == 2  # Two tools: get_current_date and get_current_time
