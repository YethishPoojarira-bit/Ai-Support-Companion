# Goal Setting MCP Server Demo

A FastAPI-based HTTP wrapper for the CrewAI Goal Setting Crew, providing RESTful endpoints to interact with the goal setting system.

## 🎯 Overview

This MCP Server Demo provides HTTP endpoints that interface with the CrewAI goal setting crew, allowing external systems to interact with the goal setting process through REST APIs instead of console interaction.

## 🚀 Features

- **RESTful API** - HTTP endpoints for all goal setting operations
- **Mock Mode** - Runs with mock responses when CrewAI isn't available
- **CrewAI Integration** - Interfaces with the goal setting crew (when available)
- **Session State** - Maintains goal data across requests
- **Error Handling** - Comprehensive error responses

## 📋 Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check and service status |
| `/status` | GET | Detailed status including dependencies |
| `/ask` | POST | Ask goal-setting questions and get responses |
| `/summary` | POST | Generate comprehensive goal summary |
| `/goal-data` | GET | Retrieve current goal data state |
| `/reset` | POST | Reset goal data to start fresh |

## 🔧 Installation

1. **Install dependencies:**
```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

2. **Set up environment variables** (optional, for real CrewAI integration):
Create a `.env` file:
```env
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

## 🚀 Running the Server

```bash
# Start the server
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --port 8000
```

The server will start at `http://127.0.0.1:8000`

## 📝 Usage Examples

### 1. Check Status
```bash
curl http://127.0.0.1:8000/status
```

### 2. Ask Goal Questions
```bash
# Ask about goal type
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "task": "goal_type",
    "user_input": "I want to improve my programming skills"
  }'

# Ask about description
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "task": "description", 
    "user_input": "I want to become proficient in backend development with .NET"
  }'

# Ask about timeline
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "task": "timeline",
    "user_input": "I want to achieve this in 6 months"
  }'

# Ask about metrics
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "task": "metrics",
    "user_input": "Build 3 complete APIs and get certified"
  }'
```

### 3. Generate Summary
```bash
curl -X POST http://127.0.0.1:8000/summary \
  -H "Content-Type: application/json" \
  -d '{
    "goal_data": {
      "goal_type": "Skill Enhancement",
      "description": "Become proficient in .NET backend development",
      "timeline": "6 months", 
      "metrics": ["Build 3 complete APIs", "Get certified"]
    }
  }'
```

### 4. Check Current Goal Data
```bash
curl http://127.0.0.1:8000/goal-data
```

### 5. Reset Goal Data
```bash
curl -X POST http://127.0.0.1:8000/reset
```

## 🌐 Interactive Documentation

Once the server is running, visit:
- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

## 🔄 Integration Flow

The typical flow for using this API:

1. **Check Status** - Verify service is running
2. **Ask Questions** - Send user inputs for each goal aspect:
   - `goal_type` - What kind of goal?
   - `description` - What do you want to achieve?
   - `timeline` - When do you want to achieve it?
   - `metrics` - How will you measure success?
3. **Generate Summary** - Get comprehensive goal summary with action steps
4. **Reset** (optional) - Clear data for next session

## 🤖 Mock Mode

When CrewAI is not available, the server runs in mock mode with realistic responses. This allows:
- Testing API endpoints without full setup
- Development and integration work
- Demonstration of the flow

## 🔗 CrewAI Integration

The server is designed to integrate with the CrewAI Goal Setting Crew located at:
`../../CrewAI/goal_setting_crew/src/`

When properly configured, it will:
- Import the `GoalSettingCrew` class
- Execute agent tasks through the crew
- Return real AI-generated responses

## 🛠️ Development

### Project Structure
```
MCPServer_Demo/
├── main.py              # FastAPI server implementation
├── pyproject.toml       # Dependencies and project config
├── README.md           # This file
└── .env                # Environment variables (create manually)
```

### Adding New Endpoints
Add new routes to `main.py` following the existing pattern:
```python
@app.post("/new-endpoint")
async def new_endpoint(request: RequestModel):
    # Implementation here
    return ResponseModel(...)
```

## 🚨 Error Handling

The API returns appropriate HTTP status codes:
- `200` - Success
- `422` - Validation Error (invalid request format)
- `500` - Internal Server Error

Error responses include descriptive messages to help with debugging.

## 📊 Monitoring

Check server logs for:
- Request/response details
- Error information
- Performance metrics
- CrewAI integration status

## 🎯 Next Steps

1. **Test the API** - Use the curl examples above
2. **Integrate with CrewAI** - Ensure the crew import works
3. **Add Authentication** - For production deployments
4. **Add Database** - For persistent goal storage
5. **Add WebSocket** - For real-time interactions

## 🤝 Contributing

This is a demonstration project. Feel free to extend it with additional features!
