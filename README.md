# MLB API MCP Server

[![CI Status](https://github.com/guillochon/mlb-api-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/guillochon/mlb-api-mcp/actions/workflows/ci.yml)
![License](https://img.shields.io/github/license/guillochon/mlb-api-mcp)

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that provides comprehensive access to MLB statistics and baseball data through a FastMCP-based interface.

## Overview

This MCP server acts as a bridge between AI applications and MLB data sources, enabling seamless integration of baseball statistics, game information, player data, and more into AI workflows and applications.

## Features

### MLB Data Access
- **Current standings** for all MLB teams with flexible filtering by league, season, and date
- **Game schedules** and results with date range support
- **Player statistics** including traditional and sabermetric stats (WAR, wOBA, wRC+)
- **Team information** and rosters with various roster types
- **Live game data** including boxscores, linescores, and play-by-play
- **Game highlights** and scoring plays
- **Player and team search** functionality
- **Draft information** and award recipients
- **Game pace statistics** and lineup information

### MCP Tools

All MLB/statistics/game/player/team/etc. functionality is exposed as MCP tools, not as RESTful HTTP endpoints. These tools are accessible via the `/mcp/` endpoint using the MCP protocol. For a list of available tools and their descriptions, visit `/tools/` when the server is running.

#### Key MCP Tools
- `get_mlb_standings` - Current MLB standings with league and season filters
- `get_mlb_schedule` - Game schedules for specific dates, ranges, or teams
- `get_mlb_team_info` - Detailed team information
- `get_mlb_player_info` - Player biographical information
- `get_mlb_boxscore` - Complete game boxscores
- `get_mlb_linescore` - Inning-by-inning game scores
- `get_mlb_game_highlights` - Video highlights for games
- `get_mlb_game_scoring_plays` - Play-by-play data with event filtering
- `get_mlb_game_pace` - Game duration and pace statistics
- `get_mlb_game_lineup` - Detailed lineup information for games
- `get_multiple_mlb_player_stats` - Traditional player statistics
- `get_mlb_sabermetrics` - Advanced sabermetric statistics (WAR, wOBA, etc.)
- `get_mlb_roster` - Team rosters with various roster types
- `get_mlb_search_players` - Search players by name
- `get_mlb_search_teams` - Search teams by name
- `get_mlb_players` - All players for a sport/season
- `get_mlb_teams` - All teams for a sport/season
- `get_mlb_draft` - Draft information by year
- `get_mlb_awards` - Award recipients
- `get_current_date` - Current date
- `get_current_time` - Current time

For the full list and detailed descriptions, see `/tools/` or `/docs` when the server is running.

### HTTP Endpoints

The following HTTP endpoints are available:
- `/` - Redirects to `/docs`
- `/docs` - Interactive API documentation and tool listing
- `/health/` - Health check endpoint
- `/mcp/info` - MCP server information
- `/tools/` - List of all available MCP tools
- `/mcp/` (POST) - MCP protocol endpoint for MCP-compatible clients

> **Note:** There are no RESTful HTTP endpoints for MLB/statistics/game/player/team/etc. All such functionality is accessed via MCP tools through the `/mcp/` endpoint.

### MCP Integration
- Compatible with MCP-enabled AI applications
- Tool-based interaction model with comprehensive endpoint descriptions
- Automatic API documentation generation
- Schema validation and type safety
- Full response schema descriptions for better AI integration

## Installation

### Option 1: Local Installation

1. Clone the repository:
```bash
git clone https://github.com/guillochon/mlb-api-mcp.git
cd mlb-api-mcp
```

2. Install dependencies:
```bash
pip install -e .
```

### Option 2: Docker Installation

1. Clone the repository:
```bash
git clone https://github.com/guillochon/mlb-api-mcp.git
cd mlb-api-mcp
```

2. Build the Docker image:
```bash
docker build -t mlb-api-mcp .
```

3. Run the container (default timezone is UTC, uses Python 3.11):
```bash
docker run -p 8000:8000 mlb-api-mcp
```

#### Setting the Timezone

To run the container in your local timezone, pass the `TZ` environment variable (e.g., for New York):

```bash
docker run -e TZ=America/New_York -p 8000:8000 mlb-api-mcp
```

Replace `America/New_York` with your desired [IANA timezone name](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).

The server will be available at `http://localhost:8000` with:
- **MCP Server**: `http://localhost:8000/mcp/`
- **Documentation**: `http://localhost:8000/docs`

#### Docker Options

You can also run the container with additional options:

```bash
# Run in detached mode
docker run -d -p 8000:8000 --name mlb-api-server mlb-api-mcp

# Run with custom port mapping
docker run -p 3000:8000 mlb-api-mcp

# View logs
docker logs mlb-api-server

# Stop the container
docker stop mlb-api-server

# Remove the container
docker rm mlb-api-server
```

## Usage

### Starting the Server

Run the MCP server locally:
```bash
python main.py
```

The server will start with:
- **MCP Server** on `http://localhost:8000/mcp/`
- **Interactive API documentation** available at `http://localhost:8000/docs`

### MCP Client Integration

This server can be integrated into any MCP-compatible application. The server provides tools for:
- Retrieving team standings and schedules
- Getting comprehensive player and team statistics
- Accessing live game data and historical records
- Searching for players and teams
- Fetching sabermetric statistics like WAR
- And much more...

## API Documentation

Once the server is running, visit `http://localhost:8000/docs` for comprehensive API documentation including:
- Available HTTP endpoints
- List of all available MCP tools at `/tools/`
- Tool descriptions and parameters
- Interactive testing interface
- Parameter descriptions and examples

## Dependencies

- **fastmcp**: MCP-compliant server framework (actual server)
- **FastAPI**: Required for compatibility (not used as the serving layer)
- **python-mlb-statsapi**: Official MLB Statistics API wrapper
- **uvicorn[standard]**: ASGI server for running the app

## Development

This project uses:
- Python 3.10+ (Docker uses Python 3.11)
- FastMCP for the web framework
- Hatchling for build management
- MLB Stats API for comprehensive baseball data access

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is open source. Please check the license file for details.

## Running Tests

To run the test suite locally:

```bash
pip install -e .
pytest
```