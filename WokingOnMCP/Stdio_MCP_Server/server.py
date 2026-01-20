from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Voice MCP Server")

@mcp.tool()
def shout (message: str) -> str:
    return message.upper()

@mcp.tool()
def whisper(message: str) -> str:
    return message.lower()

if __name__ == "__main__":
    mcp.run(transport="stdio")