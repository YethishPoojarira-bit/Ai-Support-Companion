import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def main():
    async with streamable_http_client("http://127.0.0.1:8000") as (read, write, session_init):
        async with ClientSession(read, write) as session:
            await session.initialize()
            response = await session.call_tool("echo", message="hello world")
            print(f"Response from server: {response}")

if __name__ == "__main__":
    asyncio.run(main())