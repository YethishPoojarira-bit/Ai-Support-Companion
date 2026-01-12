import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def main():
    async with streamable_http_client(
        "http://127.0.0.1:8000/mcp"   # ✅ correct endpoint
    ) as (read, write, _):

        async with ClientSession(read, write) as session:
            # REQUIRED for stateful streamable MCP
            await session.initialize()

            result = await session.call_tool("echo", {"message": "hello world"})

            print("Response from server:", result)

if __name__ == "__main__":
    asyncio.run(main())