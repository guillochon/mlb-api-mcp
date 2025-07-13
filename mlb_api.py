from datetime import datetime
from typing import Optional

import mlbstatsapi

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


def setup_mlb_tools(mcp):
    """Setup MLB tools for the MCP server"""
    
    @mcp.tool
    def get_mlb_standings(
        season: Optional[int] = None,
        standingsTypes: Optional[str] = None,
        date: Optional[str] = None,
        hydrate: Optional[str] = None,
        fields: Optional[str] = None,
        league: str = "both",
    ) -> dict:
        """Get current MLB standings for a given season (year).
        
        Args:
            season: The year for which to retrieve standings. Defaults to current year.
            standingsTypes: The type of standings to retrieve (e.g., 'regularSeason', 'wildCard', etc.).
            date: Specific date (YYYY-MM-DD) for which to retrieve standings.
            hydrate: Additional data to hydrate in the response.
            fields: Comma-separated list of fields to include in the response.
            league: Filter by league. Accepts 'AL', 'NL', or 'both' (default: 'both').
            
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

    @mcp.tool
    def get_mlb_schedule(
        date: str = None,
        start_date: str = None,
        end_date: str = None,
        sport_id: int = 1,
        team_id: int = None,
    ) -> dict:
        """Get MLB schedule for a specific date, date range, sport ID, or team ID.
        
        Args:
            date: Specific date (YYYY-MM-DD) for games
            start_date: Start date for date range (YYYY-MM-DD)
            end_date: End date for date range (YYYY-MM-DD)
            sport_id: Sport ID (default: 1 for MLB)
            team_id: Team ID to filter by specific team
            
        Returns:
            dict: Schedule data for the specified parameters
        """
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
            return {"error": str(e)}

    @mcp.tool
    def get_mlb_team_info(
        team_id: int,
        season: int = None,
        sport_id: int = None,
        hydrate: str = None,
        fields: str = None,
    ) -> dict:
        """Get information about a specific team by ID.
        
        Args:
            team_id: The team ID
            season: Season year
            sport_id: Sport ID
            hydrate: Additional data to hydrate
            fields: Comma-separated list of fields to include
            
        Returns:
            dict: Team information
        """
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
            return {"error": str(e)}

    @mcp.tool
    def get_mlb_player_info(player_id: int) -> dict:
        """Get information about a specific player by ID.
        
        Args:
            player_id: The player ID
            
        Returns:
            dict: Player information
        """
        try:
            player_info = mlb.get_person(player_id)
            return {"player_info": player_info}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool
    def get_mlb_boxscore(
        game_id: int, 
        timecode: str = None, 
        fields: str = None
    ) -> dict:
        """Get boxscore for a specific game by game_id.
        
        Args:
            game_id: The game ID
            timecode: Specific timecode for the boxscore snapshot
            fields: Comma-separated list of fields to include
            
        Returns:
            dict: Boxscore information
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
            return {"error": str(e)}

    @mcp.tool
    def get_multiple_mlb_player_stats(
        player_ids: str, 
        group: str = None, 
        type: str = None, 
        season: int = None, 
        eventType: str = None
    ) -> dict:
        """Get player stats by comma separated player_ids, group, type, season, and optional eventType.
        
        Args:
            player_ids: Comma-separated list of player IDs
            group: Stat group (e.g., hitting, pitching)
            type: Stat type (e.g., season, career)
            season: Season year
            eventType: Event type filter
            
        Returns:
            dict: Player statistics
        """
        try:
            player_ids_list = [pid.strip() for pid in player_ids.split(",")]
            
            # Use the helper function from the original code
            stats = ["season", "seasonAdvanced"] if type == "season" else ["career"]
            groups = [group] if group else ["hitting"]
            
            splits = get_multiple_player_stats(mlb, player_ids_list, stats, groups, season)
            return {"player_stats": splits}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool
    def get_mlb_sabermetrics(
        player_ids: str, 
        season: int, 
        stat_name: str = None, 
        group: str = "hitting"
    ) -> dict:
        """Get sabermetric statistics (including WAR) for multiple players for a specific season.
        
        Args:
            player_ids: Comma-separated list of player IDs
            season: Season year
            stat_name: Specific sabermetric stat to extract (e.g., 'war', 'woba', 'wRc')
            group: Stat group ('hitting' or 'pitching')
            
        Returns:
            dict: Sabermetric statistics
        """
        try:
            player_ids_list = [pid.strip() for pid in player_ids.split(",")]
            result = get_sabermetrics_for_players(mlb, player_ids_list, season, stat_name, group)
            return result
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool
    def get_mlb_game_highlights(game_id: int) -> dict:
        """Get game highlights for a specific game by game_id.
        
        Args:
            game_id: The game ID
            
        Returns:
            dict: Game highlights
        """
        try:
            highlights = mlb.get_game(game_id).content.highlights
            return highlights
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool
    def get_mlb_game_pace(season: int, sport_id: int = 1) -> dict:
        """Get game pace statistics for a given season.
        
        Args:
            season: Season year
            sport_id: Sport ID (default: 1 for MLB)
            
        Returns:
            dict: Game pace statistics
        """
        try:
            gamepace = mlb.get_gamepace(str(season), sport_id=sport_id)
            return gamepace
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool
    def get_mlb_game_scoring_plays(
        game_id: int,
        eventType: str = None,
        timecode: str = None,
        fields: str = None
    ) -> dict:
        """Get plays for a specific game by game_id, with optional filtering by eventType.
        
        Args:
            game_id: The game ID
            eventType: Filter plays by this event type (e.g., 'scoring_play', 'home_run')
            timecode: Specific timecode for the play-by-play snapshot
            fields: Comma-separated list of fields to include
            
        Returns:
            dict: Game plays, optionally filtered by eventType
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
                return {"plays": filtered_plays}
            else:
                return {"plays": plays.allplays}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool
    def get_mlb_linescore(game_id: int) -> dict:
        """Get linescore for a specific game by game_id.
        
        Args:
            game_id: The game ID
            
        Returns:
            dict: Linescore information
        """
        try:
            linescore = mlb.get_game_line_score(game_id)
            return linescore
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool
    def get_mlb_roster(
        team_id: int,
        rosterType: str = None,
        season: str = None,
        date: str = None,
        hydrate: str = None,
        fields: str = None
    ) -> dict:
        """Get team roster for a specific team by team_id, with optional filters.
        
        Args:
            team_id: The team ID
            rosterType: Filter by roster type (e.g., 40Man, fullSeason, etc.)
            season: Filter by single season (year)
            date: Filter by specific date (YYYY-MM-DD)
            hydrate: Additional data to hydrate in the response
            fields: Comma-separated list of fields to include
            
        Returns:
            dict: Team roster information
        """
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
            return {"error": str(e)}

    @mcp.tool
    def get_mlb_search_players(
        fullname: str, 
        sport_id: int = 1, 
        search_key: str = "fullname"
    ) -> dict:
        """Search for players by name.
        
        Args:
            fullname: Player name to search for
            sport_id: Sport ID (default: 1 for MLB)
            search_key: Search key (default: "fullname")
            
        Returns:
            dict: Player search results
        """
        try:
            player_ids = mlb.get_people_id(
                fullname, sport_id=sport_id, search_key=search_key
            )
            return {"player_ids": player_ids}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool
    def get_mlb_players(sport_id: int = 1, season: int = None) -> dict:
        """Get all players for a specific sport.
        
        Args:
            sport_id: Sport ID (default: 1 for MLB)
            season: Filter players by a specific season (year)
            
        Returns:
            dict: All players for the specified sport
        """
        try:
            params = {}
            if season is not None:
                params["season"] = season
            players = mlb.get_people(sport_id=sport_id, **params)
            return {"players": players}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool
    def get_mlb_draft(year_id: int) -> dict:
        """Get draft information for a specific year.
        
        Args:
            year_id: Draft year
            
        Returns:
            dict: Draft information
        """
        try:
            draft = mlb.get_draft(year_id)
            return {"draft": draft}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool
    def get_mlb_awards(award_id: int) -> dict:
        """Get award recipients for a specific award.
        
        Args:
            award_id: Award ID
            
        Returns:
            dict: Award recipients
        """
        try:
            awards = mlb.get_awards(award_id)
            return {"awards": awards}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool
    def get_mlb_search_teams(team_name: str, search_key: str = "name") -> dict:
        """Search for teams by name.
        
        Args:
            team_name: Team name to search for
            search_key: Search key (name, abbreviation, location, or "all")
            
        Returns:
            dict: Team search results
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
                if search_key == "name":
                    if team_name.lower() in team["name"].lower():
                        results.append(team)
                elif search_key == "abbreviation":
                    if team_name.lower() in team["abbreviation"].lower():
                        results.append(team)
                elif search_key == "location":
                    if team_name.lower() in team["location"].lower():
                        results.append(team)
                else:
                    # Search all fields
                    if (team_name.lower() in team["name"].lower() or 
                        team_name.lower() in team["abbreviation"].lower() or
                        team_name.lower() in team["location"].lower() or
                        team_name.lower() in team["teamName"].lower()):
                        results.append(team)
            
            return {"teams": results}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool
    def get_mlb_teams(sport_id: int = 1, season: int = None) -> dict:
        """Get all teams for a specific sport.
        
        Args:
            sport_id: Sport ID (default: 1 for MLB)
            season: Filter teams by a specific season (year)
            
        Returns:
            dict: All teams for the specified sport
        """
        try:
            params = {}
            if season is not None:
                params["season"] = season
            teams = mlb.get_teams(sport_id=sport_id, **params)
            return {"teams": teams}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool
    def get_mlb_game_lineup(game_id: int) -> dict:
        """Get lineup information for a specific game by game_id.
        
        Args:
            game_id: The game ID
            
        Returns:
            dict: Game lineup information
        """
        try:
            # Get the boxscore data
            boxscore = mlb.get_game_box_score(game_id)
            
            result = {
                "game_id": game_id,
                "teams": {}
            }
            
            # Process both teams (away and home)
            for team_type in ['away', 'home']:
                if hasattr(boxscore, 'teams') and hasattr(boxscore.teams, team_type):
                    team_data = getattr(boxscore.teams, team_type)
                    
                    team_info = {
                        "team_name": getattr(team_data.team, 'name', 'Unknown'),
                        "team_id": getattr(team_data.team, 'id', None),
                        "players": []
                    }
                    
                    # Get players from the team data
                    if hasattr(team_data, 'players') and team_data.players is not None:
                        players_dict = team_data.players
                        
                        # Extract player information
                        for player_key, player_data in players_dict.items():
                            if player_key.startswith('id'):
                                player_info = {
                                    "player_id": getattr(player_data.person, 'id', None),
                                    "player_name": getattr(player_data.person, 'fullname', 'Unknown'),
                                    "jersey_number": getattr(player_data, 'jerseynumber', None),
                                    "positions": [],
                                    "batting_order": None,
                                    "game_entries": []
                                }
                                
                                # Get position information
                                if hasattr(player_data, 'allpositions') and player_data.allpositions is not None:
                                    for position in player_data.allpositions:
                                        position_info = {
                                            "position": getattr(position, 'abbreviation', None),
                                            "position_name": getattr(position, 'name', None)
                                        }
                                        player_info["positions"].append(position_info)
                                
                                # Get batting order from player data directly
                                if hasattr(player_data, 'battingorder'):
                                    player_info["batting_order"] = getattr(player_data, 'battingorder', None)
                                
                                # Get game entry information (substitutions, etc.)
                                if hasattr(player_data, 'gamestatus'):
                                    game_status = player_data.gamestatus
                                    entry_info = {
                                        "is_on_bench": getattr(game_status, 'isonbench', False),
                                        "is_substitute": getattr(game_status, 'issubstitute', False),
                                        "status": getattr(game_status, 'status', None)
                                    }
                                    player_info["game_entries"].append(entry_info)
                                
                                team_info["players"].append(player_info)
                    
                    # Sort players by batting order (starting lineup first, then substitutes)
                    def sort_key(player):
                        batting_order = player.get("batting_order")
                        if batting_order is None:
                            return 999  # Put non-batting order players at the end
                        return int(str(batting_order).replace('0', ''))  # Handle batting order formatting
                    
                    team_info["players"].sort(key=sort_key)
                    result["teams"][team_type] = team_info
            
            return result
        except Exception as e:
            return {"error": str(e)}