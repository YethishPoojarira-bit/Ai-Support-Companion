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

-`add_parent_link` PATCHes the *child* work item to add a relation referencing the *parent* (rel: `System.LinkTypes.Hierarchy-Reverse`), so the child is linked to the parent and the parent will list that child in Azure DevOps.

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


The system is designed to run the LLM extractor, MCP server, and MCP client as separate processes. This keeps responsibilities distinct and lets you run, test, and troubleshoot each piece independently.

1) Extraction (LLM → JSON)
- Where: `user_story_extraction_agent.py` (class `UserStoryTools`).
- Purpose: Extracts user stories and tasks from transcripts and saves validated JSON to `OUTPUT_DIR`.
- Run (interactive):
```powershell
Set-Location 'c:\Ai Support Companion\WokingOnMCP\ADO_MCP_Client'
python user_story_extraction_agent.py
```
- Environment variables used by the agent:
    - `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT` (or `AZURE_OPENAI_DEPLOYMENT_NAME`), `AZURE_OPENAI_API_KEY`, optional `OUTPUT_DIR`.
- Output: Timestamped JSON in `output/` (e.g. `user_stories_20260121_120000.json`). This file is the input to the MCP client.

2) MCP Server (MCP Server → Azure DevOps)
- Where: `ADO_MCP_Server/US_MCP_Server.py`.
- Purpose: Exposes tools over MCP to create/update/link work items in Azure DevOps.
- Run (server process):
```powershell
Set-Location 'c:\Ai Support Companion\WokingOnMCP\ADO_MCP_Server'
# Ensure env: AZURE_DEVOPS_PAT, AZURE_DEVOPS_ORG_URL, AZURE_DEVOPS_PROJECT
python US_MCP_Server.py
```
- Environment variables used by the server:
    - `AZURE_DEVOPS_PAT`, `AZURE_DEVOPS_ORG_URL`, `AZURE_DEVOPS_PROJECT`, optional `OUTPUT_DIR` (for JSONL audit).
- Notes:
    - Server logs created work items to `ADO_MCP_Server/output/created_work_items.json` (JSONL).
    - Parent-child linking uses ADO Relations API; if identity fields (AssignedTo) are invalid, server omits assignment to avoid 400 errors.

3) MCP Client (JSON → MCP Server)
- Where: `ADO_MCP_Client/US_MCP_Client.py`.
- Purpose: Reads extraction JSON and pushes user stories and tasks to the MCP server via tool calls.
- Run (client process):
```powershell
Set-Location 'c:\Ai Support Companion\WokingOnMCP\ADO_MCP_Client'
python US_MCP_Client.py --push --file user_stories_20260121_120000.json
```
- Notes:
    - The client expects the MCP Server to be reachable (default `http://127.0.0.1:8000/mcp`).
    - If the server uses a different port, update `MCP_SERVER_URL` in the client or set the corresponding environment variables.

4) Data formats and expectations
- Extraction JSON: must include `user_stories` array where each story has `id`, `title`, `description`, `acceptance_criteria` (list), and optional `tasks` (list of task objects with `id`, `title`, `description`, `notes`).
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

## Extraction Agent (brief)

- **File**: `user_story_extraction_agent.py`
- **Purpose**: Uses an Azure OpenAI-backed conversational agent to extract structured user stories and tasks from meeting transcripts or documents, validate them with Pydantic models, and save them to JSON for ingestion by the MCP client.
- **Key design points**:
    - Uses Pydantic models `Task`, `UserStory`, and `ExtractionResponse` to strictly validate LLM output.

    - Exposes tools (via `@ai_function`) for `save_user_stories`, `add_user_story`, `update_user_story`, `remove_user_story`, `list_all_stories`, `get_story_details`, `add_task`, and `list_tasks` so the agent can mutate and manage stories programmatically.
    - Conversational flow separates extraction (agent with response model) and tool-driven conversational management (`conversational_agent`).
    - Designed for human-in-the-loop: clarifications are surfaced and the user can approve before saving.

- **Output**: Saves timestamped JSON files into the `output/` folder (default `./output`) with a `metadata` block and the validated `user_stories` payload. These files are the expected input for `US_MCP_Client.py`.
- **How it works (short)**:
    1. Read a `.txt` or `.docx` transcript using `read_document()`.
 2. Run `agent.run()` with an extraction prompt; parse and validate the JSON using `ExtractionResponse`.
 3. Display results and optionally enter a clarification loop where the agent uses tools to request or apply changes.
 4. When approved, call `save_user_stories` which writes a file in `output/` for the MCP client to upload.

Example run (interactive):
```bash
python user_story_extraction_agent.py
# then follow prompts to load a document and save approved stories
```

## Client Input & Flow (LLM → Client)

- **Purpose**: This document focuses on the MCP *client* behavior — how the client consumes an extraction JSON file and calls MCP tools to push work items. The server implementation details are intentionally omitted here; the client expects the server to expose the required tools (names listed below).

- **Input**: A validated extraction JSON file produced by the LLM extraction agent (`user_story_extraction_agent.py`) saved in the `output/` directory (e.g., `output/user_stories_20260121_120000.json`). The client consumes this file; you do not need server internals to run the client.

- **Run the client**:
```powershell
Set-Location 'c:\Ai Support Companion\WokingOnMCP\ADO_MCP_Client'
python US_MCP_Client.py --push --file user_stories_20260121_120000.json
```

- **Environment / Configuration**:
    - `MCP_SERVER_URL`: URL of the MCP server endpoint (default: `http://127.0.0.1:8000/mcp`). If your server uses a different port or host, update this value in `US_MCP_Client.py` or set the corresponding environment variable used by your client.

- **Client Sequence (what the client does)**:
 1. Load and validate the extraction JSON from `output/`.
 2. For each `user_story` in the file, call the server tool to create a user story and parse the returned ADO work item `id`.
 3. For each task under a user story, call the server tool to create the task and collect its `id`.
 4. Call the server tool to link each created task to its parent user story.
 5. Update the user story description to include task references and persist the update.

- **Server tools expected by the client (implemented in server)**:
    - `create_user_story` — create a user-story work item (used by the client to create stories).
    - `create_work_item` — generic work item creator (used to create tasks or other types).
    - `add_parent_link` — create a parent-child relation between work items.
    - `update_work_item` — update fields (description, state, etc.) on an existing work item.
    (These are referenced by name here; their implementation lives in the MCP server.)

- **Data formats & expectations (client side)**:
    - The input JSON must contain a top-level `user_stories` array; each story should include `id`, `title`, `description`, `acceptance_criteria` (list), and optionally `tasks` (list of task objects with `id`, `title`, `description`, `notes`).
    - The client expects each tool call to return JSON text containing at least an `id` field for created items; `US_MCP_Client.py` parses `result.content[0].text` via `json.loads()`.

- **Example JSON** (client input):
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

- **Example command** (client):
```powershell
python US_MCP_Client.py --push --file user_stories.json
```