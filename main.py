import argparse
import os
import warnings

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse

from generic_api import setup_generic_tools
from mlb_api import setup_mlb_tools

# Suppress websockets deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="websockets")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="uvicorn.protocols.websockets")

# Create FastMCP server instance
mcp = FastMCP("MLB API MCP Server")

# Setup all MLB and generic tools
setup_mlb_tools(mcp)
setup_generic_tools(mcp)


# Add custom routes to the MCP server for documentation and info
@mcp.custom_route("/", methods=["GET"])
async def root(request):
    """Root endpoint redirects to documentation"""
    return RedirectResponse(url="/docs")


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint"""
    return JSONResponse({"status": "ok"})


@mcp.custom_route("/info", methods=["GET"])
async def mcp_info(request):
    """Information about the MCP server"""
    tools_list = await mcp.get_tools()
    return JSONResponse(
        {
            "status": "running",
            "protocol": "mcp",
            "server_name": "MLB API MCP Server",
            "description": "Model Context Protocol server for MLB statistics and baseball data",
            "mcp_endpoint": "/mcp/",
            "tools_available": len(tools_list),
            "note": "This is an MCP server. Use MCP-compatible clients to interact with the tools.",
        }
    )


@mcp.custom_route("/tools", methods=["GET"])
async def list_tools(request):
    """List available MCP tools"""
    tools = []
    tools_list = await mcp.get_tools()
    for tool_name, tool in tools_list.items():
        tools.append(
            {
                "name": tool_name,
                "description": getattr(tool, "description", None)
                or "No description available",
                "parameters": getattr(tool, "parameters", None) or {},
            }
        )
    return JSONResponse({"tools": tools})


# Add a basic docs endpoint that provides information about available endpoints
@mcp.custom_route("/docs", methods=["GET"])
async def docs(request):
    """Basic documentation endpoint"""
    tools_list = await mcp.get_tools()
    docs_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>MLB API MCP Server Documentation</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .endpoint {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
            .method {{ font-weight: bold; color: #0066cc; }}
            .path {{ font-weight: bold; color: #cc6600; }}
            .tools {{ margin: 10px 0; }}
            .tool {{ margin: 5px 0; padding: 10px; background: #f5f5f5; border-radius: 3px; }}
        </style>
    </head>
    <body>
        <h1>MLB API MCP Server Documentation</h1>
        <p>A Model Context Protocol server that provides comprehensive access to MLB statistics and baseball data.</p>
        
        <h2>Available Endpoints</h2>
        
        <div class="endpoint">
            <span class="method">GET</span> <span class="path">/health</span>
            <p>Health check endpoint</p>
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span> <span class="path">/info</span>
            <p>Information about the MCP server</p>
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span> <span class="path">/tools</span>
            <p>List all available MCP tools</p>
        </div>
        
        <div class="endpoint">
            <span class="method">POST</span> <span class="path">/mcp/</span>
            <p>MCP protocol endpoint for MCP-compatible clients</p>
        </div>
        
        <h2>Available MCP Tools ({len(tools_list)} total)</h2>
        <div class="tools">
    """
    for tool_name, tool in tools_list.items():
        description = getattr(tool, "description", None) or "No description available"
        docs_html += (
            f'<div class="tool"><strong>{tool_name}</strong>: {description}</div>'
        )
    docs_html += """
        </div>
        
        <h2>Usage</h2>
        <p>This server implements the Model Context Protocol (MCP). Use MCP-compatible clients to interact with the tools.</p>
        <p>For direct HTTP access, you can use the endpoints listed above.</p>
    </body>
    </html>
    """
    return HTMLResponse(content=docs_html)





if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="MLB API MCP Server")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run server with HTTP transport (default: stdio transport)"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8000,
        help="Port to run the server on (default: 8000, env PORT takes priority)"
    )
    args = parser.parse_args()

    if args.http:
        # Environment variable takes priority over command line argument
        port = int(os.environ.get("PORT", args.port))

        print(f"Starting MLB API MCP Server on port {port}...")
        print(f"- Documentation: http://localhost:{port}/docs")
        print(f"- Health check: http://localhost:{port}/health")
        print(f"- MCP server info: http://localhost:{port}/info")
        print(f"- Tools list: http://localhost:{port}/tools")
        print(f"- MCP protocol: http://localhost:{port}/mcp/")

        # Run the MCP server with HTTP transport using uvicorn
        uvicorn.run(
            mcp.streamable_http_app(),
            host="0.0.0.0",
            port=port,
            log_level="info"
        )
    else:
        # Run with stdio transport (for Smithery)
        mcp.run(transport="stdio")
