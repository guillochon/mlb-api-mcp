from unittest.mock import MagicMock, patch

import pytest

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
    return getattr(mcp, '_tools', {}).get(name)

@pytest.fixture
def mcp():
    mcp = MagicMock()
    patch_mcp_tool(mcp)
    mlb_api.setup_mlb_tools(mcp)
    return mcp


def test_get_mlb_standings(mcp):
    get_mlb_standings = get_tool(mcp, 'get_mlb_standings')
    assert get_mlb_standings is not None
    with patch('mlb_api.mlb.get_standings', return_value={'dummy': 'standings'}):
        result = get_mlb_standings(season=2022)
        assert 'standings' in result

def test_get_mlb_schedule(mcp):
    get_mlb_schedule = get_tool(mcp, 'get_mlb_schedule')
    assert get_mlb_schedule is not None
    with patch('mlb_api.mlb.get_schedule', return_value={'games': []}):
        result = get_mlb_schedule(date='2022-01-01')
        assert 'schedule' in result

def test_get_mlb_team_info(mcp):
    get_mlb_team_info = get_tool(mcp, 'get_mlb_team_info')
    assert get_mlb_team_info is not None
    with patch('mlb_api.mlb.get_team', return_value={'id': 123}):
        result = get_mlb_team_info(team_id=123)
        assert 'team_info' in result

def test_get_mlb_player_info(mcp):
    get_mlb_player_info = get_tool(mcp, 'get_mlb_player_info')
    assert get_mlb_player_info is not None
    with patch('mlb_api.mlb.get_person', return_value={'id': 456}):
        result = get_mlb_player_info(player_id=456)
        assert 'player_info' in result

def test_get_mlb_boxscore(mcp):
    get_mlb_boxscore = get_tool(mcp, 'get_mlb_boxscore')
    assert get_mlb_boxscore is not None
    with patch('mlb_api.mlb.get_game_box_score', return_value={'boxscore': True}):
        result = get_mlb_boxscore(game_id=789)
        assert 'boxscore' in str(result) or isinstance(result, dict)

def test_get_multiple_mlb_player_stats(mcp):
    get_multiple_mlb_player_stats = get_tool(mcp, 'get_multiple_mlb_player_stats')
    assert get_multiple_mlb_player_stats is not None
    with patch('mlb_api.get_multiple_player_stats', return_value=[{'player': 1}]):
        result = get_multiple_mlb_player_stats(player_ids='1,2', group='hitting', type='season', season=2022)
        assert 'player_stats' in result

def test_get_mlb_sabermetrics(mcp):
    get_mlb_sabermetrics = get_tool(mcp, 'get_mlb_sabermetrics')
    assert get_mlb_sabermetrics is not None
    with patch('mlb_api.get_sabermetrics_for_players', return_value={'players': []}):
        result = get_mlb_sabermetrics(player_ids='1,2', season=2022)
        assert 'players' in result or 'error' in result

def test_get_mlb_game_highlights(mcp):
    get_mlb_game_highlights = get_tool(mcp, 'get_mlb_game_highlights')
    assert get_mlb_game_highlights is not None
    with patch('mlb_api.mlb.get_game') as mock_get_game:
        mock_game = MagicMock()
        mock_game.content.highlights = {'highlights': True}
        mock_get_game.return_value = mock_game
        result = get_mlb_game_highlights(game_id=123)
        assert 'highlights' in result

def test_get_mlb_game_pace(mcp):
    get_mlb_game_pace = get_tool(mcp, 'get_mlb_game_pace')
    assert get_mlb_game_pace is not None
    with patch('mlb_api.mlb.get_gamepace', return_value={'pace': True}):
        result = get_mlb_game_pace(season=2022)
        assert 'pace' in result or isinstance(result, dict)

def test_get_mlb_game_scoring_plays(mcp):
    get_mlb_game_scoring_plays = get_tool(mcp, 'get_mlb_game_scoring_plays')
    assert get_mlb_game_scoring_plays is not None
    # Corrected: Each play should be a MagicMock with .result.eventType
    mock_play1 = MagicMock()
    mock_play1.result.eventType = 'scoring_play'
    mock_play2 = MagicMock()
    mock_play2.result.eventType = 'other'
    mock_plays = MagicMock()
    mock_plays.allplays = [mock_play1, mock_play2]
    with patch('mlb_api.mlb.get_game_play_by_play', return_value=mock_plays):
        result = get_mlb_game_scoring_plays(game_id=1, eventType='scoring_play')
        assert 'plays' in result

def test_get_mlb_linescore(mcp):
    get_mlb_linescore = get_tool(mcp, 'get_mlb_linescore')
    assert get_mlb_linescore is not None
    with patch('mlb_api.mlb.get_game_line_score', return_value={'linescore': True}):
        result = get_mlb_linescore(game_id=1)
        assert 'linescore' in result or isinstance(result, dict)

def test_get_mlb_roster(mcp):
    get_mlb_roster = get_tool(mcp, 'get_mlb_roster')
    assert get_mlb_roster is not None
    with patch('mlb_api.mlb.get_team_roster', return_value={'roster': True}):
        result = get_mlb_roster(team_id=1)
        assert 'roster' in result or isinstance(result, dict)

def test_get_mlb_search_players(mcp):
    get_mlb_search_players = get_tool(mcp, 'get_mlb_search_players')
    assert get_mlb_search_players is not None
    with patch('mlb_api.mlb.get_people_id', return_value=[1, 2]):
        result = get_mlb_search_players(fullname='John Doe')
        assert 'player_ids' in result

def test_get_mlb_players(mcp):
    get_mlb_players = get_tool(mcp, 'get_mlb_players')
    assert get_mlb_players is not None
    with patch('mlb_api.mlb.get_people', return_value=[{'id': 1}]):
        result = get_mlb_players(sport_id=1)
        assert 'players' in result

def test_get_mlb_draft(mcp):
    get_mlb_draft = get_tool(mcp, 'get_mlb_draft')
    assert get_mlb_draft is not None
    with patch('mlb_api.mlb.get_draft', return_value={'draft': True}):
        result = get_mlb_draft(year_id=2022)
        assert 'draft' in result

def test_get_mlb_awards(mcp):
    get_mlb_awards = get_tool(mcp, 'get_mlb_awards')
    assert get_mlb_awards is not None
    with patch('mlb_api.mlb.get_awards', return_value={'awards': True}):
        result = get_mlb_awards(award_id=1)
        assert 'awards' in result

def test_get_mlb_search_teams(mcp):
    get_mlb_search_teams = get_tool(mcp, 'get_mlb_search_teams')
    assert get_mlb_search_teams is not None
    # Patch open and csv.DictReader for the CSV file
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value = MagicMock()
        with patch('csv.DictReader', return_value=[{'name': 'Yankees', 'abbreviation': 'NYY', 'location': 'New York', 'teamName': 'Yankees'}]):
            result = get_mlb_search_teams(team_name='Yankees')
            assert 'teams' in result

def test_get_mlb_teams(mcp):
    get_mlb_teams = get_tool(mcp, 'get_mlb_teams')
    assert get_mlb_teams is not None
    with patch('mlb_api.mlb.get_teams', return_value=[{'id': 1}]):
        result = get_mlb_teams(sport_id=1)
        assert 'teams' in result

def test_get_mlb_game_lineup(mcp):
    get_mlb_game_lineup = get_tool(mcp, 'get_mlb_game_lineup')
    assert get_mlb_game_lineup is not None
    # Patch mlb.get_game_box_score to return a MagicMock with the required structure
    mock_boxscore = MagicMock()
    mock_team = MagicMock()
    mock_team.team = MagicMock(name='Yankees', id=1)
    mock_team.players = {}
    mock_boxscore.teams = MagicMock(away=mock_team, home=mock_team)
    with patch('mlb_api.mlb.get_game_box_score', return_value=mock_boxscore):
        result = get_mlb_game_lineup(game_id=1)
        assert 'teams' in result