# MLB API MCP Server

[![CI Status](https://github.com/guillochon/mlb-api-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/guillochon/mlb-api-mcp/actions/workflows/ci.yml)
![License](https://img.shields.io/github/license/guillochon/mlb-api-mcp)
[![smithery badge](https://smithery.ai/badge/@guillochon/mlb-api-mcp)](https://smithery.ai/server/@guillochon/mlb-api-mcp)

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

### Installing via Smithery

To install MLB API Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@guillochon/mlb-api-mcp):

```bash
npx -y @smithery/cli install @guillochon/mlb-api-mcp --client claude
```

### Option 1: Local Installation

1. Install uv if you haven't already:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Clone the repository:
```bash
git clone https://github.com/guillochon/mlb-api-mcp.git
cd mlb-api-mcp
```

3. Create and activate a virtual environment:

```bash
uv venv
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows
```

4. Install dependencies:

```bash
uv pip install -e .
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

3. Run the container (default timezone is UTC, uses Python 3.12):
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
# For stdio transport (default, for MCP clients like Smithery)
uv run python main.py

# For HTTP transport (for web access)
uv run python main.py --http
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

- **mcp[cli]**: MCP-compliant server framework with CLI support
- **FastAPI**: Web framework for HTTP transport
- **python-mlb-statsapi**: Official MLB Statistics API wrapper
- **uvicorn[standard]**: ASGI server for running the app
- **websockets**: WebSocket support (latest version to avoid deprecation warnings)
- **python-dotenv**: Environment variable management
- **httpx**: HTTP client for API requests

## Development

This project uses:
- Python 3.10+ (Docker uses Python 3.12)
- FastMCP for the web framework
- uv for fast Python package management
- Hatchling for build management
- MLB Stats API for comprehensive baseball data access
- Ruff for linting and formatting

### Setup Pre-commit Hooks

1. Install pre-commit:

```bash
pip install pre-commit
```

2. Initialize pre-commit hooks:

```bash
pre-commit install
```

Now, the linting checks will run automatically whenever you commit code. You can also run them manually:

```bash
pre-commit run --all-files
```

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is open source. Please check the license file for details.

## Running Tests

To run the test suite locally:

```bash
uv run pytest
```
