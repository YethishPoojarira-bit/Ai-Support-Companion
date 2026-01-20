from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

stdio_server_params = StdioServerParameters(
    command="python",
    args=["C:\\Ai Support Companion\\WokingOnMCP\\Stdio_MCP_Server\\server.py"]
)

async def main():
    async with stdio_client(stdio_server_params) as (read, write):
        async with ClientSession(read_stream= read, write_stream= write) as session:
            # REQUIRED for stateful MCP sessions
            await session.initialize()

            # tools = await session.list_tools()
            # print("Available tools:", tools)

            result = await session.call_tool("shout", {"message": "hello world"})
            print("Shout Response from server:", result)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())