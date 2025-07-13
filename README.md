# MLB API MCP Server

[![CI Status](https://github.com/guillochon/mlb-api-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/guillochon/mlb-api-mcp/actions/workflows/ci.yml)
![License](https://img.shields.io/github/license/guillochon/mlb-api-mcp)

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that provides comprehensive access to MLB statistics and baseball data through a FastAPI-based interface.

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

### API Endpoints

#### MLB Endpoints (`/mlb/`)
- `GET /mlb/standings` - Current MLB standings with league and season filters
- `GET /mlb/schedule` - Game schedules for specific dates, ranges, or teams
- `GET /mlb/team/{team_id}` - Detailed team information
- `GET /mlb/player/{player_id}` - Player biographical information
- `GET /mlb/boxscore` - Complete game boxscores
- `GET /mlb/linescore` - Inning-by-inning game scores
- `GET /mlb/game_highlights` - Video highlights for games
- `GET /mlb/game_scoring_plays` - Play-by-play data with event filtering
- `GET /mlb/game_pace` - Game duration and pace statistics
- `GET /mlb/game_lineup` - Detailed lineup information for games
- `GET /mlb/player_stats` - Traditional player statistics
- `GET /mlb/sabermetrics` - Advanced sabermetric statistics (WAR, wOBA, etc.)
- `GET /mlb/roster` - Team rosters with various roster types
- `GET /mlb/search_players` - Search players by name
- `GET /mlb/search_teams` - Search teams by name
- `GET /mlb/players` - All players for a sport/season
- `GET /mlb/teams` - All teams for a sport/season
- `GET /mlb/draft/{year}` - Draft information by year
- `GET /mlb/awards/{award_id}` - Award recipients

#### Generic Endpoints
- `GET /current_date` - Current date
- `GET /current_time` - Current time

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

3. Run the container (default timezone is UTC):
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
- Available endpoints with detailed descriptions
- Request/response schemas
- Interactive testing interface
- Parameter descriptions and examples
- List of all available MCP tools at `http://localhost:8000/tools/`

## Dependencies

- **FastAPI**: Modern web framework for building APIs
- **fastapi-mcp**: MCP integration for FastAPI
- **python-mlb-statsapi**: Official MLB Statistics API wrapper

## Development

This project uses:
- Python 3.10+
- FastAPI for the web framework
- Hatchling for build management
- MLB Stats API for comprehensive baseball data access

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is open source. Please check the license file for details.

## Running Tests

To run the test suite locally:

```bash
pip install -r requirements.txt  # or use poetry install if using Poetry
pytest
```