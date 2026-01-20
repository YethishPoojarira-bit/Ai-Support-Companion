# Azure DevOps MCP Server Documentation

## Overview

The Azure DevOps MCP Server (`US_MCP_Server.py`) is a FastMCP-based Model Context Protocol server that provides comprehensive tools for interacting with Azure DevOps work items. It enables AI assistants to create, read, update, and manage work items (User Stories, Tasks, Bugs) with full parent-child relationship support.

## Architecture

### Core Components

1. **FastMCP Framework**: Uses the FastMCP library for MCP protocol implementation
2. **Azure DevOps REST API**: Interfaces with ADO v7.0 API endpoints
3. **Authentication**: Uses Personal Access Tokens (PAT) for ADO authentication
4. **Local Logging**: Maintains JSONL records of created work items

### Transport Protocol

The server runs using `streamable-http` transport, enabling persistent connections and session management for efficient communication with MCP clients.

## Configuration

### Environment Variables

```bash
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/your-organization
AZURE_DEVOPS_PAT=your_personal_access_token
AZURE_DEVOPS_PROJECT=your_default_project
AZURE_DEVOPS_API_VERSION=7.0
```

### Authentication

Uses HTTP Basic Authentication with:
- Username: Empty string
- Password: Personal Access Token

## Tools Overview

### 1. `create_work_item`

**Purpose**: Create any type of Azure DevOps work item with full field support.

**Parameters**:
- `project` (str): Project name (default: DEFAULT_PROJECT)
- `work_item_type` (str): Type of work item ("Task", "User Story", "Bug", etc.)
- `title` (str): Work item title (required)
- `description` (str): Work item description
- `assigned_to` (str): Email/display name of assignee
- `area_path` (str): Area path for organization
- `iteration_path` (str): Iteration/sprint path
- `acceptance_criteria` (str): Acceptance criteria (formatted as HTML list)
- `parent_id` (int): ID of parent work item for automatic linking

**ADO Interaction**:
- Uses JSON Patch operations to set work item fields
- Automatically establishes parent-child relationships using Relations API
- URL: `PATCH /{org}/{project}/_apis/wit/workitems/${work_item_type}`
- Content-Type: `application/json-patch+json`

**Special Features**:
- **Automatic Parent Linking**: When `parent_id` is provided, automatically creates parent-child relationship using ADO Relations API
- **Field Formatting**: Converts acceptance criteria to HTML unordered list
- **Error Handling**: Returns detailed error information including status codes and ADO error messages

### 2. `get_work_item`

**Purpose**: Retrieve detailed information about a specific work item.

**Parameters**:
- `work_item_id` (int): The ID of the work item to retrieve

**ADO Interaction**:
- URL: `GET /{org}/_apis/wit/workitems/{id}`
- Returns full work item data including fields, relations, and links

### 3. `create_user_story`

**Purpose**: Convenience wrapper for creating User Stories with automatic type detection.

**Parameters**:
- `project` (str): Project name
- `title` (str): User story title
- `description` (str): User story description
- `assigned_to` (str): Assignee
- `acceptance_criteria` (str): Acceptance criteria

**ADO Interaction**:
- Tries multiple work item types: "User Story", "Product Backlog Item"
- Uses the first successful type for the organization's process template

### 4. `create_task_for_user_story`

**Purpose**: Create a task and automatically link it to a parent User Story.

**Parameters**:
- `user_story_id` (int): ID of the parent User Story
- `title` (str): Task title (required)
- `description` (str): Task description
- `assigned_to` (str): Assignee (left empty to avoid identity errors)
- `project` (str): Project name

**ADO Interaction**:
- Calls `create_work_item` with `parent_id` set to establish automatic linking
- Uses Relations API for reliable parent-child relationship creation

### 5. `list_recent_created`

**Purpose**: Return locally logged records of recently created work items.

**Parameters**:
- `limit` (int): Maximum number of records to return (default: 20)

**Implementation**:
- Reads from local JSONL file: `output/created_work_items.json`
- Returns most recent records based on creation timestamp

### 6. `health_check`

**Purpose**: Verify ADO connectivity and authentication.

**ADO Interaction**:
- URL: `GET /{org}/_apis/projects`
- Returns project count and sample project names
- Used to validate PAT and organization access

### 7. `list_team_members`

**Purpose**: Retrieve all team members across all teams in a project.

**Parameters**:
- `project` (str): Project name

**ADO Interaction**:
- Gets project ID from project name
- Retrieves all teams in the project
- Fetches members from each team
- Avoids duplicate members across teams

**Returns**:
- Member count and detailed member information (ID, display name, email, team)

### 8. `assign_work_item`

**Purpose**: Assign a work item to a specific person.

**Parameters**:
- `work_item_id` (int): Work item ID to assign
- `person_name` (str): Display name or email of assignee

**ADO Interaction**:
- URL: `PATCH /{org}/_apis/wit/workitems/{id}`
- Uses JSON Patch to update `System.AssignedTo` field
- Returns updated work item information

### 9. `add_parent_link`

**Purpose**: Establish parent-child relationship between existing work items.

**Parameters**:
- `child_work_item_id` (int): ID of child work item
- `parent_work_item_id` (int): ID of parent work item

**ADO Interaction**:
- Uses Relations API to add hierarchy link
- URL: `PATCH /{org}/_apis/wit/workitems/{child_id}`
- Adds relation with type: `System.LinkTypes.Hierarchy-Reverse`

**Implementation Details**:
- Creates JSON Patch operation to add relation
- Sets comment attribute for tracking
- Returns success confirmation with work item details

### 10. `list_user_stories`

**Purpose**: Query and list User Stories in a project with filtering options.

**Parameters**:
- `project` (str): Project name
- `state` (str): Filter by state ("New", "Active", "Resolved", "Closed")
- `limit` (int): Maximum results (default: 50)

**ADO Interaction**:
- Uses WIQL (Work Item Query Language) for efficient querying
- Supports both "User Story" and "Product Backlog Item" types
- Orders results by ID descending (most recent first)

**Query Structure**:
```sql
SELECT [System.Id], [System.Title], [System.State], [System.AssignedTo],
       [Microsoft.VSTS.Common.Priority], [System.IterationPath]
FROM WorkItems
WHERE [System.TeamProject] = '{project}'
AND [System.WorkItemType] IN ('User Story', 'Product Backlog Item')
[AND [System.State] = '{state}']
ORDER BY [System.Id] DESC
```

### 11. `update_work_item`

**Purpose**: Update multiple fields of an existing work item.

**Parameters**:
- `work_item_id` (int): Work item ID to update
- `title` (str): New title
- `description` (str): New description
- `state` (str): New state
- `assigned_to` (str): New assignee
- `priority` (int): New priority
- `area_path` (str): New area path
- `iteration_path` (str): New iteration path
- `acceptance_criteria` (str): New acceptance criteria
- `parent_id` (int): New parent work item ID

**ADO Interaction**:
- URL: `PATCH /{org}/_apis/wit/workitems/{id}`
- Uses JSON Patch operations for each provided field
- Supports partial updates (only provided fields are updated)

### 12. `get_child_work_items`

**Purpose**: Retrieve all child work items for a given parent.

**Parameters**:
- `parent_id` (int): ID of parent work item
- `project` (str): Project name

**ADO Interaction**:
- Uses WIQL to query work items where `System.Parent = {parent_id}`
- Returns full details for all child work items

**Query Structure**:
```sql
SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType]
FROM WorkItems
WHERE [System.Parent] = {parent_id}
ORDER BY [System.Id]
```

## Azure DevOps API Integration

### Authentication Pattern

```python
def ado_auth():
    from requests.auth import HTTPBasicAuth
    return HTTPBasicAuth("", ADO_PAT)
```

### Common API Patterns

1. **Work Item Creation/Update**:
   - Method: PATCH
   - Content-Type: `application/json-patch+json`
   - Body: Array of JSON Patch operations

2. **Work Item Retrieval**:
   - Method: GET
   - Query parameters: `$expand=all` for full details

3. **WIQL Queries**:
   - Method: POST
   - Content-Type: `application/json`
   - Body: `{"query": "WIQL query string"}`

4. **Batch Operations**:
   - Multiple work item IDs: `?ids=1,2,3,4`

### Parent-Child Relationships

The server implements parent-child relationships using ADO's Relations API:

```json
{
  "op": "add",
  "path": "/relations/-",
  "value": {
    "rel": "System.LinkTypes.Hierarchy-Reverse",
    "url": "{org_url}/_apis/wit/workItems/{parent_id}",
    "attributes": {
      "comment": "Auto-linked during creation"
    }
  }
}
```

## Data Flow and Processing

### Work Item Creation Flow

1. **Input Validation**: Check required fields (title)
2. **Field Preparation**: Format acceptance criteria as HTML
3. **ADO API Call**: Create work item without parent link
4. **Parent Linking**: If `parent_id` provided, use Relations API to link
5. **Local Logging**: Save creation record to JSONL file
6. **Response**: Return work item data with linking status

### Query Processing Flow

1. **WIQL Construction**: Build query based on parameters
2. **ADO Query**: Execute WIQL query to get work item IDs
3. **Batch Retrieval**: Fetch full details for all matching items
4. **Data Formatting**: Structure response with consistent field mapping
5. **Response**: Return formatted work item list

## Error Handling

### ADO API Errors

- **400 Bad Request**: Invalid field values, unknown identities
- **401 Unauthorized**: Invalid PAT or insufficient permissions
- **403 Forbidden**: Missing permissions for operation
- **404 Not Found**: Work item or project not found

### Error Response Format

```json
{
  "ok": false,
  "error": "Descriptive error message",
  "status_code": 400,
  "details": "Full ADO error response"
}
```

### Identity Validation Issues

Common issue with `assigned_to` field:
- ADO requires exact email addresses or display names
- Team names like "AI Development Team" are not valid identities
- Server skips assignment when invalid identities are provided

## Local Data Management

### Creation Logging

- **File**: `output/created_work_items.json`
- **Format**: JSON Lines (one JSON object per line)
- **Content**: Creation timestamp, project, work item type, title, ADO response

### Record Structure

```json
{
  "created": "2024-01-20T12:39:41.123456",
  "project": "Online Learning Portal",
  "work_item_type": "User Story",
  "title": "US-001: Implement user authentication",
  "ado_response": {
    "id": 9490,
    "fields": {...},
    "parent_link_added": true,
    "parent_id": 9489
  }
}
```

## Integration with MCP Clients

### Client Workflow Example

1. **Create User Story**:
   ```python
   result = await session.call_tool("create_user_story", {
       "title": "Implement login feature",
       "description": "Users should be able to log in",
       "acceptance_criteria": "User can enter credentials\nSystem validates credentials"
   })
   ```

2. **Create Linked Tasks**:
   ```python
   user_story_id = result.content[0].text["id"]
   await session.call_tool("create_task_for_user_story", {
       "user_story_id": user_story_id,
       "title": "Build login form",
       "description": "Create HTML form with email/password fields"
   })
   ```

3. **Query Relationships**:
   ```python
   await session.call_tool("get_child_work_items", {
       "parent_id": user_story_id
   })
   ```

## Security Considerations

- **PAT Storage**: Personal Access Tokens stored in environment variables
- **Network Security**: HTTPS-only communication with ADO
- **Permission Scope**: PAT requires appropriate ADO permissions (Work Items: Read/Write)
- **Error Information**: Sensitive error details are truncated in responses

## Performance Optimizations

- **Batch Operations**: Multiple work item retrievals use single API call
- **WIQL Queries**: Efficient querying using Work Item Query Language
- **Connection Reuse**: Persistent HTTP connections via requests library
- **Timeout Handling**: 30-second timeouts for API operations

## Monitoring and Debugging

### Health Check Tool

- Validates ADO connectivity
- Confirms authentication
- Lists available projects

### Local Logging

- All creation operations logged locally
- Enables audit trail and debugging
- JSONL format for easy parsing

### Error Response Details

- Full ADO error messages included in responses
- Status codes and detailed error information
- Helps diagnose integration issues

This MCP server provides a complete interface for AI assistants to manage Azure DevOps work items with robust error handling, automatic relationship management, and comprehensive CRUD operations.