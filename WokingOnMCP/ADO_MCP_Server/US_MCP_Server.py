"""
ADO Issue Creation MCP Server (FastMCP)
Provides MCP tools to create and fetch Azure DevOps work items (Tasks / User Stories).

Run: python main.py
"""
import os
import json
from datetime import datetime
from dotenv import load_dotenv
import requests
from urllib.parse import quote

# FastMCP import (same style used in MCPServer_Demo)
from mcp.server.fastmcp import FastMCP

load_dotenv()

# Read ADO config from environment
ADO_ORG_URL = os.getenv("AZURE_DEVOPS_ORG_URL")  # e.g. https://dev.azure.com/your-organization
ADO_PAT = os.getenv("AZURE_DEVOPS_PAT")          # Personal Access Token
DEFAULT_PROJECT = os.getenv("AZURE_DEVOPS_PROJECT")  # default project name
API_VERSION = os.getenv("AZURE_DEVOPS_API_VERSION", "7.0")

if not ADO_ORG_URL or not ADO_PAT or not DEFAULT_PROJECT:
    print("⚠️  Please set AZURE_DEVOPS_ORG_URL, AZURE_DEVOPS_PAT and AZURE_DEVOPS_PROJECT in .env")

mcp = FastMCP("ADO Issue Creator", json_response=True)

def format_acceptance_criteria(criteria: str) -> str:
    """Format acceptance criteria as HTML list."""
    if not criteria:
        return ""
    lines = [line.strip() for line in criteria.split('\n') if line.strip()]
    html = "<ul>"
    for line in lines:
        html += f"<li>{line}</li>"
    html += "</ul>"
    return html

# Helper for ADO requests
def ado_auth():
    # Use basic auth with empty username and PAT as password
    from requests.auth import HTTPBasicAuth
    return HTTPBasicAuth("", ADO_PAT)


def create_work_item_ado(project: str, work_item_type: str, fields: list):
    """
    Create a work item using the ADO REST API.
    'fields' is a list of JSON Patch operations, e.g.:
    [{"op": "add", "path": "/fields/System.Title", "value": "My title"}, ...]
    """
    # URL-encode project name to handle spaces
    encoded_project = quote(project, safe='')
    url = f"{ADO_ORG_URL}/{encoded_project}/_apis/wit/workitems/${work_item_type}?api-version={API_VERSION}"
    headers = {"Content-Type": "application/json-patch+json"}
    try:
        resp = requests.patch(url, json=fields, headers=headers, auth=ado_auth(), timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        error_details = e.response.text if hasattr(e.response, 'text') else str(e)
        return {"error": str(e), "status_code": e.response.status_code, "details": error_details}
    except Exception as e:
        return {"error": str(e), "status_code": getattr(e, "response", None) and e.response.status_code}


def get_work_item_ado(work_item_id: int, expand: str = "all"):
    url = f"{ADO_ORG_URL}/_apis/wit/workitems/{work_item_id}?api-version={API_VERSION}&$expand={expand}"
    try:
        resp = requests.get(url, auth=ado_auth(), timeout=20)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e), "status_code": getattr(e, "response", None) and e.response.status_code}


# MCP tools
@mcp.tool()
def create_work_item(project: str = DEFAULT_PROJECT, work_item_type: str = "Task", title: str = "", description: str = "", assigned_to: str = "", area_path: str = "", iteration_path: str = "", acceptance_criteria: str = "", parent_id: int = None):
    """
    Create an ADO work item.
    - work_item_type: e.g., Task, User Story, Bug
    - title: short title
    - description: HTML or plain text description
    - assigned_to: email or display name
    - acceptance_criteria: acceptance criteria for user stories/features
    - parent_id: ID of parent work item (for creating child tasks/user stories)
    - don't include html tags in description; use plain text
    """
    if not title:
        return {"error": "Title is required"}

    fields = [
        {"op": "add", "path": "/fields/System.Title", "value": title},
        {"op": "add", "path": "/fields/System.Description", "value": description or ""},
    ]
    if assigned_to:
        fields.append({"op": "add", "path": "/fields/System.AssignedTo", "value": assigned_to})
    if area_path:
        fields.append({"op": "add", "path": "/fields/System.AreaPath", "value": area_path})
    if iteration_path:
        fields.append({"op": "add", "path": "/fields/System.IterationPath", "value": iteration_path})
    if acceptance_criteria:
        formatted_criteria = format_acceptance_criteria(acceptance_criteria)
        fields.append({"op": "add", "path": "/fields/Microsoft.VSTS.Common.AcceptanceCriteria", "value": formatted_criteria})
    if parent_id is not None:
        fields.append({"op": "add", "path": "/fields/System.Parent", "value": parent_id})

    result = create_work_item_ado(project, work_item_type, fields)
    # Auto-save a record locally
    try:
        OUT_DIR = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(OUT_DIR, exist_ok=True)
        record = {
            "created": datetime.utcnow().isoformat(),
            "project": project,
            "work_item_type": work_item_type,
            "title": title,
            "ado_response": result
        }
        path = os.path.join(OUT_DIR, "created_work_items.json")
        # append to file as JSON lines for simplicity
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass

    return result


@mcp.tool()
def get_work_item(work_item_id: int):
    """Get ADO work item by id."""
    try:
        wid = int(work_item_id)
    except Exception:
        return {"error": "work_item_id must be an integer"}
    return get_work_item_ado(wid)


@mcp.tool()
def create_user_story(project: str = DEFAULT_PROJECT, title: str = "", description: str = "", assigned_to: str = "", acceptance_criteria: str = ""):
    """Convenience wrapper to create a User Story (work item type may vary by process template)."""
    # In some orgs the type is "User Story" or "Product Backlog Item"
    preferred_types = ["User Story", "Product Backlog Item"]
    # Try each type until success
    for t in preferred_types:
        res = create_work_item(project=project, work_item_type=t, title=title, description=description, assigned_to=assigned_to, acceptance_criteria=acceptance_criteria)
        # Successful response includes 'id'
        if isinstance(res, dict) and res.get("id"):
            return res
    return {"error": "Failed to create User Story. Check work_item_type names for your process template.", "last_response": res}


@mcp.tool()
def create_task_for_user_story(user_story_id: int, title: str = "", description: str = "", assigned_to: str = "", project: str = DEFAULT_PROJECT):
    """
    Create a task and automatically link it as a child of the specified user story.
    - user_story_id: ID of the parent user story
    - title: Task title
    - description: Task description
    - assigned_to: Person to assign the task to (optional - leave empty to avoid assignment errors)
    - project: Project name (defaults to DEFAULT_PROJECT)
    """
    if not title:
        return {"error": "Title is required"}
    
    try:
        user_story_id = int(user_story_id)
    except Exception:
        return {"error": "user_story_id must be an integer"}
    
    # Create the task with parent_id set to the user story
    # Skip assigned_to to avoid identity validation errors in ADO
    return create_work_item(
        project=project,
        work_item_type="Task",
        title=title,
        description=description,
        assigned_to="",  # Don't assign to avoid identity errors
        parent_id=user_story_id
    )


@mcp.tool()
def list_recent_created(limit: int = 20):
    """
    Return recent created records stored locally (best-effort).
    This is not an ADO query; it's a local record.
    """
    try:
        path = os.path.join(os.path.dirname(__file__), "output", "created_work_items.json")
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().strip().splitlines()
            records = [json.loads(l) for l in lines if l.strip()]
            return records[-limit:]
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def health_check():
    """Quick ADO auth check by calling the projects API."""
    try:
        url = f"{ADO_ORG_URL}/_apis/projects?api-version={API_VERSION}"
        resp = requests.get(url, auth=ado_auth(), timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            return {"ok": True, "project_count": data.get("count"), "projects_sample": [p.get("name") for p in (data.get("value") or [])][:5]}
        else:
            return {"ok": False, "status_code": resp.status_code, "text": resp.text}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def list_team_members(project: str = DEFAULT_PROJECT):
    """
    List all team members in a project.
    Returns team members with their display names, email addresses, and unique identifiers.
    """
    try:
        # First, get the project to find its ID
        encoded_project = quote(project, safe='')
        project_url = f"{ADO_ORG_URL}/_apis/projects/{encoded_project}?api-version={API_VERSION}"
        proj_resp = requests.get(project_url, auth=ado_auth(), timeout=15)
        
        if proj_resp.status_code != 200:
            return {"error": f"Project not found: {project}", "status_code": proj_resp.status_code}
        
        project_id = proj_resp.json().get("id")
        
        # Get the default team for the project
        teams_url = f"{ADO_ORG_URL}/_apis/projects/{project_id}/teams?api-version={API_VERSION}"
        teams_resp = requests.get(teams_url, auth=ado_auth(), timeout=15)
        
        if teams_resp.status_code != 200:
            return {"error": "Failed to fetch teams", "status_code": teams_resp.status_code}
        
        teams = teams_resp.json().get("value", [])
        
        # Get members from all teams (usually there's a default team with same name as project)
        all_members = []
        seen_ids = set()
        
        for team in teams:
            team_id = team.get("id")
            team_name = team.get("name")
            
            # Get team members
            members_url = f"{ADO_ORG_URL}/_apis/projects/{project_id}/teams/{team_id}/members?api-version={API_VERSION}"
            members_resp = requests.get(members_url, auth=ado_auth(), timeout=15)
            
            if members_resp.status_code == 200:
                members = members_resp.json().get("value", [])
                for member in members:
                    identity = member.get("identity", {})
                    member_id = identity.get("id")
                    
                    # Avoid duplicates
                    if member_id and member_id not in seen_ids:
                        seen_ids.add(member_id)
                        all_members.append({
                            "id": member_id,
                            "display_name": identity.get("displayName"),
                            "unique_name": identity.get("uniqueName"),  # Usually email
                            "email": identity.get("uniqueName"),
                            "team": team_name
                        })
        
        return {
            "ok": True,
            "project": project,
            "member_count": len(all_members),
            "members": all_members
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def assign_work_item(work_item_id: int, person_name: str):
    """
    Assign a work item to a person.
    - work_item_id: The ID of the work item to assign
    - person_name: Display name or email address of the person to assign to
    
    The person_name can be:
    - Email address (e.g., "user@company.com")
    - Display name (e.g., "John Doe")
    - Partial match will be attempted
    """
    try:
        work_item_id = int(work_item_id)
    except Exception:
        return {"error": "work_item_id must be an integer"}
    
    if not person_name:
        return {"error": "person_name is required"}
    
    try:
        # Update the work item using JSON Patch
        url = f"{ADO_ORG_URL}/_apis/wit/workitems/{work_item_id}?api-version={API_VERSION}"
        headers = {"Content-Type": "application/json-patch+json"}
        
        # Create patch operation to update AssignedTo field
        patch_document = [
            {
                "op": "add",
                "path": "/fields/System.AssignedTo",
                "value": person_name
            }
        ]
        
        resp = requests.patch(url, json=patch_document, headers=headers, auth=ado_auth(), timeout=30)
        
        if resp.status_code == 200:
            data = resp.json()
            assigned_to = data.get("fields", {}).get("System.AssignedTo", {})
            
            return {
                "ok": True,
                "work_item_id": work_item_id,
                "assigned_to": {
                    "display_name": assigned_to.get("displayName") if isinstance(assigned_to, dict) else assigned_to,
                    "unique_name": assigned_to.get("uniqueName") if isinstance(assigned_to, dict) else None,
                },
                "title": data.get("fields", {}).get("System.Title"),
                "state": data.get("fields", {}).get("System.State"),
                "url": data.get("_links", {}).get("html", {}).get("href")
            }
        else:
            return {
                "ok": False,
                "error": f"Failed to assign work item",
                "status_code": resp.status_code,
                "message": resp.text[:500]
            }
            
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def add_parent_link(child_work_item_id: int, parent_work_item_id: int):
    """
    Add a parent-child relationship between two existing work items.
    This is the alternative to setting System.Parent during creation.
    
    - child_work_item_id: The ID of the child work item (e.g., Task)
    - parent_work_item_id: The ID of the parent work item (e.g., User Story)
    
    This establishes the relationship: Parent <- Child
    """
    try:
        child_work_item_id = int(child_work_item_id)
        parent_work_item_id = int(parent_work_item_id)
    except Exception:
        return {"error": "Both work_item_id values must be integers"}
    
    try:
        # Use JSON Patch to add the parent relationship
        url = f"{ADO_ORG_URL}/_apis/wit/workitems/{child_work_item_id}?api-version={API_VERSION}"
        headers = {"Content-Type": "application/json-patch+json"}
        
        # Add parent link using relations
        patch_document = [
            {
                "op": "add",
                "path": "/relations/-",
                "value": {
                    "rel": "System.LinkTypes.Hierarchy-Reverse",
                    "url": f"{ADO_ORG_URL}/_apis/wit/workItems/{parent_work_item_id}",
                    "attributes": {
                        "comment": "Adding parent link"
                    }
                }
            }
        ]
        
        resp = requests.patch(url, json=patch_document, headers=headers, auth=ado_auth(), timeout=30)
        
        if resp.status_code == 200:
            data = resp.json()
            return {
                "ok": True,
                "child_id": child_work_item_id,
                "parent_id": parent_work_item_id,
                "child_title": data.get("fields", {}).get("System.Title"),
                "message": f"Successfully linked work item {child_work_item_id} as child of {parent_work_item_id}",
                "url": data.get("_links", {}).get("html", {}).get("href")
            }
        else:
            return {
                "ok": False,
                "error": "Failed to add parent link",
                "status_code": resp.status_code,
                "details": resp.text
            }
            
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def list_user_stories(project: str = DEFAULT_PROJECT, state: str = "", limit: int = 50):
    """
    List all User Stories in a project.
    - project: Project name (defaults to DEFAULT_PROJECT)
    - state: Filter by state (e.g., 'New', 'Active', 'Resolved', 'Closed'). Leave empty for all states.
    - limit: Maximum number of user stories to return (default 50)
    
    Returns user stories with ID, title, state, assigned to, priority, and iteration.
    """
    try:
        encoded_project = quote(project, safe='')
        
        # Build WIQL query for User Stories (or Product Backlog Item)
        if state:
            wiql_query = {
                "query": f"""
                    SELECT [System.Id], [System.Title], [System.State], [System.AssignedTo], 
                           [Microsoft.VSTS.Common.Priority], [System.IterationPath]
                    FROM WorkItems 
                    WHERE [System.TeamProject] = '{project}'
                    AND [System.WorkItemType] IN ('User Story', 'Product Backlog Item')
                    AND [System.State] = '{state}'
                    ORDER BY [System.Id] DESC
                """
            }
        else:
            wiql_query = {
                "query": f"""
                    SELECT [System.Id], [System.Title], [System.State], [System.AssignedTo], 
                           [Microsoft.VSTS.Common.Priority], [System.IterationPath]
                    FROM WorkItems 
                    WHERE [System.TeamProject] = '{project}'
                    AND [System.WorkItemType] IN ('User Story', 'Product Backlog Item')
                    ORDER BY [System.Id] DESC
                """
            }
        
        # Execute WIQL query
        wiql_url = f"{ADO_ORG_URL}/{encoded_project}/_apis/wit/wiql?api-version={API_VERSION}"
        wiql_resp = requests.post(
            wiql_url,
            json=wiql_query,
            auth=ado_auth(),
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if wiql_resp.status_code != 200:
            return {
                "ok": False,
                "error": "Failed to query user stories",
                "status_code": wiql_resp.status_code,
                "message": wiql_resp.text[:500]
            }
        
        wiql_data = wiql_resp.json()
        work_items = wiql_data.get("workItems", [])
        
        if not work_items:
            return {
                "ok": True,
                "project": project,
                "count": 0,
                "user_stories": [],
                "message": f"No user stories found{' with state: ' + state if state else ''}"
            }
        
        # Limit results
        work_items = work_items[:limit]
        
        # Get full details for each work item
        ids = [str(item["id"]) for item in work_items]
        batch_url = f"{ADO_ORG_URL}/_apis/wit/workitems?ids={','.join(ids)}&api-version={API_VERSION}"
        
        batch_resp = requests.get(batch_url, auth=ado_auth(), timeout=30)
        
        if batch_resp.status_code != 200:
            return {
                "ok": False,
                "error": "Failed to fetch work item details",
                "status_code": batch_resp.status_code
            }
        
        batch_data = batch_resp.json()
        user_stories = []
        
        for item in batch_data.get("value", []):
            fields = item.get("fields", {})
            assigned_to = fields.get("System.AssignedTo", {})
            
            user_stories.append({
                "id": item.get("id"),
                "title": fields.get("System.Title"),
                "state": fields.get("System.State"),
                "assigned_to": assigned_to.get("displayName") if isinstance(assigned_to, dict) else assigned_to,
                "priority": fields.get("Microsoft.VSTS.Common.Priority"),
                "iteration": fields.get("System.IterationPath"),
                "work_item_type": fields.get("System.WorkItemType"),
                "url": item.get("_links", {}).get("html", {}).get("href")
            })
        
        return {
            "ok": True,
            "project": project,
            "count": len(user_stories),
            "filter_state": state if state else "all",
            "user_stories": user_stories
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def update_work_item(work_item_id: int, title: str = None, description: str = None, state: str = None, assigned_to: str = None, priority: int = None, area_path: str = None, iteration_path: str = None, acceptance_criteria: str = None, parent_id: int = None):
    """
    Update an existing ADO work item (User Story, Task, etc.).
    Only provided fields will be updated.
    - work_item_id: The ID of the work item to update
    - title: New title (optional)
    - description: New description (optional)
    - state: New state (e.g., 'New', 'Active', 'Resolved', 'Closed') (optional)
    - assigned_to: Email or display name to assign to (optional)
    - priority: Priority number (optional)
    - area_path: New area path (optional)
    - iteration_path: New iteration path (optional)
    - acceptance_criteria: New acceptance criteria (optional)
    - parent_id: ID of parent work item to link as child (optional)
    """
    try:
        work_item_id = int(work_item_id)
    except Exception:
        return {"error": "work_item_id must be an integer"}
    
    patch_operations = []
    
    if title is not None:
        patch_operations.append({"op": "add", "path": "/fields/System.Title", "value": title})
    if description is not None:
        patch_operations.append({"op": "add", "path": "/fields/System.Description", "value": description})
    if state is not None:
        patch_operations.append({"op": "add", "path": "/fields/System.State", "value": state})
    if assigned_to is not None:
        patch_operations.append({"op": "add", "path": "/fields/System.AssignedTo", "value": assigned_to})
    if priority is not None:
        patch_operations.append({"op": "add", "path": "/fields/Microsoft.VSTS.Common.Priority", "value": priority})
    if area_path is not None:
        patch_operations.append({"op": "add", "path": "/fields/System.AreaPath", "value": area_path})
    if iteration_path is not None:
        patch_operations.append({"op": "add", "path": "/fields/System.IterationPath", "value": iteration_path})
    if acceptance_criteria is not None:
        formatted_criteria = format_acceptance_criteria(acceptance_criteria)
        patch_operations.append({"op": "add", "path": "/fields/Microsoft.VSTS.Common.AcceptanceCriteria", "value": formatted_criteria})
    if parent_id is not None:
        patch_operations.append({"op": "add", "path": "/fields/System.Parent", "value": parent_id})
    
    if not patch_operations:
        return {"error": "At least one field must be provided to update"}
    
    try:
        url = f"{ADO_ORG_URL}/_apis/wit/workitems/{work_item_id}?api-version={API_VERSION}"
        headers = {"Content-Type": "application/json-patch+json"}
        
        resp = requests.patch(url, json=patch_operations, headers=headers, auth=ado_auth(), timeout=30)
        
        if resp.status_code == 200:
            data = resp.json()
            return {
                "ok": True,
                "work_item_id": work_item_id,
                "updated_fields": [op["path"] for op in patch_operations],
                "work_item": {
                    "id": data.get("id"),
                    "title": data.get("fields", {}).get("System.Title"),
                    "state": data.get("fields", {}).get("System.State"),
                    "url": data.get("_links", {}).get("html", {}).get("href")
                }
            }
        else:
            return {
                "ok": False,
                "error": f"Failed to update work item",
                "status_code": resp.status_code,
                "message": resp.text[:500]
            }
            
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def get_child_work_items(parent_id: int, project: str = DEFAULT_PROJECT):
    """
    Get all child work items (tasks, subtasks) for a given parent work item ID.
    - parent_id: ID of the parent work item (e.g., User Story)
    - project: Project name (defaults to DEFAULT_PROJECT)
    """
    try:
        parent_id = int(parent_id)
    except Exception:
        return {"error": "parent_id must be an integer"}
    
    # Use WIQL to query child work items
    wiql_query = f"""
    SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType]
    FROM WorkItems
    WHERE [System.Parent] = {parent_id}
    ORDER BY [System.Id]
    """
    
    try:
        encoded_project = quote(project, safe='')
        wiql_url = f"{ADO_ORG_URL}/{encoded_project}/_apis/wit/wiql?api-version={API_VERSION}"
        headers = {"Content-Type": "application/json"}
        
        wiql_payload = {"query": wiql_query}
        wiql_resp = requests.post(wiql_url, json=wiql_payload, headers=headers, auth=ado_auth(), timeout=30)
        
        if wiql_resp.status_code != 200:
            return {
                "ok": False,
                "error": "Failed to query child work items",
                "status_code": wiql_resp.status_code,
                "message": wiql_resp.text[:500]
            }
        
        wiql_data = wiql_resp.json()
        work_items = wiql_data.get("workItems", [])
        
        if not work_items:
            return {
                "ok": True,
                "parent_id": parent_id,
                "count": 0,
                "child_work_items": [],
                "message": "No child work items found"
            }
        
        # Get full details for each work item
        ids = [str(item["id"]) for item in work_items]
        batch_url = f"{ADO_ORG_URL}/_apis/wit/workitems?ids={','.join(ids)}&api-version={API_VERSION}"
        
        batch_resp = requests.get(batch_url, auth=ado_auth(), timeout=30)
        
        if batch_resp.status_code != 200:
            return {
                "ok": False,
                "error": "Failed to fetch work item details",
                "status_code": batch_resp.status_code
            }
        
        batch_data = batch_resp.json()
        child_items = []
        
        for item in batch_data.get("value", []):
            fields = item.get("fields", {})
            assigned_to = fields.get("System.AssignedTo", {})
            
            child_items.append({
                "id": item.get("id"),
                "title": fields.get("System.Title"),
                "state": fields.get("System.State"),
                "work_item_type": fields.get("System.WorkItemType"),
                "assigned_to": assigned_to.get("displayName") if isinstance(assigned_to, dict) else assigned_to,
                "url": item.get("_links", {}).get("html", {}).get("href")
            })
        
        return {
            "ok": True,
            "parent_id": parent_id,
            "count": len(child_items),
            "child_work_items": child_items
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}


# Run the server
if __name__ == "__main__":
    print("🚀 Starting ADO Issue Creator MCP Server...")
    if not ADO_ORG_URL or not ADO_PAT or not DEFAULT_PROJECT:
        print("⚠️ Missing ADO configuration in environment; server will still start but ADO calls will fail.")
    try:
        # mcp.run(transport="sse")
        mcp.run(transport="streamable-http")
    except KeyboardInterrupt:
        print("\n🛑 Server stopping...")
        print("👋 Goodbye.")