from datetime import datetime
from typing import Any, List, Optional

import mlbstatsapi
import mlbstatsapi.mlb_dataadapter
from pybaseball import statcast, statcast_batter, statcast_pitcher

# mlbstatsapi.mlb_dataadapter.MlbDataAdapter.get() calls requests.get() with no timeout, so a
# stalled upstream connection (statsapi.mlb.com not responding, a hung proxy, etc.) blocks the
# calling thread forever instead of failing. Under concurrent tool calls this exhausts the
# server's worker pool and stalls unrelated requests too - observed in production as every
# in-flight get_mlb_search_players/get_mlb_player_info call hanging for exactly 300s, which was
# actually the *caller's* client-side timeout tearing down the connection, not ours. Patch in a
# bounded timeout so a stalled upstream fails fast with a normal {"error": ...} response.
_MLB_STATSAPI_TIMEOUT_SECONDS = 15
_original_mlb_dataadapter_requests_get = mlbstatsapi.mlb_dataadapter.requests.get


def _mlb_dataadapter_requests_get_with_timeout(*args, **kwargs):
    kwargs.setdefault("timeout", _MLB_STATSAPI_TIMEOUT_SECONDS)
    return _original_mlb_dataadapter_requests_get(*args, **kwargs)


mlbstatsapi.mlb_dataadapter.requests.get = _mlb_dataadapter_requests_get_with_timeout

mlb = mlbstatsapi.Mlb()


def get_multiple_player_stats(
    mlb, person_ids: list, stats: list, groups: list, season: Optional[int] = None, **params
) -> dict | list:
    """
    returns stat data for a team

    Parameters
    ----------
    mlb : mlbstatsapi.Mlb
        The MLB stats API instance
    person_ids : list
        the person ids
    stats : list
        list of stat types. List of statTypes can be found at https://statsapi.mlb.com/api/v1/statTypes
    groups : list
        list of stat grous. List of statGroups can be found at https://statsapi.mlb.com/api/v1/statGroups
    season : str, optional
        Insert year to return team stats for a particular season, season=2018
    eventType : str, optional
        Notes for individual events for playLog, playlog can be filered by individual events.
        List of eventTypes can be found at https://statsapi.mlb.com/api/v1/eventTypes

    Returns
    -------
    dict
        returns a dict of stats

    See Also
    --------
    Mlb.get_stats : Get stats
    Mlb.get_team_stats : Get team stats
    Mlb.get_players_stats_for_game : Get player stats for a game

    Examples
    --------
    >>> mlb = Mlb()
    >>> stats = ['season', 'seasonAdvanced']
    >>> groups = ['hitting']
    >>> mlb.get_player_stats(647351, stats, groups)
    {'hitting': {'season': [HittingSeason], 'seasonadvanced': [HittingSeasonAdvanced] }}
    """
    from mlbstatsapi import mlb_module

    params["stats"] = stats
    params["group"] = groups

    hydrate_arr = []
    if groups:
        hydrate_arr.append(f"group=[{','.join(groups)}]")
    if stats:
        hydrate_arr.append(f"type=[{','.join(stats)}]")
    if season:
        hydrate_arr.append(f"season={season}")

    mlb_data = mlb._mlb_adapter_v1.get(
        endpoint=f"people?personIds={','.join(person_ids)}&hydrate=stats({','.join(hydrate_arr)})"
    )
    if 400 <= mlb_data.status_code <= 499:
        return {}

    splits = []

    for person in mlb_data.data["people"]:
        if person.get("stats"):
            splits.append(mlb_module.create_split_data(person["stats"]))

    return splits


def get_sabermetrics_for_players(
    mlb, player_ids: list, season: int, stat_name: Optional[str] = None, group: str = "hitting"
) -> dict:
    """
    Get sabermetric statistics (like WAR) for multiple players for a specific season.

    Parameters
    ----------
    mlb : mlbstatsapi.Mlb
        The MLB stats API instance
    player_ids : list
        List of player IDs to get sabermetrics for
    season : int
        The season year to get stats for
    stat_name : str, optional
        Specific sabermetric stat to extract (e.g., 'war', 'woba', 'wRc'). If None, returns all sabermetrics.
    group : str, optional
        The stat group ('hitting' or 'pitching'). Default is 'hitting'.

    Returns
    -------
    dict
        Dictionary containing player sabermetrics data
    """

    # Build the API endpoint URL
    endpoint = f"stats?stats=sabermetrics&group={group}&sportId=1&season={season}"

    # Make the API call directly
    response = mlb._mlb_adapter_v1.get(endpoint=endpoint)

    if 400 <= response.status_code <= 499:
        return {"error": f"API error: {response.status_code}"}

    if not response.data or "stats" not in response.data:
        return {"error": "No stats data found"}

    # Extract the relevant data
    result: dict[str, Any] = {"season": season, "group": group, "players": []}

    # Filter for our specific players
    player_ids_int = [int(pid) for pid in player_ids]

    for stat_group in response.data["stats"]:
        if "splits" in stat_group:
            for split in stat_group["splits"]:
                if "player" in split and split["player"]["id"] in player_ids_int:
                    player_data = {
                        "player_id": split["player"]["id"],
                        "player_name": split["player"].get("fullName", "Unknown"),
                        "position": split.get("position", {}).get("abbreviation", "N/A"),
                        "team": split.get("team", {}).get("name", "N/A"),
                        "team_id": split.get("team", {}).get("id", None),
                    }

                    # Extract the sabermetric stats
                    if "stat" in split:
                        if stat_name:
                            # Return only the specific stat requested
                            if stat_name.lower() in split["stat"]:
                                player_data[stat_name] = split["stat"][stat_name.lower()]
                            else:
                                player_data[stat_name] = None
                                player_data["available_stats"] = list(split["stat"].keys())
                        else:
                            # Return all sabermetric stats
                            player_data["sabermetrics"] = split["stat"]

                    result["players"].append(player_data)

    return result


def filter_fields_by_name(obj, field_names: set):
    """
    Recursively prune a dict/list structure, keeping only keys listed in field_names
    (plus whatever ancestors are needed to reach a match). If a matched key's subtree
    contains no deeper matches, the subtree is returned unfiltered rather than emptied,
    since the caller didn't ask for anything more specific below it.
    """
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            if key in field_names:
                if isinstance(value, (dict, list)):
                    nested = filter_fields_by_name(value, field_names)
                    result[key] = nested if nested else value
                else:
                    result[key] = value
            elif isinstance(value, (dict, list)):
                nested = filter_fields_by_name(value, field_names)
                if nested:
                    result[key] = nested
        return result
    if isinstance(obj, list):
        items = [filter_fields_by_name(item, field_names) for item in obj]
        return [item for item in items if item not in (None, {}, [])]
    return obj


# statTypes accepted by the MLB Stats API for player stat lookups (see
# https://statsapi.mlb.com/api/v1/statTypes).
VALID_STAT_TYPES = {
    "byDateRange",
    "byDateRangeAdvanced",
    "byDayOfWeek",
    "byDayOfWeekPlayoffs",
    "byMonth",
    "byMonthPlayoffs",
    "career",
    "careerAdvanced",
    "careerPlayoffs",
    "careerRegularSeason",
    "expectedStatistics",
    "gameLog",
    "homeAndAway",
    "homeAndAwayPlayoffs",
    "hotColdZones",
    "lastXGames",
    "opponentsFaced",
    "outsAboveAverage",
    "pitchArsenal",
    "pitchLog",
    "playLog",
    "projectedRos",
    "rankingsByYear",
    "sabermetrics",
    "season",
    "seasonAdvanced",
    "sprayChart",
    "statsSingleSeason",
    "statsSingleSeasonAdvanced",
    "vsPlayer",
    "vsPlayer5Y",
    "vsPlayerTotal",
    "vsTeam",
    "vsTeam5Y",
    "vsTeamTotal",
    "winLoss",
    "winLossPlayoffs",
    "yearByYear",
    "yearByYearAdvanced",
    "yearByYearPlayoffs",
}


def get_team_id_from_name(team: str) -> Optional[int]:
    """Helper to get team ID from team name, partial name, or stringified ID."""
    # Accept stringified integer as ID
    try:
        return int(team)
    except (ValueError, TypeError):
        pass
    import csv

    team_lower = team.lower().strip()
    with open("current_mlb_teams.csv", "r") as f:
        reader = csv.DictReader(f)
        # First, try exact match
        for row in reader:
            if team_lower == row["team_name"].lower().strip():
                return int(row["team_id"])
        f.seek(0)
        next(reader)  # skip header
        # Then, try substring match
        for row in reader:
            if team_lower in row["team_name"].lower():
                return int(row["team_id"])
    return None


def get_team_abbreviation_from_name(team: str) -> Optional[str]:
    """
    Given a team name, partial name, or ID, return the 3-letter team abbreviation (e.g., 'NYY' for Yankees).
    Returns None if not found.
    """
    team_id = get_team_id_from_name(team)
    if team_id is None:
        return None
    team_info = mlb.get_team(team_id)
    return getattr(team_info, "abbreviation", None)


def check_result_size(result: dict, context: str) -> Optional[dict]:
    """
    Utility to check the size of a result dictionary (by word count). Returns an error dict if too large, else None.
    """
    import json

    word_count = len(json.dumps(result).split())
    if word_count > 100000:
        return {
            "error": (
                f"Result too large ({word_count} words). Please narrow your query "
                f"(e.g., shorter date range, specific {context})."
            )
        }
    return None


def validate_date_range(start_date: str, end_date: str) -> Optional[dict]:
    """
    Utility to check that start_date is before or equal to end_date.
    Returns an error dict if invalid, else None.
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        if start > end:
            return {"error": f"start_date ({start_date}) must be before or equal to end_date ({end_date})"}
    except Exception as e:
        return {"error": f"Invalid date format: {e}"}
    return None


def setup_mlb_tools(mcp):
    """Setup MLB tools for the MCP server"""

    @mcp.tool()
    def get_mlb_standings(
        season: Optional[int] = None,
        standingsTypes: Optional[str] = None,
        date: Optional[str] = None,
        hydrate: Optional[str] = None,
        fields: Optional[str] = None,
        league: str = "both",
    ) -> dict:
        """
        Get current MLB standings for a given season (year).

        Args:
            season (Optional[int]): The year for which to retrieve standings. Defaults to current year.
            standingsTypes (Optional[str]): The type of standings to retrieve (e.g., 'regularSeason', 'wildCard', etc.).
            date (Optional[str]): Date in 'YYYY-MM-DD' format.
            hydrate (Optional[str]): Additional data to hydrate in the response.
            fields (Optional[str]): Comma-separated list of fields to include in the response.
            league (str): Filter by league. Accepts 'AL', 'NL', or 'both' (default: 'both').

        Returns:
            dict: Standings for the specified league(s) and season.
        """
        try:
            if season is None:
                season = datetime.now().year
            params = {}
            if standingsTypes is not None:
                params["standingsTypes"] = standingsTypes
            if date is not None:
                params["date"] = date
            if hydrate is not None:
                params["hydrate"] = hydrate
            if fields is not None:
                params["fields"] = fields
            league = league.upper()
            result = {}
            if league == "AL" or league == "BOTH":
                result["AL"] = mlb.get_standings(103, season=str(season), **params)
            if league == "NL" or league == "BOTH":
                result["NL"] = mlb.get_standings(104, season=str(season), **params)
            if not result:
                return {"error": "Invalid league parameter. Use 'AL', 'NL', or 'both'."}
            return {"standings": result}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_schedule(
        start_date: str,
        end_date: str,
        sport_id: int = 1,
        team: Optional[str] = None,
    ) -> dict:
        """
        Get MLB schedule for a specific date range, sport ID, or team (ID or name).

        Args:
            sport_id (int): Sport ID (default: 1 for MLB).
            start_date (str): Start date in 'YYYY-MM-DD' format. Required.
            end_date (str): End date in 'YYYY-MM-DD' format. Required.
            team (Optional[str]): Team ID or team name as a string. Can be numeric string, full name, abbreviation, or
              location. If not provided, defaults to all teams.

        Returns:
            dict: Schedule data for the specified parameters.
        """
        try:
            # Validate date range
            date_error = validate_date_range(start_date, end_date)
            if date_error:
                return date_error
            team_id = get_team_id_from_name(team) if team is not None else None
            schedule = mlb.get_schedule(
                start_date=start_date,
                end_date=end_date,
                sport_id=sport_id,
                team_id=team_id,
            )
            if not schedule:
                return {
                    "error": (
                        f"No games found for the given date range ({start_date} to {end_date}). The date range may "
                        "have resulted in nothing being returned."
                    )
                }
            return {"schedule": schedule}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_team_info(
        team: str,
        season: Optional[int] = None,
        sport_id: Optional[int] = None,
        hydrate: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> dict:
        """
        Get information about a specific team by ID or name.

        Args:
            team (str): Team ID or team name as a string. Can be numeric string, full name, abbreviation, or location.
            season (Optional[int]): Season year.
            sport_id (Optional[int]): Sport ID.
            hydrate (Optional[str]): Additional data to hydrate.
            fields (Optional[str]): Comma-separated list of fields to include.

        Returns:
            dict: Team information.
        """
        try:
            params: dict[str, Any] = {}
            if season is not None:
                params["season"] = season
            if sport_id is not None:
                params["sportId"] = sport_id
            if hydrate is not None:
                params["hydrate"] = hydrate
            if fields is not None:
                params["fields"] = fields
            team_id = get_team_id_from_name(team)
            if team_id is None:
                return {"error": f"Could not find team ID for '{team}'"}
            team_info = mlb.get_team(team_id, **params)
            return {"team_info": team_info}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_player_info(player_id: int) -> dict:
        """
        Get information about a specific player by ID.

        Args:
            player_id (int): The player ID.

        Returns:
            dict: Player information.
        """
        try:
            player_info = mlb.get_person(player_id)
            return {"player_info": player_info}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_boxscore(game_id: int, timecode: Optional[str] = None, fields: Optional[str] = None) -> dict:
        """
        Get boxscore for a specific game by game_id.

        Args:
            game_id (int): The game ID.
            timecode (Optional[str]): Specific timecode for the boxscore snapshot.
            fields (Optional[str]): Comma-separated list of field names to include in the response. Filtering is
              applied locally after fetching the full boxscore, so it never breaks response validation.

        Returns:
            dict: Boxscore information, under the ``boxscore`` key.
        """
        try:
            params = {}
            if timecode is not None:
                params["timecode"] = timecode
            # Note: `fields` is intentionally NOT passed to the underlying API call. The MLB Stats API applies
            # `fields` server-side, which can strip fields that the response model requires, causing validation
            # to fail. Instead we always fetch the full boxscore (so validation always succeeds) and filter it
            # ourselves afterward.
            boxscore = mlb.get_game_box_score(game_id, **params)
            if boxscore is None:
                return {"error": f"No boxscore found for game_id {game_id}"}
            if fields is not None:
                boxscore_dict = boxscore.model_dump(by_alias=True) if hasattr(boxscore, "model_dump") else boxscore
                field_names = {f.strip() for f in fields.split(",") if f.strip()}
                return {"boxscore": filter_fields_by_name(boxscore_dict, field_names)}
            return {"boxscore": boxscore}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_multiple_mlb_player_stats(
        player_ids: str,
        group: Optional[str] = None,
        type: Optional[str] = None,
        season: Optional[int] = None,
        eventType: Optional[str] = None,
    ) -> dict:
        """
        Get player stats by comma separated player_ids, group, type, season, and optional eventType.

        Args:
            player_ids (str): Comma-separated list of player IDs.
            group (Optional[str]): Stat group (e.g., hitting, pitching).
            type (Optional[str]): Stat type. Defaults to "career" if not specified. See
              https://statsapi.mlb.com/api/v1/statTypes for the full list of accepted values
              (e.g. "season", "career", "gameLog", "yearByYear").
            season (Optional[int]): Season year.
            eventType (Optional[str]): Event type filter.

        Returns:
            dict: Player statistics.
        """
        try:
            player_ids_list = [pid.strip() for pid in player_ids.split(",")]

            if type is None:
                stats = ["career"]
            elif type == "season":
                stats = ["season", "seasonAdvanced"]
            elif type in VALID_STAT_TYPES:
                stats = [type]
            else:
                return {
                    "error": (
                        f"Invalid type '{type}'. See https://statsapi.mlb.com/api/v1/statTypes for valid values, "
                        f"e.g.: {', '.join(sorted(VALID_STAT_TYPES))}."
                    )
                }
            groups = [group] if group else ["hitting"]

            splits = get_multiple_player_stats(mlb, player_ids_list, stats, groups, season)
            return {"player_stats": splits}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_sabermetrics(
        player_ids: str, season: int, stat_name: Optional[str] = None, group: str = "hitting"
    ) -> dict:
        """
        Get sabermetric statistics (including WAR) for multiple players for a specific season.

        Args:
            player_ids (str): Comma-separated list of player IDs.
            season (int): Season year.
            stat_name (Optional[str]): Specific sabermetric stat to extract (e.g., 'war', 'woba', 'wRc').
            group (str): Stat group ('hitting' or 'pitching').

        Returns:
            dict: Sabermetric statistics.
        """
        try:
            player_ids_list = [pid.strip() for pid in player_ids.split(",")]
            result = get_sabermetrics_for_players(mlb, player_ids_list, season, stat_name, group)
            return result
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_game_highlights(game_id: int) -> dict:
        """
        Get game highlights for a specific game by game_id.

        Args:
            game_id (int): The game ID.

        Returns:
            dict: Game highlights, under the ``highlights`` key.
        """
        try:
            # Fetch the raw game content directly rather than going through
            # ``mlb.get_game(game_id).content.highlights``. The ``Game`` model
            # validates the full game feed and breaks when upstream changes a
            # field's shape (e.g. ``gameData.absChallenges`` was changed from a
            # list to an object), which makes the whole highlights tool fail
            # even though the highlights payload itself is intact. Reading the
            # content endpoint directly sidesteps that validation entirely.
            response = mlb._mlb_adapter_v1.get(endpoint=f"game/{game_id}/content")
            if 400 <= response.status_code <= 499:
                return {"error": f"No content found for game_id {game_id}"}
            content = response.data or {}
            highlights = content.get("highlights", {})
            if isinstance(highlights, dict):
                highlights = highlights.get("highlights", [])
            if not highlights:
                return {"error": f"No highlights found for game_id {game_id}"}
            return {"highlights": highlights}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_game_pace(season: int, sport_id: int = 1) -> dict:
        """
        Get game pace statistics for a given season.

        Args:
            season (int): Season year.
            sport_id (int): Sport ID (default: 1 for MLB).

        Returns:
            dict: Game pace statistics, under the ``game_pace`` key.
        """
        try:
            gamepace = mlb.get_gamepace(str(season), sport_id=sport_id)
            return {"game_pace": gamepace}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_game_scoring_plays(
        game_id: int, eventType: Optional[str] = None, timecode: Optional[str] = None, fields: Optional[str] = None
    ) -> dict:
        """
        Get plays for a specific game by game_id, with optional filtering by eventType.

        Args:
            game_id (int): The game ID.
            eventType (Optional[str]): Filter plays by this event type (e.g., 'scoring_play', 'home_run').
            timecode (Optional[str]): Specific timecode for the play-by-play snapshot.
            fields (Optional[str]): Comma-separated list of fields to include.

        Returns:
            dict: Game plays (under the ``plays`` key), optionally filtered by eventType.
        """
        try:
            params = {}
            if timecode is not None:
                params["timecode"] = timecode
            if fields is not None:
                params["fields"] = fields
            plays = mlb.get_game_play_by_play(game_id, **params)
            # The Plays model exposes plays as ``all_plays`` (snake_case) and each
            # play's event type as ``result.event_type``. The previous ``allplays`` /
            # ``eventType`` spellings were pre-attribute-rename and silently matched
            # nothing, so the eventType filter dropped every play.
            all_plays = getattr(plays, "all_plays", []) or []
            if eventType:
                filtered_plays = [
                    play
                    for play in all_plays
                    if getattr(getattr(play, "result", None), "event_type", None) == eventType
                ]
                return {"plays": filtered_plays}
            return {"plays": all_plays}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_linescore(game_id: int) -> dict:
        """
        Get linescore for a specific game by game_id.

        Args:
            game_id (int): The game ID.

        Returns:
            dict: Linescore information, under the ``linescore`` key.
        """
        try:
            linescore = mlb.get_game_line_score(game_id)
            return {"linescore": linescore}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_roster(
        team: str,
        date: Optional[str] = None,
        rosterType: Optional[str] = None,
        season: Optional[str] = None,
        hydrate: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> dict:
        """
        Get team roster for a specific team (ID or name), with optional filters.

        Args:
            team (str): Team ID or team name as a string. Can be numeric string, full name, abbreviation, or location.
            date (Optional[str]): Date in 'YYYY-MM-DD' format. If not provided, defaults to today.
            rosterType (Optional[str]): Filter by roster type (e.g., 40Man, fullSeason, etc.).
            season (Optional[str]): Filter by single season (year).
            hydrate (Optional[str]): Additional data to hydrate in the response.
            fields (Optional[str]): Comma-separated list of fields to include.

        Returns:
            dict: Team roster information.
        """
        try:
            if date is None:
                date = datetime.now().strftime("%Y-%m-%d")
            params = {}
            if rosterType is not None:
                params["rosterType"] = rosterType
            if season is not None:
                params["season"] = season
            params["date"] = date
            if hydrate is not None:
                params["hydrate"] = hydrate
            if fields is not None:
                params["fields"] = fields
            team_id = get_team_id_from_name(team)
            if team_id is None:
                return {"error": f"Could not find team ID for '{team}'"}
            roster = mlb.get_team_roster(team_id, **params)
            # ``get_team_roster`` returns a bare list of Player objects. Per the
            # MCP spec a tool's structured result must be a dict (or None), so
            # wrap the list under a descriptive key rather than returning it
            # directly.
            return {"roster": roster}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_search_players(fullname: str, sport_id: int = 1, search_key: str = "fullName") -> dict:
        """
        Search for players by name.

        Args:
            fullname (str): Player name to search for. Must be the player's exact full name
              (case-insensitive); the underlying API does not support partial/substring matches.
            sport_id (int): Sport ID (default: 1 for MLB).
            search_key (str): Which field of each candidate player record to compare `fullname` against.
              The underlying API only ever fetches "fullName" for each player, so this must be "fullName"
              (default) - any other value will silently match nothing.

        Returns:
            dict: Player search results.
        """
        try:
            # The underlying API only ever populates "fullName" (and "id", which can't be used here - the
            # library's own name-matching logic assumes a string field) on each candidate record. Normalize
            # common casings (e.g. "fullname") instead of silently matching zero players.
            if search_key.lower() != "fullname":
                return {"error": f"Invalid search_key '{search_key}'. Must be 'fullName'."}
            # The library does an exact (case-insensitive) string comparison with no trimming, so stray
            # whitespace causes a silent zero-result match.
            fullname = fullname.strip()
            player_ids = mlb.get_people_id(fullname, sport_id=sport_id, search_key="fullName")
            result: dict = {"player_ids": player_ids}
            if not player_ids:
                result["note"] = (
                    f"No player found with the exact full name '{fullname}'. This search requires an "
                    "exact match (case-insensitive) against the player's full name; partial names "
                    "(e.g. just a last name) will not match."
                )
            return result
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_players(sport_id: int = 1, season: Optional[int] = None) -> dict:
        """
        Get all players for a specific sport.

        Args:
            sport_id (int): Sport ID (default: 1 for MLB).
            season (Optional[int]): Filter players by a specific season (year).

        Returns:
            dict: All players for the specified sport.
        """
        try:
            params = {}
            if season is not None:
                params["season"] = season
            players = mlb.get_people(sport_id=sport_id, **params)
            return {"players": players}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_draft(year_id: int) -> dict:
        """
        Get draft information for a specific year.

        Args:
            year_id (int): Draft year.

        Returns:
            dict: Draft information.
        """
        try:
            draft = mlb.get_draft(year_id)
            return {"draft": draft}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_awards(award_id: int) -> dict:
        """
        Get award recipients for a specific award.

        Args:
            award_id (int): Award ID.

        Returns:
            dict: Award recipients.
        """
        try:
            awards = mlb.get_awards(award_id)
            return {"awards": awards}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_search_teams(team_name: str, search_key: str = "name") -> dict:
        """
        Search for teams by name or ID.

        Args:
            team_name (str): Team name or ID to search for.
            search_key (str): Search key ("name", "id", or "all").

        Returns:
            dict: Team search results.
        """
        try:
            import csv

            # Load teams from CSV
            teams = []
            with open("current_mlb_teams.csv", "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    teams.append(row)

            # Search for teams
            results = []
            for team in teams:
                if search_key == "id":
                    if team_name == team["team_id"]:
                        results.append(team)
                elif search_key == "name":
                    if team_name.lower() in team["team_name"].lower():
                        results.append(team)
                else:  # search_key == "all"
                    if team_name == team["team_id"] or team_name.lower() in team["team_name"].lower():
                        results.append(team)

            return {"teams": results}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_teams(sport_id: int = 1, season: Optional[int] = None) -> dict:
        """
        Get all teams for a specific sport.

        Args:
            sport_id (int): Sport ID (default: 1 for MLB).
            season (Optional[int]): Filter teams by a specific season (year).

        Returns:
            dict: All teams for the specified sport.
        """
        try:
            params = {}
            if season is not None:
                params["season"] = season
            teams = mlb.get_teams(sport_id=sport_id, **params)
            return {"teams": teams}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_game_lineup(game_id: int) -> dict:
        """
        Get lineup information for a specific game by game_id.

        Args:
            game_id (int): The game ID.

        Returns:
            dict: Game lineup information.
        """
        try:
            # Get the boxscore data
            boxscore = mlb.get_game_box_score(game_id)

            result: dict[str, Any] = {"game_id": game_id, "teams": {}}

            # Process both teams (away and home)
            for team_type in ["away", "home"]:
                if hasattr(boxscore, "teams") and hasattr(boxscore.teams, team_type):
                    team_data = getattr(boxscore.teams, team_type)

                    team_info: dict[str, Any] = {
                        "team_name": getattr(team_data.team, "name", "Unknown"),
                        "team_id": getattr(team_data.team, "id", None),
                        "players": [],
                    }

                    # Get players from the team data
                    if hasattr(team_data, "players") and team_data.players is not None:
                        players_dict = team_data.players

                        # Extract player information. Player dict keys are formatted like "ID660271"
                        # (uppercase "ID" prefix from the raw MLB Stats API response).
                        for player_key, player_data in players_dict.items():
                            if player_key.upper().startswith("ID"):
                                player_info: dict[str, Any] = {
                                    "player_id": getattr(player_data.person, "id", None),
                                    "player_name": getattr(player_data.person, "full_name", "Unknown"),
                                    "jersey_number": getattr(player_data, "jersey_number", None),
                                    "positions": [],
                                    "batting_order": None,
                                    "game_entries": [],
                                }

                                # Get position information
                                if hasattr(player_data, "all_positions") and player_data.all_positions is not None:
                                    for position in player_data.all_positions:
                                        position_info = {
                                            "position": getattr(position, "abbreviation", None),
                                            "position_name": getattr(position, "name", None),
                                        }
                                        player_info["positions"].append(position_info)

                                # Get batting order from player data directly
                                if hasattr(player_data, "batting_order"):
                                    player_info["batting_order"] = getattr(player_data, "batting_order", None)

                                # Get game entry information (substitutions, etc.)
                                if hasattr(player_data, "game_status"):
                                    game_status = player_data.game_status
                                    entry_info = {
                                        "is_on_bench": getattr(game_status, "is_on_bench", False),
                                        "is_substitute": getattr(game_status, "is_substitute", False),
                                        "is_current_batter": getattr(game_status, "is_current_batter", False),
                                        "is_current_pitcher": getattr(game_status, "is_current_pitcher", False),
                                    }
                                    player_info["game_entries"].append(entry_info)

                                team_info["players"].append(player_info)

                    # Sort players by batting order (starting lineup first, then substitutes).
                    # MLB's battingOrder is a 3-digit string: the first digit is the lineup spot
                    # (1-9), the remaining digits count substitutions in that spot (e.g. "100" is the
                    # leadoff starter, "101" is the first sub batting leadoff).
                    def sort_key(player):
                        batting_order = player.get("batting_order")
                        if batting_order is None:
                            return 999  # Put non-batting order players at the end
                        return int(str(batting_order))

                    team_info["players"].sort(key=sort_key)
                    result["teams"][team_type] = team_info

            return result
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_statcast_pitcher(
        player_id: int,
        start_date: str,
        end_date: str,
    ) -> dict:
        """
        Retrieve MLB Statcast data for a single pitcher over a date range.

        Parameters
        ----------
        player_id : int
            MLBAM ID of the pitcher.
        start_date : str
            The start date in 'YYYY-MM-DD' format. Required.
        end_date : str
            The end date in 'YYYY-MM-DD' format. Required.

        Returns
        -------
        dict
            Dictionary with Statcast data for the pitcher. If the result is too large, returns an error message.

        Notes
        -----
        Data is sourced from MLB Statcast via pybaseball. See the official documentation for more details:
        https://github.com/jldbc/pybaseball/tree/master/docs
        """
        try:
            # Validate date range
            date_error = validate_date_range(start_date, end_date)
            if date_error:
                return date_error
            data = statcast_pitcher(start_date, end_date, player_id)
            # Convert all columns to string to ensure JSON serializability
            data = data.astype(str)
            result = {"statcast_data": data.to_dict(orient="records")}
            if not result["statcast_data"]:
                return {
                    "error": (
                        f"No Statcast data found for the given date range ({start_date} to {end_date}). The date "
                        "range may have resulted in nothing being returned."
                    )
                }
            size_error = check_result_size(result, "player")
            if size_error:
                return size_error
            return result
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_statcast_batter(
        player_id: int,
        start_date: str,
        end_date: str,
    ) -> dict:
        """
        Retrieve MLB Statcast data for a single batter over a date range.

        Parameters
        ----------
        player_id : int
            MLBAM ID of the batter.
        start_date : str
            The start date in 'YYYY-MM-DD' format. Required.
        end_date : str
            The end date in 'YYYY-MM-DD' format. Required.

        Returns
        -------
        dict
            Dictionary with Statcast data for the batter. If the result is too large, returns an error message.

        Notes
        -----
        Data is sourced from MLB Statcast via pybaseball. See the official documentation for more details:
        https://github.com/jldbc/pybaseball/tree/master/docs
        """
        try:
            # Validate date range
            date_error = validate_date_range(start_date, end_date)
            if date_error:
                return date_error
            data = statcast_batter(start_date, end_date, player_id)
            # Convert all columns to string to ensure JSON serializability
            data = data.astype(str)
            result = {"statcast_data": data.to_dict(orient="records")}
            if not result["statcast_data"]:
                return {
                    "error": (
                        f"No Statcast data found for the given date range ({start_date} to {end_date}). The date "
                        "range may have resulted in nothing being returned."
                    )
                }
            size_error = check_result_size(result, "player")
            if size_error:
                return size_error
            return result
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_statcast_team(
        team: str,
        start_date: str,
        end_date: str,
        fields: List[str],
    ) -> dict:
        """
        Retrieve MLB Statcast data for all players on a team over a date range.

        Parameters
        ----------
        team : str
            Team ID or team name (see MLB team list for valid values).
        start_date : str
            The start date in 'YYYY-MM-DD' format. Required.
        end_date : str
            The end date in 'YYYY-MM-DD' format. Required.
        fields: List[str]
            The field to return. If not provided, defaults to all fields. Available fields:
                 pitch_type, game_date, release_speed, release_pos_x, release_pos_z, player_name, batter, pitcher,
                 events, description, spin_dir, spin_rate_deprecated, break_angle_deprecated, break_length_deprecated,
                 zone, des, game_type, stand, p_throws, home_team, away_team, type, hit_location, bb_type, balls,
                 strikes, game_year, pfx_x, pfx_z, plate_x, plate_z, on_3b, on_2b, on_1b, outs_when_up, inning,
                 inning_topbot, hc_x, hc_y, tfs_deprecated, tfs_zulu_deprecated, umpire, sv_id, vx0, vy0, vz0, ax, ay,
                 az, sz_top, sz_bot, hit_distance_sc, launch_speed, launch_angle, effective_speed, release_spin_rate,
                 release_extension, game_pk, fielder_2, fielder_3, fielder_4, fielder_5, fielder_6, fielder_7,
                 fielder_8, fielder_9, release_pos_y, estimated_ba_using_speedangle,
                 estimated_woba_using_speedangle, woba_value, woba_denom, babip_value, iso_value, launch_speed_angle,
                 at_bat_number, pitch_number, pitch_name, home_score, away_score, bat_score, fld_score,
                 post_away_score, post_home_score, post_bat_score, post_fld_score, if_fielding_alignment,
                 of_fielding_alignment, spin_axis, delta_home_win_exp, delta_run_exp, bat_speed, swing_length,
                 estimated_slg_using_speedangle, delta_pitcher_run_exp, hyper_speed, home_score_diff, bat_score_diff,
                 home_win_exp, bat_win_exp, age_pit_legacy, age_bat_legacy, age_pit, age_bat, n_thruorder_pitcher,
                 n_priorpa_thisgame_player_at_bat, pitcher_days_since_prev_game, batter_days_since_prev_game,
                 pitcher_days_until_next_game, batter_days_until_next_game, api_break_z_with_gravity,
                 api_break_x_arm, api_break_x_batter_in, arm_angle, attack_angle, attack_direction, swing_path_tilt,
                 intercept_ball_minus_batter_pos_x_inches, intercept_ball_minus_batter_pos_y_inches
        Returns
        -------
        dict
            Dictionary with Statcast data for all players on the team. If the result is too large, returns an error
            message.
        Notes
        -----
        This uses the pybaseball `statcast` function, which returns all Statcast events for the specified team and date
        range. See the official documentation for more details:
        https://github.com/jldbc/pybaseball/tree/master/docs
        """
        try:
            # Validate date range
            date_error = validate_date_range(start_date, end_date)
            if date_error:
                return date_error
            abbreviation = get_team_abbreviation_from_name(team)
            if not abbreviation:
                return {"error": f"Could not find 3-letter abbreviation for team '{team}'"}
            data = statcast(start_date, end_date, team=abbreviation)
            # Convert all columns to string to ensure JSON serializability
            data = data.astype(str)
            records = data.to_dict(orient="records")
            # Always include batter and pitcher, plus all requested fields
            filtered_records = []
            for row in records:
                filtered_row = {}
                for key in ["batter", "pitcher", *list(fields)]:
                    if key in row:
                        filtered_row[key] = row[key]
                filtered_records.append(filtered_row)
            result = {"statcast_data": filtered_records}
            if not result["statcast_data"]:
                return {
                    "error": (
                        f"No Statcast data found for the given date range ({start_date} to {end_date}). The date "
                        "range may have resulted in nothing being returned."
                    )
                }
            size_error = check_result_size(result, "team")
            if size_error:
                return size_error
            return result
        except Exception as e:
            return {"error": str(e)}
