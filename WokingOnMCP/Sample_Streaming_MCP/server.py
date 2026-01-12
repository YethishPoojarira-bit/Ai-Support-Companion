from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Demo MCP Server")

@mcp.tool(description="Echoes the input message back to the client.")
async def echo(message: str) -> str:
    return message.upper()

if __name__ == "__main__":
    mcp.run(transport="streamable-http")