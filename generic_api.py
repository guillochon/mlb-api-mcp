from datetime import datetime


def setup_generic_tools(mcp):
    """Setup generic tools for the MCP server"""
    
    @mcp.tool
    def get_current_date() -> str:
        """Get the current date.
        
        Returns:
            str: The current date in YYYY-MM-DD format
        """
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            return current_date
        except Exception as e:
            return f"Error getting current date: {str(e)}"
    
    @mcp.tool
    def get_current_time() -> str:
        """Get the current time.
        
        Returns:
            str: The current time in HH:MM:SS format
        """
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            return current_time
        except Exception as e:
            return f"Error getting current time: {str(e)}"