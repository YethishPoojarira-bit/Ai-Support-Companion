# Simple Goal Setting MCP Server

A very basic MCP server implementation for learning and understanding MCP concepts.

## 🎯 What This Does

This is a simplified MCP (Model Context Protocol) server that demonstrates the core MCP concepts:

- **Tools** - Functions that can be called by LLM clients
- **Resources** - Data that can be retrieved
- **Prompts** - Template prompts for LLM interactions

## 🔧 Installation

```bash
# Install the MCP library
pip install mcp

# Or using uv
uv add mcp
```

## 🚀 Running the Server

```bash
python simple_mcp.py
```

## 📋 Available Features

### Tools (Functions LLMs can call):
- `set_goal_type(goal_type: str)` - Set the type of goal
- `set_goal_description(description: str)` - Set goal description  
- `set_timeline(timeline: str)` - Set when to achieve the goal
- `add_metric(metric: str)` - Add a success metric
- `get_goal_summary()` - Get current goal summary
- `reset_goal()` - Clear all goal data

### Resources (Data that can be retrieved):
- `goal://current` - Get formatted current goal information

### Prompts (Templates for LLM guidance):
- `goal_setting_guide(focus="general")` - Get guidance prompts
  - Options: "general", "smart", "metrics"

## 📝 Example Usage Flow

1. **Set Goal Type**: `set_goal_type("Skill Enhancement")`
2. **Add Description**: `set_goal_description("Learn Python programming")`
3. **Set Timeline**: `set_timeline("6 months")`  
4. **Add Metrics**: `add_metric("Complete 5 projects")`
5. **Get Summary**: `get_goal_summary()`
6. **View Resource**: Access `goal://current`
7. **Reset**: `reset_goal()` to start over

## 🔍 Key MCP Concepts Demonstrated

### 1. Tools (@mcp.tool())
Functions that external LLM clients can discover and call:
```python
@mcp.tool()
def set_goal_type(goal_type: str) -> str:
    """Set the type of corporate goal"""
    goal_data["goal_type"] = goal_type
    return f"Goal type set to: {goal_type}"
```

### 2. Resources (@mcp.resource())  
Data sources that can be retrieved with URI patterns:
```python
@mcp.resource("goal://current")
def get_current_goal() -> str:
    """Get the current goal data"""
    return formatted_goal_info
```

### 3. Prompts (@mcp.prompt())
Template prompts for LLM interactions:
```python
@mcp.prompt()
def goal_setting_guide(focus: str = "general") -> str:
    """Generate guidance for goal setting"""
    return prompt_templates[focus]
```

## 🆚 Comparison with Other Implementations

| Feature | SemanticKernel | LangGraph | CrewAI | **MCP Server** |
|---------|----------------|-----------|--------|----------------|
| Approach | Function plugins | State graphs | Agent collaboration | **Protocol tools** |
| Interaction | Console chat | Console chat | Console chat | **Client-server** |
| Integration | Direct calling | Direct calling | Direct calling | **Protocol-based** |
| Best For | Plugin systems | Complex flows | Multi-agent tasks | **Tool exposure** |

## 🔗 How MCP Differs

Unlike the other implementations that run complete conversations:
- **MCP exposes individual functions** that clients can call
- **Clients decide the conversation flow** 
- **Server provides tools, clients orchestrate**
- **Protocol-based** - can work with any MCP-compatible client

## 🎓 Learning Points

1. **Decorators**: `@mcp.tool()`, `@mcp.resource()`, `@mcp.prompt()`
2. **Transport**: Uses "streamable-http" for web communication  
3. **State Management**: Simple in-memory dict for data storage
4. **Return Types**: Tools return strings/dicts, resources return strings
5. **URI Patterns**: Resources use URI-like identifiers

This is the simplest possible MCP server - perfect for understanding the basics!

## 🔧 Next Steps

1. Run `python simple_mcp.py`
2. Use an MCP client to connect and call tools
3. Try modifying the tools and resources
4. Experiment with different prompt templates
5. Add more complex goal-setting logic

Happy learning! 🎉