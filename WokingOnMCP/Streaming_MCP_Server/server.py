import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import langsmith
from langsmith import traceable

load_dotenv()
mcp = FastMCP("Demo MCP Server")

# Configure LangSmith tracing
langsmith_client = langsmith.Client()


@mcp.prompt()
@traceable("search_prompt", client=langsmith_client)
def search(query: str) -> str:
    return (
        f"Perform comprehensive research on '{query}', including background, "
        f"key concepts, recent developments, real-world use cases, "
        f"benefits, limitations, and credible references."
    )

@mcp.tool(description="Echoes the input message back to the client.")
@traceable("echo_tool", client=langsmith_client)
async def echo(message: str) -> str:
    return message.upper()

if __name__ == "__main__":
    # print(os.getenv("LANGSMITH_API_KEY"))
    mcp.run(transport="streamable-http")