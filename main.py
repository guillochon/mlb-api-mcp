import json
import asyncio
import threading
import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastmcp import FastMCP
from mlb_api import setup_mlb_tools
from generic_api import setup_generic_tools
from fastmcp.server.server import Request, Response

# Create FastMCP server instance
mcp = FastMCP("MLB API MCP Server")

# Setup all MLB and generic tools
setup_mlb_tools(mcp)
setup_generic_tools(mcp)

# Create a separate FastAPI app for documentation and health checks
docs_app = FastAPI(
    title="MLB API MCP Server",
    description="A Model Context Protocol server that provides comprehensive access to MLB statistics and baseball data",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

@docs_app.get("/")
async def root():
    """Root endpoint redirects to documentation"""
    return RedirectResponse(url="/docs")

@docs_app.get("/health/")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

@docs_app.get("/mcp/")
async def mcp_info():
    """Information about the MCP server"""
    return {
        "status": "running",
        "protocol": "mcp",
        "server_name": "MLB API MCP Server",
        "description": "Model Context Protocol server for MLB statistics and baseball data",
        "mcp_endpoint": "/mcp/",
        "tools_available": len(mcp.tools),
        "note": "This is an MCP server. Use MCP-compatible clients to interact with the tools."
    }

@docs_app.get("/tools/")
async def list_tools():
    """List available MCP tools"""
    tools = []
    for tool_name, tool in mcp.tools.items():
        tools.append({
            "name": tool_name,
            "description": tool.description or "No description available",
            "parameters": tool.parameters or {}
        })
    return {"tools": tools}

def run_docs_server():
    """Run the FastAPI docs server"""
    uvicorn.run(docs_app, host="0.0.0.0", port=8001, log_level="info")

if __name__ == "__main__":
    # Start the docs server in a separate thread
    docs_thread = threading.Thread(target=run_docs_server, daemon=True)
    docs_thread.start()
    
    print("Starting MLB API MCP Server...")
    print("- MCP server running on http://0.0.0.0:8000/mcp/")
    print("- Documentation available at http://0.0.0.0:8001/docs")
    print("- Health check at http://0.0.0.0:8001/health/")
    print("- Tools list at http://0.0.0.0:8001/tools/")
    
    # Run the MCP server
    mcp.run(
        transport="http", host="0.0.0.0", port=8000, path="/mcp/", stateless_http=True
    )
