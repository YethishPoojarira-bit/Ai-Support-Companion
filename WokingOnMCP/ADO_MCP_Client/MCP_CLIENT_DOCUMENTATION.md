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

## Azure DevOps Integration Details

### Authentication
- Server uses Personal Access Token (PAT) from environment variables
- `AZURE_DEVOPS_PAT`: PAT with work item permissions
- `AZURE_DEVOPS_ORG_URL`: Organization URL
- `AZURE_DEVOPS_PROJECT`: Default project name

### API Interactions
- **Work Item Creation**: Uses JSON Patch operations via `PATCH /_apis/wit/workitems/$type`
- **Parent-Child Linking**: Uses Relations API with `System.LinkTypes.Hierarchy-Reverse`
- **Updates**: JSON Patch for field modifications
- **Error Handling**: Captures HTTP status codes and error messages

### Data Flow
1. Client → MCP Server (tool call with arguments)
2. MCP Server → Azure DevOps REST API (authenticated request)
3. Azure DevOps → MCP Server (response with work item data)
4. MCP Server → Client (structured JSON response)
5. Client processes and continues workflow

## Error Handling and Resilience

### Tool Call Errors
- Checks `result.isError` for failed tool calls
- Parses error responses from server
- Continues processing other items on individual failures

### ADO API Errors
- Handles 400/401/403 status codes
- Skips problematic fields (e.g., invalid assignees)
- Logs detailed error information

### Connection Issues
- Uses async context managers for proper cleanup
- Times out requests appropriately
- Provides summary statistics

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