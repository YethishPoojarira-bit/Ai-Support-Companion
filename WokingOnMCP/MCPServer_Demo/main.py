"""
Simple Goal Setting MCP Server - FastMCP Example
A basic MCP server for studying and understanding MCP concepts.

Run with: python main.py
"""

import json
import os
from datetime import datetime
from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Goal Setting Demo", json_response=True)

# Simple in-memory storage for goal data
goal_data = {
    "goal_type": "",
    "description": "", 
    "timeline": "",
    "metrics": []
}

# Tool to set goal type
@mcp.tool()
def set_goal_type(goal_type: str) -> str:
    """Set the type of corporate goal (e.g., Revenue Growth, Skill Enhancement)"""
    goal_data["goal_type"] = goal_type
    return f"Goal type set to: {goal_type}"

# Tool to set goal description  
@mcp.tool()
def set_goal_description(description: str) -> str:
    """Set detailed description of what you want to achieve"""
    goal_data["description"] = description
    return f"Goal description updated: {description[:50]}..."

# Tool to set timeline
@mcp.tool()
def set_timeline(timeline: str) -> str:
    """Set when you want to achieve this goal"""
    goal_data["timeline"] = timeline
    return f"Timeline set to: {timeline}"

# Tool to add success metric
@mcp.tool()
def add_metric(metric: str) -> str:
    """Add a metric to measure goal success"""
    goal_data["metrics"].append(metric)
    return f"Added metric: {metric}. Total metrics: {len(goal_data['metrics'])}"

# Tool to get goal summary
@mcp.tool()
def get_goal_summary() -> dict:
    """Get current goal information summary"""
    summary = {
        "goal_type": goal_data["goal_type"] or "Not set",
        "description": goal_data["description"] or "Not set", 
        "timeline": goal_data["timeline"] or "Not set",
        "metrics": goal_data["metrics"] if goal_data["metrics"] else ["Not set"],
        "completeness": "Complete" if all([goal_data["goal_type"], goal_data["description"], goal_data["timeline"], goal_data["metrics"]]) else "Incomplete"
    }
    
    # Auto-save when getting summary
    save_goal_to_file()
    
    return summary


# Resource to get current goal data
@mcp.resource("goal://current")
def get_current_goal() -> str:
    """Get the current goal data as formatted text"""
    return f"""
Current Goal Information:
- Type: {goal_data['goal_type'] or 'Not set'}
- Description: {goal_data['description'] or 'Not set'}
- Timeline: {goal_data['timeline'] or 'Not set'}
- Metrics: {', '.join(goal_data['metrics']) if goal_data['metrics'] else 'Not set'}
"""


# Prompt for goal setting guidance
@mcp.prompt()
def goal_setting_guide(focus: str = "general") -> str:
    """Generate guidance prompt for goal setting"""
    guides = {
        "general": "Please help the user set a clear, achievable corporate goal. Ask about their goal type, what they want to accomplish, timeline, and success metrics.",
        "smart": "Please guide the user to create a SMART goal (Specific, Measurable, Achievable, Relevant, Time-bound). Focus on clarity and actionability.",
        "metrics": "Please help the user define concrete success metrics for their goal. Focus on both quantitative and qualitative measures."
    }
    
    return guides.get(focus, guides["general"])


# Tool to save goal data to JSON file
@mcp.tool()
def save_goal() -> str:
    """Save current goal data to JSON file"""
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    OUTPUT_DIR = os.path.join(BASE_DIR, "output")
    return save_goal_to_file(OUTPUT_DIR=OUTPUT_DIR)

def save_goal_to_file(OUTPUT_DIR) -> str:
    """Internal function to save goal data to JSON file"""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # os.makedirs("output", exist_ok=True)
        
        # Prepare data for saving
        save_data = {
            "goal_data": goal_data,
            "timestamp": datetime.now().isoformat(),
            "completeness": "Complete" if all([goal_data["goal_type"], goal_data["description"], goal_data["timeline"], goal_data["metrics"]]) else "Incomplete"
        }
        
        # Save to JSON file
        filepath = os.path.join(OUTPUT_DIR, "goal_data.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        return f"Goal data saved to {filepath}"
    
    except Exception as e:
        return f"Error saving goal data: {str(e)}"

# Simple reset function
@mcp.tool()
def reset_goal() -> str:
    """Reset all goal data to start fresh"""
    # Save current data before resetting
    save_result = save_goal_to_file()
    
    # Reset the data
    goal_data["goal_type"] = ""
    goal_data["description"] = ""
    goal_data["timeline"] = ""
    goal_data["metrics"] = []
    
    return f"Goal data reset successfully. Previous data saved. ({save_result})"

# Run with streamable HTTP transport
if __name__ == "__main__":
    print("🎯 Starting Simple Goal Setting MCP Server...")
    print("📋 Available tools: set_goal_type, set_goal_description, set_timeline, add_metric, get_goal_summary, save_goal, reset_goal")
    print("📄 Available resources: goal://current")
    print("💡 Available prompts: goal_setting_guide")
    print("💾 Goal data will be auto-saved to output/goal_data.json")
    print("🌐 Server starting on streamable HTTP transport...")
    
    try:
        mcp.run(transport="streamable-http")
    except KeyboardInterrupt:
        print("\n🛑 Server stopping...")
        final_save = save_goal_to_file()
        print(f"💾 Final save: {final_save}")
        print("👋 Server stopped.")