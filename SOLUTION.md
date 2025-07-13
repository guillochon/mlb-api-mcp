# Solution for Issue #7: Unable to access /docs endpoint

## Problem Analysis

The original issue was that users couldn't access API documentation at `localhost:8000/docs` or `localhost:8000/mcp/docs`. This happened because:

1. **404 Not Found at `/docs`**: The FastMCP server was configured to serve only the MCP protocol, not standard FastAPI documentation endpoints.

2. **JSON-RPC error at `/mcp/docs`**: The MCP server expected `text/event-stream` content type for MCP protocol communication, but browsers send different content types when accessing endpoints directly.

## Solution

I've implemented a unified server approach that provides both MCP functionality and API documentation on the same port:

### Architecture Changes

1. **Single FastAPI Application**: Everything runs on port 8000
2. **MCP Server**: Mounted at `/mcp/` path
3. **Documentation**: Standard FastAPI docs at `/docs` and `/redoc`
4. **Additional Endpoints**: Health checks and tool listing

### Available Endpoints

All endpoints are now available on port 8000:

- `GET /` - Redirects to documentation
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative documentation (ReDoc)
- `GET /health/` - Health check endpoint
- `GET /mcp/info` - Information about the MCP server
- `GET /tools/` - List all available MCP tools with descriptions
- `POST /mcp/` - MCP protocol endpoint (for MCP clients)

### Usage Instructions

#### Running with Docker

```bash
# Build the image
docker build -t mlb-api-mcp .

# Run the container
docker run -p 8000:8000 mlb-api-mcp
```

#### Running Locally

```bash
# Install dependencies
pip install -e .

# Run the server
python main.py
```

### Accessing the Services

All services are now available on port 8000:

1. **API Documentation**: http://localhost:8000/docs
2. **Health Check**: http://localhost:8000/health/
3. **MCP Server Info**: http://localhost:8000/mcp/info
4. **Available Tools**: http://localhost:8000/tools/
5. **MCP Protocol**: http://localhost:8000/mcp/ (for MCP clients)

## Key Features

- **Single Port**: Everything runs on port 8000 as expected
- **Comprehensive Documentation**: Full Swagger UI with all endpoint details
- **Tools Discovery**: Endpoint to list all available MCP tools
- **Health Monitoring**: Health check endpoint for monitoring
- **MCP Integration**: Seamless MCP protocol support

## Benefits

1. **Solves the 404 Issue**: Documentation is now properly accessible at `/docs`
2. **Fixes JSON-RPC Error**: MCP protocol and HTTP documentation are properly integrated
3. **Simplified Deployment**: Single port reduces complexity
4. **Backward Compatible**: MCP functionality remains unchanged
5. **Easy Discovery**: Tools and server information easily accessible

## Testing

```bash
# Test documentation access
curl http://localhost:8000/docs

# Test health check
curl http://localhost:8000/health/

# Test MCP server info
curl http://localhost:8000/mcp/info

# Test tools list
curl http://localhost:8000/tools/

# Test MCP protocol (with proper headers)
curl -H "Accept: text/event-stream" http://localhost:8000/mcp/
```

## Docker Compose Example

For easier deployment, you can use this docker-compose.yml:

```yaml
version: '3.8'
services:
  mlb-api-mcp:
    build: .
    ports:
      - "8000:8000"
    environment:
      - TZ=UTC
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3
```

This solution provides a complete fix for the original issue while maintaining all existing MCP functionality on a single port as expected.