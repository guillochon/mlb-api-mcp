import json
from fastmcp import FastMCP
from mlb_api import setup_mlb_tools
from generic_api import setup_generic_tools
from fastmcp.server.server import Request, Response

# Create FastMCP server instance
mcp = FastMCP("MLB API MCP Server")


@mcp.custom_route("/health/", methods=["GET"])
async def health_check(request: Request) -> Response:
    return Response(json.dumps({"status": "ok"}))


# Setup all MLB and generic tools
setup_mlb_tools(mcp)
setup_generic_tools(mcp)

if __name__ == "__main__":
    # Run with streamable HTTP transport for web deployment
    mcp.run(
        transport="http", host="0.0.0.0", port=8000, path="/mcp/", stateless_http=True
    )
