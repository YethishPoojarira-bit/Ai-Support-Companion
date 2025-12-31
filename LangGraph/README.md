# Corporate Goal Setting Agent 🎯

A simple LangGraph-based agent that helps you interactively set up corporate goals through natural conversation.

## Features

- 🤖 Interactive AI-powered conversation
- 📊 Structured goal setting process
- 🎯 Covers goal type, description, timeline, and metrics
- 💾 Option to save goals to a file
- ✨ Built with LangGraph for clear workflow management

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
   - Add your Azure OpenAI credentials to the `.env` file:
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

The agent will guide you through:
1. **Goal Type**: What kind of corporate goal (Revenue, Customer Satisfaction, etc.)
2. **Description**: Detailed explanation of what you want to achieve
3. **Timeline**: When you want to achieve this goal
4. **Key Metrics**: How you'll measure success
5. **Summary**: A structured summary with action steps

## Example Interaction

```
🎯 Corporate Goal Setting Assistant
==================================================

🤖 Assistant: Hello! I'd love to help you set a corporate goal. 
What type of goal would you like to focus on today? For example, 
it could be related to Revenue, Customer Satisfaction, Employee 
Development, Operational Efficiency, or something else entirely.

👤 You: Customer Satisfaction

🤖 Assistant: Great choice! Customer satisfaction is crucial for 
long-term success. Can you describe in detail what you'd like to 
achieve with this goal?

👤 You: Improve our NPS score and reduce customer complaints by 50%
...
```

## Architecture

The agent uses LangGraph's StateGraph to manage conversation flow:
- **Nodes**: Each step in the goal-setting process
- **State**: Maintains conversation history and collected information
- **Conditional Edges**: Routes between steps based on progress

## Requirements

- Python 3.8+
- Azure OpenAI resource with GPT-4o-mini deployment
- Dependencies listed in requirements.txt

## License

MIT
