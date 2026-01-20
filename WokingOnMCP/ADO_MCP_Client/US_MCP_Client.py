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

    success_stories = failed_stories = 0
    success_tasks = failed_tasks = 0

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
                
                if result.isError:
                    raise Exception(result.content)

                raw_text = result.content[0].text
                tool_response = json.loads(raw_text)

                ado_id = tool_response.get("id")

                if not ado_id:
                    raise Exception(f"Unexpected response: {tool_response}")

                print(f"✅ Successfully created: {story['id']} (ADO ID: {ado_id})")
                success_stories += 1

                # Create tasks for this user story
                tasks = story.get("tasks", [])
                created_task_ids = []
                if tasks:
                    print(f"   📋 Creating {len(tasks)} tasks...")
                    for task_idx, task in enumerate(tasks, 1):
                        try:
                            # Format task title with ID and name
                            task_title = f"{task.get('id', f'Task-{task_idx}')}: {task.get('title', 'Untitled Task')}"
                            task_description = task.get("description", "")
                            if task.get("notes"):
                                task_description += f"\n\nNotes: {task['notes']}"
                            
                            # Create task without parent link first
                            task_result = await session.call_tool(
                                "create_work_item",
                                arguments={
                                    "project": "Online Learning Portal",
                                    "work_item_type": "Task",
                                    "title": task_title,
                                    "description": task_description,
                                    "assigned_to": ""
                                }
                            )
                            
                            if task_result.isError:
                                raise Exception(task_result.content)
                            
                            task_raw_text = task_result.content[0].text
                            task_response = json.loads(task_raw_text)
                            task_ado_id = task_response.get("id")
                            
                            if task_ado_id:
                                print(f"   ✅ Task {task_idx}/{len(tasks)}: {task.get('id', 'N/A')} (ADO ID: {task_ado_id})")
                                created_task_ids.append({"id": task_ado_id, "name": task_title})
                                success_tasks += 1
                            else:
                                # Print detailed error response
                                print(f"   ❌ Task {task_idx}/{len(tasks)} failed - ADO Response:")
                                if "error" in task_response:
                                    print(f"      Error: {task_response.get('error')}")
                                    print(f"      Status Code: {task_response.get('status_code')}")
                                    print(f"      Details: {task_response.get('details', 'No details')}")
                                else:
                                    print(f"      No task ID returned: {task_response}")
                                failed_tasks += 1
                                
                        except Exception as task_error:
                            print(f"   ❌ Task {task_idx}/{len(tasks)} failed: {task_error}")
                            failed_tasks += 1
                    
                    # Update user story description with task links
                    if created_task_ids:
                        # First, link all tasks to the user story
                        print(f"   🔗 Linking {len(created_task_ids)} tasks to user story...")
                        linked_count = 0
                        for task_info in created_task_ids:
                            try:
                                link_result = await session.call_tool(
                                    "add_parent_link",
                                    arguments={
                                        "child_work_item_id": task_info['id'],
                                        "parent_work_item_id": ado_id
                                    }
                                )
                                
                                if not link_result.isError:
                                    linked_count += 1
                                else:
                                    print(f"   ⚠️  Could not link task {task_info['id']}: {link_result.content}")
                            except Exception as link_error:
                                print(f"   ⚠️  Error linking task {task_info['id']}: {link_error}")
                        
                        print(f"   ✅ Linked {linked_count}/{len(created_task_ids)} tasks to user story")
                        
                        # Then update description with task references
                        try:
                            print(f"   📝 Adding task references to user story description...")
                            task_links_html = "<br/><br/><strong>Related Tasks:</strong><ul>"
                            for task_info in created_task_ids:
                                task_links_html += f"<li>#{task_info['id']}: {task_info['name']}</li>"
                            task_links_html += "</ul>"
                            
                            # Append to existing description
                            updated_description = description + task_links_html
                            
                            update_result = await session.call_tool(
                                "update_work_item",
                                arguments={
                                    "work_item_id": ado_id,
                                    "description": updated_description
                                }
                            )
                            
                            if not update_result.isError:
                                print(f"   ✅ Task references added to user story description")
                        except Exception as update_error:
                            print(f"   ⚠️  Could not update user story description: {update_error}")

            except Exception as e:
                print(f"❌ Failed {story['id']}: {e}")
                failed_stories += 1

    print("\n📊 Summary")
    print(f"✅ User Stories - Success: {success_stories}, Failed: {failed_stories}")
    print(f"✅ Tasks - Success: {success_tasks}, Failed: {failed_tasks}")


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
