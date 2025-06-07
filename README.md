# MLB API MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that provides comprehensive access to MLB statistics and baseball data through a FastAPI-based interface.

## Overview

This MCP server acts as a bridge between AI applications and MLB data sources, enabling seamless integration of baseball statistics, game information, player data, and more into AI workflows and applications.

## Features

### MLB Data Access
- **Current standings** for all MLB teams
- **Game schedules** and results 
- **Player statistics** and information
- **Team rosters** and details
- **Live scores** and game data
- **Historical statistics** and records

### API Endpoints
- RESTful API interface via FastAPI
- Comprehensive MLB Stats API integration
- Real-time and historical data access
- Structured JSON responses

### MCP Integration
- Compatible with MCP-enabled AI applications
- Tool-based interaction model
- Automatic API documentation generation
- Schema validation and type safety

## Installation

1. Clone the repository:
```bash
git clone https://github.com/guillochon/mlb-api-mcp.git
cd mlb-api-mcp
```

2. Install dependencies:
```bash
pip install -e .
```

## Usage

### Starting the Server

Run the MCP server locally:
```bash
python main.py
```

The server will start on `http://localhost:8000` with interactive API documentation available at `http://localhost:8000/docs`.

### MCP Client Integration

This server can be integrated into any MCP-compatible application. The server provides tools for:
- Retrieving team standings
- Getting game schedules
- Accessing player statistics
- Fetching team information
- And much more...

## API Documentation

Once the server is running, visit `http://localhost:8000/docs` for comprehensive API documentation including:
- Available endpoints
- Request/response schemas
- Interactive testing interface
- Example usage

## Dependencies

- **FastAPI**: Modern web framework for building APIs
- **fastapi-mcp**: MCP integration for FastAPI
- **python-mlb-statsapi**: Official MLB Statistics API wrapper

## Development

This project uses:
- Python 3.10+
- FastAPI for the web framework
- Hatchling for build management
- MLB Stats API for data access

## Repository Rename

This repository was recently renamed from `mcp` to `mlb-api-mcp` to better reflect its purpose as an MLB-focused MCP server. See [issue #1](../../issues/1) for the full discussion.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is open source. Please check the license file for details.