import asyncio
import json
import argparse
from pathlib import Path
from contextlib import asynccontextmanager

from mcp.client.streamable_http import streamable_http_client
from mcp import ClientSession

# MCP Server Configuration
MCP_SERVER_URL = "http://127.0.0.1:8000/mcp"


@asynccontextmanager
async def create_mcp_client():
    async with streamable_http_client(MCP_SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def push_stories_from_file(filename: str):
    file_path = Path("output") / filename
    if not file_path.exists():
        raise FileNotFoundError(file_path)

    print(f"📖 Reading user stories from: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    user_stories = data.get("user_stories", [])
    if not user_stories:
        print("⚠️ No user stories found")
        return

    print(f"🚀 Pushing {len(user_stories)} user stories")
    print("=" * 60)

    success = failed = 0

    async with create_mcp_client() as session:
        for i, story in enumerate(user_stories, 1):
            try:
                print(f"\n📝 {i}/{len(user_stories)} {story['id']}")

                description = f"<p>{story['description']}</p><ul>"
                for c in story.get("acceptance_criteria", []):
                    description += f"<li>{c}</li>"
                description += "</ul>"

                result = await session.call_tool(
                    "create_user_story",
                    arguments={
                        "project": "Online Learning Portal",
                        "title": f"{story['id']}: {story['title']}",
                        "description": description,
                        "assigned_to": ""
                    }
                )
                
                # print(json.loads(result.content[0].text).get("id"))
                if result.isError:
                    raise Exception(result.content)

                raw_text = result.content[0].text
                tool_response = json.loads(raw_text)

                # 3️⃣ Detect ADO success robustly
                ado_id = tool_response.get("id")

                if not ado_id:
                    raise Exception(f"Unexpected response: {tool_response}")

                print(f"✅ Successfully created: {story['id']} (ADO ID: {ado_id})")
                success += 1

            except Exception as e:
                print(f"❌ Failed {story['id']}: {e}")
                failed += 1

    print("\n📊 Summary")
    print(f"✅ Success: {success}")
    print(f"❌ Failed: {failed}")


async def main():
    parser = argparse.ArgumentParser(description="ADO MCP Client")
    parser.add_argument("--push", action="store_true", required=True)
    parser.add_argument("--file", required=True)
    args = parser.parse_args()

    print("🚀 ADO MCP Client")
    print("=" * 50)

    await push_stories_from_file(args.file)


if __name__ == "__main__":
    asyncio.run(main())
