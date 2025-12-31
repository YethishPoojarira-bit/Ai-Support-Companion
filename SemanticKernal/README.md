# Corporate Goal Setting Agent 🎯 (Semantic Kernel)

A Semantic Kernel-based agent that helps you interactively set up corporate goals through natural conversation using function calling.

## Features

- 🤖 **Semantic Kernel Plugins**: Uses SK plugins for modular goal management
- 🔧 **Function Calling**: Automatically calls functions to extract and store information
- 💬 **Natural Conversation**: LLM decides when to call functions based on user input
- 📊 **Structured Goal Setting**: Covers goal type, description, timeline, and metrics
- 💾 **Goal Persistence**: Save goals to a file
- ✨ **Intelligent Extraction**: LLM interprets user input and fills state automatically

## Architecture

The agent uses Semantic Kernel's function calling capabilities:

- **GoalSettingPlugin**: Contains functions for managing goal state
  - `update_goal_type()`: Store goal type
  - `update_goal_description()`: Store description
  - `update_timeline()`: Store timeline
  - `add_metric()`: Add success metrics
  - `get_goal_status()`: Check collected information
  - `check_completeness()`: Verify all info is collected

- **GoalSettingAgent**: Main agent orchestrating the conversation
  - Uses Azure OpenAI with function calling
  - Manages chat history
  - Decides when to call functions vs respond naturally

## Setup

1. **Activate the virtual environment:**
   ```bash
   .\.venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure your Azure OpenAI credentials:**
   - Copy `.env.example` to `.env`
   - Ensure your Azure OpenAI credentials are set:
     ```
     AZURE_OPENAI_API_KEY=your_azure_api_key_here
     AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
     AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini
     AZURE_OPENAI_API_VERSION=2024-08-01-preview
     ```

## Usage

Run the agent:
```bash
python goal_setting_agent.py
```

The agent will guide you through setting up a corporate goal naturally. Just have a conversation!

## Example Interaction

```
🎯 Corporate Goal Setting Assistant (Semantic Kernel)
==================================================

🤖 Assistant: Hello! I'm here to help you set up a corporate goal.
What would you like to achieve in your organization?

👤 You: I want to improve our customer satisfaction significantly 
by the end of Q2 with better NPS scores

🤖 Assistant: Excellent! I've noted that you want to improve 
customer satisfaction by the end of Q2, focusing on NPS scores.
Could you tell me more about what specific NPS score you're 
targeting?

👤 You: We want to go from 45 to 70
...
```

## How It Works

1. **User speaks naturally**: No need to follow a rigid format
2. **LLM extracts information**: Calls appropriate functions to store data
3. **Agent tracks progress**: Uses `get_goal_status()` to know what's collected
4. **Smart questioning**: Only asks for missing information
5. **Auto-completion**: When `check_completeness()` returns "complete", provides summary

## Requirements

- Python 3.8+
- Azure OpenAI resource with GPT-4o-mini deployment
- Semantic Kernel
- Dependencies listed in requirements.txt

## Comparison with LangGraph Version

**Semantic Kernel approach:**
- Uses function calling (plugins) for state management
- More modular with separate plugin functions
- Leverages SK's built-in function orchestration
- Natural fit for Azure OpenAI ecosystem

**LangGraph approach:**
- Uses state graph for explicit flow control
- More visual workflow representation
- Better for complex multi-step processes with branching logic

Both achieve intelligent goal extraction but with different architectural patterns!

## License

MIT
