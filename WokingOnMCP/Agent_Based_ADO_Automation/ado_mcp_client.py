"""
ADO MCP Client - Push user stories to Azure DevOps
Connects to the HTTP MCP server to create user stories from JSON files.

Usage:
    python ado_mcp_client.py --push --file user_stories_20260108_105117.json
"""

import asyncio
import json
import argparse
from pathlib import Path
import httpx
from contextlib import asynccontextmanager
from mcp import ClientSession
from mcp.client.sse import sse_client

# MCP Server Configuration
MCP_SERVER_URL = "http://127.0.0.1:8000/sse"


@asynccontextmanager
async def create_mcp_client():
    """Create and connect to the MCP server via HTTP."""
    async with httpx.AsyncClient() as http_client:
        async with sse_client(MCP_SERVER_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session


async def push_stories_from_file(filename: str):
    """
    Read user stories from JSON file and push them to Azure DevOps.
    
    Args:
        filename: Name of the JSON file in the output directory
    """
    file_path = Path("output") / filename
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    print(f"📖 Reading user stories from: {file_path}")
    
    # Read and parse JSON
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    user_stories = data.get('user_stories', [])
    if not user_stories:
        print("⚠️ No user stories found in the file")
        return
    
    print(f"🚀 Pushing {len(user_stories)} user stories to Azure DevOps")
    print("=" * 60)
    
    async with create_mcp_client() as session:
        success_count = 0
        failed_count = 0
        
        for i, story in enumerate(user_stories, 1):
            try:
                print(f"\n📝 Processing story {i}/{len(user_stories)}: {story['id']} - {story['title']}")
                
                # Format description with acceptance criteria and notes
                description = f"""
<p><strong>Description:</strong></p>
<p>{story['description']}</p>

<p><strong>Acceptance Criteria:</strong></p>
<ul>
"""
                
                for criteria in story.get('acceptance_criteria', []):
                    description += f"<li>{criteria}</li>\n"
                
                description += "</ul>\n"
                
                if story.get('notes'):
                    description += f"<p><strong>Notes:</strong></p>\n<p>{story['notes']}</p>\n"
                
                if story.get('clarifications_needed'):
                    description += f"<p><strong>Clarifications Needed:</strong></p>\n<ul>\n"
                    for clarification in story['clarifications_needed']:
                        description += f"<li>{clarification}</li>\n"
                    description += "</ul>\n"
                
                # Call the create_user_story tool
                result = await session.call_tool(
                    "create_user_story",
                    arguments={
                        "project": "Online Learning Portal",
                        "title": f"{story['id']}: {story['title']}",
                        "description": description,
                        "assigned_to": ""
                    }
                )
                
                print(f"✅ Successfully created: {story['id']}")
                success_count += 1
                
            except Exception as e:
                print(f"❌ Failed to create {story['id']}: {e}")
                failed_count += 1
                continue
        
        print("\n" + "=" * 60)
        print(f"📊 Push Summary:")
        print(f"✅ Successful: {success_count}")
        print(f"❌ Failed: {failed_count}")
        print(f"📈 Success Rate: {success_count}/{len(user_stories)} ({success_count/len(user_stories)*100:.1f}%)")


async def main():
    """Main function - only supports pushing from specified file."""
    parser = argparse.ArgumentParser(description="ADO MCP Client")
    parser.add_argument('--push', action='store_true', help='Push user stories from JSON file to ADO')
    parser.add_argument('--file', type=str, required=True, help='Name of JSON file in output/ directory (e.g., user_stories_20260108_105117.json)')
    
    args = parser.parse_args()
    
    if not args.push:
        parser.error("--push flag is required")
    
    print("🚀 ADO MCP Client")
    print("=" * 50)
    
    try:
        await push_stories_from_file(args.file)
        print("\n✅ Push operation completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
