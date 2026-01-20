# MCP Client Documentation: Azure DevOps Work Item Management

## Overview
This document provides a detailed explanation of the MCP (Model Context Protocol) Client implementation in `US_MCP_Client.py`. The client connects to an MCP Server (`US_MCP_Server.py`) to manage Azure DevOps (ADO) work items, specifically focusing on creating user stories and their associated tasks with proper parent-child relationships.

## Architecture
The MCP Client follows the Model Context Protocol architecture:
- **MCP Host**: The Python script logic that decides when and how to call tools
- **MCP Client**: The code that establishes connections and sends tool calls to the server
- **MCP Server**: The backend that executes tools and interacts with Azure DevOps APIs

In this implementation, the host and client are combined in a single script for simplicity.

## Key Components

### 1. Connection Setup
```python
@asynccontextmanager
async def create_mcp_client():
    async with streamable_http_client(MCP_SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session
```
- Uses `streamable_http_client` for persistent HTTP connections
- Establishes MCP session with the server at `http://127.0.0.1:8000/mcp`
- Handles session lifecycle (initialize, communicate, cleanup)

### 2. Main Workflow
The client reads user stories from a JSON file and pushes them to Azure DevOps through a series of tool calls:

1. **Read Input Data**: Parses JSON file containing user stories with tasks
2. **Create User Stories**: Calls server tools to create ADO User Story work items
3. **Create Tasks**: Creates Task work items for each user story
4. **Establish Relationships**: Links tasks to user stories using parent-child relationships
5. **Update Descriptions**: Adds task references to user story descriptions

## Available Tools and Resources

The client interacts with the following MCP Server tools (defined in `US_MCP_Server.py`):

### Core Tools Used by Client

#### 1. `create_user_story`
**Purpose**: Creates a new User Story work item in Azure DevOps
**Parameters**:
- `project` (str): ADO project name (default: from environment)
- `title` (str): Story title
- `description` (str): HTML-formatted description
- `assigned_to` (str): Assignee email/name
- `acceptance_criteria` (str): Acceptance criteria as text

**Usage in Client**:
```python
result = await session.call_tool(
    "create_user_story",
    arguments={
        "project": "Online Learning Portal",
        "title": f"{story['id']}: {story['title']}",
        "description": description,
        "assigned_to": ""
    }
)
```

#### 2. `create_work_item`
**Purpose**: Creates any type of ADO work item (Task, Bug, etc.)
**Parameters**:
- `project` (str): ADO project name
- `work_item_type` (str): Type of work item (Task, User Story, Bug)
- `title` (str): Work item title
- `description` (str): Description
- `assigned_to` (str): Assignee
- `area_path` (str): Area path
- `iteration_path` (str): Iteration path
- `acceptance_criteria` (str): For user stories
- `parent_id` (int): Parent work item ID for linking

**Usage in Client**:
```python
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
```

#### 3. `add_parent_link`
**Purpose**: Establishes parent-child relationship between work items
**Parameters**:
- `child_work_item_id` (int): ID of the child work item
- `parent_work_item_id` (int): ID of the parent work item

**Usage in Client**:
```python
link_result = await session.call_tool(
    "add_parent_link",
    arguments={
        "child_work_item_id": task_info['id'],
        "parent_work_item_id": ado_id
    }
)
```

#### 4. `update_work_item`
**Purpose**: Updates existing work item fields
**Parameters**:
- `work_item_id` (int): Work item to update
- `title` (str): New title
- `description` (str): New description
- `state` (str): New state
- `assigned_to` (str): New assignee
- `priority` (int): Priority level
- `area_path` (str): Area path
- `iteration_path` (str): Iteration path
- `acceptance_criteria` (str): Acceptance criteria
- `parent_id` (int): Parent work item ID

**Usage in Client**:
```python
update_result = await session.call_tool(
    "update_work_item",
    arguments={
        "work_item_id": ado_id,
        "description": updated_description
    }
)
```

### Other Available Tools (Not Used by Current Client)
The server provides additional tools that could be integrated:

- `get_work_item`: Retrieve work item details
- `list_recent_created`: List recently created work items
- `health_check`: Server health status
- `list_team_members`: Get project team members
- `assign_work_item`: Assign work item to person
- `list_user_stories`: Query existing user stories
- `get_child_work_items`: Get child items of a parent

## Detailed Workflow

### 1. Input Processing
- Reads JSON file from `output/` directory
- Expects structure: `{"user_stories": [{"id": "...", "title": "...", "description": "...", "acceptance_criteria": [...], "tasks": [...]}]}`
- Validates file existence and content

### 2. User Story Creation
For each user story:
- Formats description as HTML with acceptance criteria as bulleted list
- Calls `create_user_story` tool
- Parses response to extract ADO work item ID
- Tracks success/failure counts

### 3. Task Creation
For each task in a user story:
- Formats task title with ID and name
- Calls `create_work_item` with `work_item_type: "Task"`
- Collects created task IDs for linking
- Handles creation failures gracefully

### 4. Relationship Establishment
- Uses `add_parent_link` to connect each task to its user story
- Employs ADO's Relations API for reliable parent-child linking
- Updates success counters

### 5. Description Enhancement
- Appends task references to user story description
- Uses HTML formatting for readability
- Calls `update_work_item` to persist changes


## Command Line Interface

```bash
python US_MCP_Client.py --push --file <filename.json>
```

- `--push`: Required flag to initiate push operation
- `--file`: JSON file containing user stories (relative to `output/` directory)

## Output and Logging

### Console Output
- Progress indicators with emojis
- Success/failure counts per operation type
- Detailed error messages for debugging
- Final summary statistics

### Local Logging
- Server automatically logs creations to JSONL files
- Client tracks operations in memory
- No direct file output from client

## LLM → JSON → Upload Flow (end-to-end)

This section describes the complete flow from extracting user stories with the LLM agent, saving them to a JSON file, and uploading them to Azure DevOps via the MCP client and server.

1) Extraction (LLM → JSON)
- Where: `user_story_extraction_agent.py` (class `UserStoryTools`).
- Models: `Task`, `UserStory`, `ExtractionResponse` are defined as Pydantic models at the top of the file.
- Save step: The `save_stories` tool (`@ai_function(name="save_user_stories")`) writes a timestamped JSON file to `OUTPUT_DIR` (default `./output`). It writes an object with `metadata` plus the extracted data (`user_stories`, `summary`, `questions`, etc.). Example path: `output/user_stories_20260121_120000.json`.

2) Client upload (JSON → MCP Server)
- CLI: run `python US_MCP_Client.py --push --file <filename.json>` from the `ADO_MCP_Client` folder. The `--file` name is resolved against the `output/` directory.
- File read: `push_stories_from_file()` loads the JSON file and expects a top-level `user_stories` array.
- Sequence per story (see `US_MCP_Client.py`):
    1. Call `create_user_story` with formatted title and description.
    2. For each task, call `create_work_item` (type `Task`) to create the task work item.
    3. Link each created task to the user story by calling `add_parent_link` (child_id, parent_id).
    4. Append task references to the story description and call `update_work_item` to persist the description.

3) Server actions (MCP Server → ADO)
- Authentication: `US_MCP_Server.py` reads `AZURE_DEVOPS_PAT` and uses `ado_auth()` to authorize all REST calls to ADO.
- Create mechanics: `create_work_item` builds JSON Patch operations and calls `create_work_item_ado()` which performs `PATCH /_apis/wit/workitems/$type` with `application/json-patch+json`.
- Parent linking: The server uses the Relations API by PATCHing `/relations/-` to the child work item with `rel: System.LinkTypes.Hierarchy-Reverse` pointing at the parent work item URL. `add_parent_link` does this explicitly when called from the client.
- Local audit: After creating a work item the server appends a JSON record to `ADO_MCP_Server/output/created_work_items.json` (newline-delimited JSON).

4) Data formats and expectations
- Extraction JSON: must include `user_stories` array where each story has `id`, `title`, `description`, `acceptance_criteria` (list), and optional `tasks` (list of task objects with `id`, `title`, `description`, `notes`). See example below.
- MCP tool responses: server returns JSON (tool response text contains JSON); `US_MCP_Client.py` loads `result.content[0].text` via `json.loads()` and expects an `id` field for created items.

5) Example JSON
```json
{
    "metadata": {"extracted_at": "2026-01-21T12:00:00", "approved": true, "total_stories": 1},
    "user_stories": [
        {
            "id": "US-001",
            "title": "User can log in",
            "description": "As a user, I want to log in so that I can access my dashboard.",
            "acceptance_criteria": ["Login accepts username/password", "Shows error on wrong credentials"],
            "priority": "High",
            "tasks": [
                {"id": "T-1", "title": "Create login UI", "description": "Create a responsive login page", "notes": ""}
            ]
        }
    ]
}
```

6) Example commands
Start server (in `ADO_MCP_Server`):
```bash
python US_MCP_Server.py
```

Run client push (in `ADO_MCP_Client`):
```bash
python US_MCP_Client.py --push --file user_stories_20260121_120000.json
```