from fastapi import FastAPI
from fastapi_mcp import FastApiMCP
from mlb_api import router as mlb_router
from generic_api import router as generic_router

app = FastAPI(
    title="MCP API Gateway",
    description="API Gateway for various services including MLB statistics and more",
    version="0.1.0"
)

# Initialize MCP server
mcp = FastApiMCP(app,
    describe_all_responses=True,
    describe_full_response_schema=True
)

# Mount the MCP server
mcp.mount()

# Include MLB API routes
app.include_router(mlb_router)
app.include_router(generic_router)

mcp.setup_server()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)