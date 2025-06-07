from datetime import datetime
from typing import List, Optional

import mlbstatsapi
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/mlb", tags=["MLB"])
mlb = mlbstatsapi.Mlb()


def get_multiple_player_stats(mlb, person_ids: list, stats: list, groups: list, season: int = None, **params) -> dict:
    """
    returns stat data for a team

    Parameters
    ----------
    person_ids : list
        the person ids
    stats : list
        list of stat types. List of statTypes can be found at https://statsapi.mlb.com/api/v1/statTypes
    groups : list
        list of stat grous. List of statGroups can be found at https://statsapi.mlb.com/api/v1/statGroups

    Other Parameters
    ----------------
    season : str
        Insert year to return team stats for a particular season, season=2018
    eventType : str
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
    params['stats'] = stats
    params['group'] = groups

    hydrate_arr = []
    if groups:
        hydrate_arr.append(f'group=[{",".join(groups)}]')
    if stats:
        hydrate_arr.append(f'type=[{",".join(stats)}]')
    if season:
        hydrate_arr.append(f'season={season}')

    mlb_data = mlb._mlb_adapter_v1.get(endpoint=f'people?personIds={",".join(person_ids)}&hydrate=stats({",".join(hydrate_arr)})')
    if 400 <= mlb_data.status_code <= 499:
        return {}
    
    splits = []

    for person in mlb_data.data['people']:
        if 'stats' in person and person['stats']:
            splits.append(mlb_module.create_split_data(person['stats']))

    return splits


def get_sabermetrics_for_players(mlb, player_ids: list, season: int, stat_name: str = None, group: str = "hitting") -> dict:
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
    group : str
        The stat group ('hitting' or 'pitching'). Default is 'hitting'.
    
    Returns
    -------
    dict
        Dictionary containing player sabermetrics data
    """
    
    # Build the API endpoint URL
    endpoint = f'stats?stats=sabermetrics&group={group}&sportId=1&season={season}'
    
    # Make the API call directly
    response = mlb._mlb_adapter_v1.get(endpoint=endpoint)
    
    if 400 <= response.status_code <= 499:
        return {"error": f"API error: {response.status_code}"}
    
    if not response.data or 'stats' not in response.data:
        return {"error": "No stats data found"}
    
    # Extract the relevant data
    result = {"season": season, "group": group, "players": []}
    
    # Filter for our specific players
    player_ids_int = [int(pid) for pid in player_ids]
    
    for stat_group in response.data['stats']:
        if 'splits' in stat_group:
            for split in stat_group['splits']:
                if 'player' in split and split['player']['id'] in player_ids_int:
                    player_data = {
                        "player_id": split['player']['id'],
                        "player_name": split['player'].get('fullName', 'Unknown'),
                        "position": split.get('position', {}).get('abbreviation', 'N/A'),
                        "team": split.get('team', {}).get('name', 'N/A'),
                        "team_id": split.get('team', {}).get('id', None)
                    }
                    
                    # Extract the sabermetric stats
                    if 'stat' in split:
                        if stat_name:
                            # Return only the specific stat requested
                            if stat_name.lower() in split['stat']:
                                player_data[stat_name] = split['stat'][stat_name.lower()]
                            else:
                                player_data[stat_name] = None
                                player_data["available_stats"] = list(split['stat'].keys())
                        else:
                            # Return all sabermetric stats
                            player_data["sabermetrics"] = split['stat']
                    
                    result["players"].append(player_data)
    
    return result


@router.get(
    "/standings",
    operation_id="get_mlb_standings",
    description="""
Get current MLB standings for a given season (year). If no season is provided, defaults to the current year. 

Returns the standings for both the American League (AL) and National League (NL).

Example:
- `/mlb/standings` (returns current season standings)
- `/mlb/standings?season=2022` (returns 2022 season standings)
""",
)
async def get_standings(
    season: Optional[int] = None,
    standingsTypes: Optional[str] = None,
    date: Optional[str] = None,
    hydrate: Optional[str] = None,
    fields: Optional[str] = None,
    league: str = "both",
):
    """
    Get current MLB standings for a given season (year).

    Parameters:
        season (Optional[int]): The year for which to retrieve standings. Defaults to the current year if not provided.
        standingsTypes (Optional[str]): The type of standings to retrieve (e.g., 'regularSeason', 'wildCard', etc.). Optional.
        date (Optional[str]): Specific date (YYYY-MM-DD) for which to retrieve standings. Optional.
        hydrate (Optional[str]): Additional data to hydrate in the response. Optional.
        fields (Optional[str]): Comma-separated list of fields to include in the response. Optional.
        league (str): Filter by league. Accepts 'AL', 'NL', or 'both' (default: 'both').

    Returns:
        dict: Standings for the specified league(s) and season.

    Examples:
        - Get current season standings for both leagues:
            /mlb/standings
        - Get 2022 season standings for the American League:
            /mlb/standings?season=2022&league=AL
        - Get standings for a specific date:
            /mlb/standings?date=2024-06-01
        - Get wildcard standings for the National League:
            /mlb/standings?standingsTypes=wildCard&league=NL
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
            raise HTTPException(status_code=400, detail="Invalid league parameter. Use 'AL', 'NL', or 'both'.")
        return {"standings": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/schedule",
    operation_id="get_mlb_schedule",
    description="""
Get MLB schedule for a specific date, date range, sport ID, or team ID.

Examples:
- `/mlb/schedule?date=2024-06-01` (returns all games scheduled for June 1, 2024)
- `/mlb/schedule?start_date=2024-06-01&end_date=2024-06-07` (returns all games scheduled from June 1-7, 2024)
- `/mlb/schedule?team_id=147` (returns games for the Yankees)
""",
)
async def get_schedule(
    date: str = None,
    start_date: str = None,
    end_date: str = None,
    sport_id: int = 1,
    team_id: int = None,
):
    """Get MLB schedule using various parameters"""
    try:
        schedule = mlb.get_schedule(
            date=date,
            start_date=start_date,
            end_date=end_date,
            sport_id=sport_id,
            team_id=team_id,
        )
        return {"schedule": schedule}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/team/{team_id}",
    operation_id="get_mlb_team_info",
    description="""
Get information about a specific team by ID.

Returns details such as team name, location, venue, and league.

Example:
- `/mlb/team/147` (returns info for the New York Yankees)
""",
)
async def get_team_info(
    team_id: int,
    season: int = None,
    sport_id: int = None,
    hydrate: str = None,
    fields: str = None,
):
    """Get information about a specific team by ID (using get_team)"""
    try:
        params = {}
        if season is not None:
            params["season"] = season
        if sport_id is not None:
            params["sportId"] = sport_id
        if hydrate is not None:
            params["hydrate"] = hydrate
        if fields is not None:
            params["fields"] = fields
        team_info = mlb.get_team(team_id, **params)
        return {"team_info": team_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/player/{player_id}",
    operation_id="get_mlb_player_info",
    description="""
Get information about a specific player by ID.

Returns player details such as name, position, team, and biographical info.

Example:
- `/mlb/player/592450` (returns info for Aaron Judge)
""",
)
async def get_player_info(player_id: int):
    """Get information about a specific player by ID (using get_person)"""
    try:
        player_info = mlb.get_person(player_id)
        return {"player_info": player_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/boxscore",
    operation_id="get_mlb_boxscore",
    description="""
Get boxscore for a specific game by game_id.

Returns detailed boxscore information including lineups, player stats, and scoring summary.

Optional parameters:
- `timecode`: A specific timecode for the boxscore snapshot (optional, rarely used).
- `fields`: Comma-separated list of fields to include in the response (optional).

Examples:
- `/mlb/boxscore?game_id=715793` (returns boxscore for the specified game)
- `/mlb/boxscore?game_id=715793&fields=teams,players` (returns only teams and players fields)
- `/mlb/boxscore?game_id=715793&timecode=20240601_150000` (returns boxscore at a specific timecode)
""",
)
async def boxscore(game_id: int, timecode: str = None, fields: str = None):
    """
    Get boxscore for a specific game by game_id.

    Parameters:
        game_id (int): The game ID for which to retrieve the boxscore.
        timecode (str, optional): A specific timecode for the boxscore snapshot (format: YYYYMMDD_HHMMSS). Optional.
        fields (str, optional): Comma-separated list of fields to include in the response. Optional.

    Returns:
        dict: Boxscore information for the specified game.

    Examples:
        - Get boxscore for a game:
            /mlb/boxscore?game_id=715793
        - Get boxscore with specific fields:
            /mlb/boxscore?game_id=715793&fields=teams,players
        - Get boxscore at a specific timecode:
            /mlb/boxscore?game_id=715793&timecode=20240601_150000
    """
    try:
        params = {}
        if timecode is not None:
            params["timecode"] = timecode
        if fields is not None:
            params["fields"] = fields
        boxscore = mlb.get_game_box_score(game_id, **params)
        return boxscore
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/game_highlights",
    operation_id="get_mlb_game_highlights",
    description="""
Get game highlights for a specific game by game_id.

Returns video and media highlights for the specified game.

Example:
- `/mlb/game_highlights?game_id=715793` (returns highlights for the specified game)
""",
)
async def game_highlights(game_id: int):
    try:
        highlights = mlb.get_game(game_id).content.highlights
        return highlights
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/game_pace",
    operation_id="get_mlb_game_pace",
    description="""
Get game pace statistics for a given season.

Returns average game duration and pace-related stats for the specified season.

Example:
- `/mlb/game_pace?season=2023` (returns game pace stats for 2023)
""",
)
async def game_pace(season: int, sport_id: int = 1):
    try:
        gamepace = mlb.get_gamepace(str(season), sport_id=sport_id)
        return gamepace
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/game_scoring_plays",
    operation_id="get_mlb_game_scoring_plays",
    description="""
Get plays for a specific game by game_id, with optional filtering by eventType.

Returns a list of plays in the game. If eventType is provided, only plays matching that eventType are returned.

Optional parameters:
- `eventType`: Filter plays by this event type (e.g., 'scoring_play', 'home_run', etc.). If not provided, returns all plays.
- `timecode`: A specific timecode for the play-by-play snapshot (optional, rarely used). Format: YYYYMMDD_HHMMSS
- `fields`: Comma-separated list of fields to include in the response (optional).

Examples:
- `/mlb/game_scoring_plays?game_id=715793` (returns all plays for the specified game)
- `/mlb/game_scoring_plays?game_id=715793&eventType=scoring_play` (returns only scoring plays)
- `/mlb/game_scoring_plays?game_id=715793&eventType=home_run` (returns only home run plays)
- `/mlb/game_scoring_plays?game_id=715793&fields=allplays,result` (returns only allplays and result fields)
- `/mlb/game_scoring_plays?game_id=715793&timecode=20240601_150000` (returns plays at a specific timecode)
""",
)
async def game_scoring_plays(
    game_id: int,
    eventType: str = None,
    timecode: str = None,
    fields: str = None
):
    """
    Get plays for a specific game by game_id, with optional filtering by eventType.

    Parameters:
        game_id (int): The game ID for which to retrieve plays.
        eventType (str, optional): Filter plays by this event type (e.g., 'scoring_play', 'home_run'). Optional.
        timecode (str, optional): A specific timecode for the play-by-play snapshot (format: YYYYMMDD_HHMMSS). Optional.
        fields (str, optional): Comma-separated list of fields to include in the response. Optional.

    Returns:
        list: Plays in the game, optionally filtered by eventType.

    Examples:
        - Get all plays for a game:
            /mlb/game_scoring_plays?game_id=715793
        - Get only scoring plays:
            /mlb/game_scoring_plays?game_id=715793&eventType=scoring_play
        - Get only home run plays:
            /mlb/game_scoring_plays?game_id=715793&eventType=home_run
        - Get plays with specific fields:
            /mlb/game_scoring_plays?game_id=715793&fields=allplays,result
        - Get plays at a specific timecode:
            /mlb/game_scoring_plays?game_id=715793&timecode=20240601_150000
    """
    try:
        params = {}
        if timecode is not None:
            params["timecode"] = timecode
        if fields is not None:
            params["fields"] = fields
        plays = mlb.get_game_play_by_play(game_id, **params)
        if eventType:
            filtered_plays = [
                play for play in plays.allplays if getattr(play.result, "eventType", None) == eventType
            ]
            return filtered_plays
        else:
            return plays.allplays
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/linescore",
    operation_id="get_mlb_linescore",
    description="""
Get linescore for a specific game by game_id.

Returns inning-by-inning linescore for the specified game, including runs, hits, and errors.

Example:
- `/mlb/linescore?game_id=715793` (returns linescore for the specified game)
""",
)
async def linescore(game_id: int):
    try:
        linescore = mlb.get_game_line_score(game_id)
        return linescore
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/player_stats",
    operation_id="get_multiple_mlb_player_stats",
    description="""
Get player stats by comma separated player_ids, group, type, season, and optional eventType.

Returns statistical data for a player(s), filtered by stat group (e.g., hitting, pitching), stat type (e.g., season, career), season, and optionally eventType.

Examples:
- `/mlb/player_stats?player_ids=592450,647351&group=hitting&type=season&season=2023` (returns Aaron Judge's and Giancarlo Stanton's 2023 season hitting stats)
- `/mlb/player_stats?player_ids=592450&group=hitting&type=season&season=2023` (returns Aaron Judge's 2023 season hitting stats)
- `/mlb/player_stats?player_ids=592450&type=career` (returns Aaron Judge's career stats)
- `/mlb/player_stats?player_ids=592450&eventType=home_run` (returns stats filtered by eventType 'home_run')
""",
)
async def player_stats(
    player_ids: str, group: str = None, type: str = None, season: int = None, eventType: str = None
):
    try:
        params = {}
        if eventType is not None:
            params["eventType"] = eventType
        stats = get_multiple_player_stats(
            mlb,
            player_ids.split(","),
            stats=[type] if type else None,
            groups=[group] if group else None,
            season=season,
            **params
        )
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/sabermetrics",
    operation_id="get_mlb_sabermetrics",
    description="""
Get sabermetric statistics (including WAR) for multiple players for a specific season.

Returns advanced statistical data like WAR, wOBA, wRC+, and other sabermetric measures.

Examples:
- `/mlb/sabermetrics?player_ids=592450,605141&season=2023` (returns all sabermetrics for Aaron Judge and Mookie Betts in 2023)
- `/mlb/sabermetrics?player_ids=592450&season=2023&stat_name=war` (returns only WAR for Aaron Judge in 2023)
- `/mlb/sabermetrics?player_ids=545361,592450&season=2021&group=hitting` (returns hitting sabermetrics for Mike Trout and Aaron Judge in 2021)
""",
)
async def get_sabermetrics(
    player_ids: str, 
    season: int, 
    stat_name: str = None, 
    group: str = "hitting"
):
    """
    Get sabermetric statistics for multiple players for a specific season.

    Parameters:
        player_ids (str): Comma-separated list of player IDs to get sabermetrics for.
        season (int): The season year to get stats for.
        stat_name (str, optional): Specific sabermetric stat to extract (e.g., 'war', 'woba', 'wrc'). If not provided, returns all sabermetrics.
        group (str): The stat group ('hitting' or 'pitching'). Default is 'hitting'.

    Returns:
        dict: Dictionary containing player sabermetrics data.

    Examples:
        - Get all sabermetrics for multiple players:
            /mlb/sabermetrics?player_ids=592450,605141&season=2023
        - Get only WAR for a specific player:
            /mlb/sabermetrics?player_ids=592450&season=2023&stat_name=war
        - Get pitching sabermetrics:
            /mlb/sabermetrics?player_ids=594798&season=2023&group=pitching
    """
    try:
        result = get_sabermetrics_for_players(
            mlb,
            player_ids.split(","),
            season=season,
            stat_name=stat_name,
            group=group
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/roster",
    operation_id="get_mlb_roster",
    description="""
Get team roster for a specific team by team_id, with optional filters.

Returns the current roster for the specified team, including player IDs and positions.

Optional parameters:
- `rosterType`: Filter by roster type (e.g., 40Man, fullSeason, fullRoster, nonRosterInvitees, active, allTime, depthChart, gameday, coach).
- `season`: Filter by single season (year).
- `date`: Filter by specific date (YYYY-MM-DD).
- `hydrate`: Additional data to hydrate in the response (e.g., person, awards, stats, etc.).
- `fields`: Comma-separated list of fields to include in the response.

Examples:
- `/mlb/roster?team_id=147` (returns the New York Yankees roster)
- `/mlb/roster?team_id=147&rosterType=40Man&season=2018` (returns 40-man roster for 2018)
- `/mlb/roster?team_id=147&date=2024-06-01` (returns roster for a specific date)
- `/mlb/roster?team_id=147&hydrate=person(stats)` (returns roster with hydrated person stats)
""",
)
async def roster(
    team_id: int,
    rosterType: str = None,
    season: str = None,
    date: str = None,
    hydrate: str = None,
    fields: str = None
):
    try:
        params = {}
        if rosterType is not None:
            params["rosterType"] = rosterType
        if season is not None:
            params["season"] = season
        if date is not None:
            params["date"] = date
        if hydrate is not None:
            params["hydrate"] = hydrate
        if fields is not None:
            params["fields"] = fields
        roster = mlb.get_team_roster(team_id, **params)
        return roster
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Add new endpoints
@router.get(
    "/search_players",
    operation_id="get_mlb_search_players",
    description="""
Search for players by name.

Returns player ID(s) matching the given name.

Example:
- `/mlb/search_players?fullname=Aaron Judge` (returns IDs for players named Aaron Judge)
""",
)
async def search_players(
    fullname: str, sport_id: int = 1, search_key: str = "fullname"
):
    try:
        player_ids = mlb.get_people_id(
            fullname, sport_id=sport_id, search_key=search_key
        )
        return {"player_ids": player_ids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/players",
    operation_id="get_mlb_players",
    description="""
Get all players for a specific sport.

Returns a list of all players for the specified sport ID.

Optional parameters:
- `season`: Filter players by a specific season (year).

Examples:
- `/mlb/players` (returns all current MLB players)
- `/mlb/players?season=2023` (returns all MLB players for the 2023 season)
""",
)
async def get_players(sport_id: int = 1, season: int = None):
    try:
        params = {}
        if season is not None:
            params["season"] = season
        players = mlb.get_people(sport_id=sport_id, **params)
        return {"players": players}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/draft/{year}",
    operation_id="get_mlb_draft",
    description="""
Get draft information for a specific year.

Returns draft picks and details for the specified year.

Example:
- `/mlb/draft/2023` (returns 2023 MLB draft information)
""",
)
async def get_draft(year_id: int):
    try:
        draft = mlb.get_draft(year_id)
        return {"draft": draft}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/awards/{award_id}",
    operation_id="get_mlb_awards",
    description="""
Get award recipients for a specific award.

Returns recipients of the specified award.

Example:
- `/mlb/awards/MLBMVP` (returns MVP award recipients)
""",
)
async def get_awards(award_id: int):
    try:
        awards = mlb.get_awards(award_id)
        return {"awards": awards}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/search_teams",
    operation_id="get_mlb_search_teams",
    description="""
Search for teams by name.

Returns team ID(s) matching the given name. Searches across full name, team name, abbreviation, and location.

Example:
- `/mlb/search_teams?team_name=Yankees` (returns IDs for teams named Yankees)
""",
)
async def search_teams(team_name: str, search_key: str = "name"):
    try:
        # First try the original method with full name
        team_ids = mlb.get_team_id(team_name, search_key=search_key)
        
        # If no results, try a more comprehensive search
        if not team_ids:
            # Get all teams and search manually
            all_teams = mlb.get_teams(sport_id=1)
            team_ids = []
            search_term = team_name.lower()
            
            for team in all_teams:
                # Search across multiple fields
                fields_to_search = [
                    getattr(team, 'name', ''),
                    getattr(team, 'teamname', ''),
                    getattr(team, 'abbreviation', ''),
                    getattr(team, 'shortname', ''),
                    getattr(team, 'locationname', ''),
                    getattr(team, 'franchisename', ''),
                    getattr(team, 'clubname', '')
                ]
                
                # Check if search term matches any field (case insensitive)
                for field in fields_to_search:
                    if search_term in field.lower():
                        team_ids.append(team.id)
                        break  # Avoid adding the same team multiple times
        
        return {"team_ids": team_ids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/teams",
    operation_id="get_mlb_teams",
    description="""
Get all teams for a specific sport.

Returns a list of all teams for the specified sport ID.

Optional parameters:
- `season`: Filter teams by a specific season (year).

Examples:
- `/mlb/teams` (returns all current MLB teams)
- `/mlb/teams?season=2023` (returns all MLB teams for the 2023 season)
""",
)
async def get_teams(sport_id: int = 1, season: int = None):
    try:
        params = {}
        if season is not None:
            params["season"] = season
        teams = mlb.get_teams(sport_id=sport_id, **params)
        return {"teams": teams}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))