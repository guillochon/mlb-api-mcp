# Solution for Issue #7: Unable to access /docs endpoint

## Problem Analysis

The original issue was that users couldn't access API documentation at `localhost:8000/docs` or `localhost:8000/mcp/docs`. This happened because:

1. **404 Not Found at `/docs`**: The FastMCP server was configured to serve only the MCP protocol, not standard FastAPI documentation endpoints.

2. **JSON-RPC error at `/mcp/docs`**: The MCP server expected `text/event-stream` content type for MCP protocol communication, but browsers send different content types when accessing endpoints directly.

## Solution

I've implemented a dual-server approach that provides both MCP functionality and API documentation:

### Architecture Changes

1. **MCP Server**: Runs on port 8000 at path `/mcp/` (unchanged)
2. **Documentation Server**: New FastAPI server on port 8001 with documentation and utility endpoints

### New Endpoints

#### Documentation Server (Port 8001)
- `GET /` - Redirects to documentation
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative documentation (ReDoc)
- `GET /health/` - Health check endpoint
- `GET /mcp/` - Information about the MCP server
- `GET /tools/` - List all available MCP tools with descriptions

#### MCP Server (Port 8000)
- `POST /mcp/` - MCP protocol endpoint (unchanged)

### Usage Instructions

#### Running with Docker

```bash
# Build the image
docker build -t mlb-api-mcp .

# Run the container (expose both ports)
docker run -p 8000:8000 -p 8001:8001 mlb-api-mcp
```

#### Running Locally

```bash
# Install dependencies
pip install -e .

# Run the server
python main.py
```

### Accessing the Services

1. **API Documentation**: http://localhost:8001/docs
2. **Health Check**: http://localhost:8001/health/
3. **MCP Server Info**: http://localhost:8001/mcp/
4. **Available Tools**: http://localhost:8001/tools/
5. **MCP Protocol**: http://localhost:8000/mcp/ (for MCP clients)

## Key Features

- **Dual Port Setup**: Separates MCP protocol from documentation
- **Comprehensive Documentation**: Full Swagger UI with all endpoint details
- **Tools Discovery**: Endpoint to list all available MCP tools
- **Health Monitoring**: Separate health checks for both services
- **Docker Support**: Updated Dockerfile with proper port exposure

## Benefits

1. **Solves the 404 Issue**: Documentation is now properly accessible
2. **Fixes JSON-RPC Error**: MCP protocol and HTTP documentation are separated
3. **Better UX**: Clear separation of concerns between MCP and documentation
4. **Backward Compatible**: MCP functionality remains unchanged
5. **Easy Discovery**: Tools and server information easily accessible

## Testing

```bash
# Test documentation access
curl http://localhost:8001/docs

# Test health check
curl http://localhost:8001/health/

# Test MCP server info
curl http://localhost:8001/mcp/

# Test tools list
curl http://localhost:8001/tools/

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
      - "8000:8000"  # MCP server
      - "8001:8001"  # Documentation server
    environment:
      - TZ=UTC
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health/"]
      interval: 30s
      timeout: 10s
      retries: 3
```

This solution provides a complete fix for the original issue while maintaining all existing MCP functionality.