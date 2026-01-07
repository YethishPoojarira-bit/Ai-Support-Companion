# User Story Extraction Agent

An intelligent agent powered by Microsoft Agent Framework that extracts user stories from meeting transcripts and documents with **human-in-the-loop verification**.

## Features

✅ **Intelligent Extraction**: Uses Azure OpenAI to understand context and extract meaningful user stories  
✅ **Multiple Formats**: Supports `.txt` and `.docx` files  
✅ **Interactive Clarification**: Agent asks questions when information is unclear  
✅ **Human Verification**: Review, refine, and approve stories before saving  
✅ **Structured Output**: Generates well-formatted JSON with acceptance criteria and priorities  
✅ **Conversation History**: Maintains context throughout the extraction process  

## Prerequisites

- Python 3.10 or later
- Azure OpenAI service endpoint and deployment
- Azure CLI installed and authenticated
- User has Cognitive Services OpenAI User or Contributor role

## Installation

### 1. Clone or navigate to the project directory

```bash
cd "c:\Ai Support Companion\WokingOnMCP\Agent_Based_ADO_Automation"
```

### 2. Create and activate virtual environment

```powershell
# Create venv
python -m venv venv

# Activate (PowerShell)
.\venv\Scripts\Activate.ps1

# On Windows CMD:
# venv\Scripts\activate.bat
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Azure OpenAI

Create a `.env` file (copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` and add your Azure OpenAI details:

```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your-gpt-4-deployment-name
AZURE_OPENAI_API_VERSION=2024-08-01-preview
OUTPUT_DIR=./output
```

### 5. Authenticate with Azure CLI

```bash
az login
```

## Usage

### Running the Agent

```bash
python user_story_extraction_agent.py
```

### Interactive Workflow

1. **Provide Document Path**: Enter the path to your `.txt` or `.docx` file
2. **Review Extracted Stories**: Agent displays all identified user stories
3. **Interactive Options**:
   - **Ask clarification questions** if requirements are unclear
   - **Refine specific stories** based on feedback
   - **Approve and save** when satisfied
   - **Save without approval** for draft versions
   - **Exit** without saving

### Example Interaction

```
📂 Enter path to document (.txt or .docx): meeting_notes.txt

🤖 Agent analyzing 'meeting_notes.txt'...
📄 Document length: 2450 characters

================================================================================
📋 EXTRACTED USER STORIES (5 found)
================================================================================

🎯 US-001: User Login with Multi-Factor Authentication
   Priority: High
   Confidence: High

   Description:
   As a user, I want to log in with multi-factor authentication so that my account is secure

   Acceptance Criteria:
   1. User can enable MFA in settings
   2. SMS and authenticator app options available
   3. Backup codes provided during setup

   Notes: Mentioned security requirement in meeting

--------------------------------------------------------------------------------

🔄 What would you like to do?
1. Ask a clarification question
2. Refine a specific user story
3. Approve and save
4. Save without approval
5. Exit without saving

Enter your choice (1-5): 1

❓ Your question: What authentication methods should we support?

🤖 Agent: Based on the meeting notes, the team discussed supporting...
```

## Output Format

Saved JSON structure:

```json
{
  "metadata": {
    "extracted_at": "2026-01-06T10:30:00",
    "approved": true,
    "agent": "UserStoryExtractionAgent",
    "total_stories": 5
  },
  "user_stories": [
    {
      "id": "US-001",
      "title": "User Login with MFA",
      "description": "As a user, I want to...",
      "acceptance_criteria": ["Criterion 1", "Criterion 2"],
      "priority": "High",
      "confidence": "High",
      "notes": "Additional context",
      "clarifications_needed": []
    }
  ],
  "summary": "Brief overview of extracted stories",
  "questions": []
}
```

## Agent Capabilities

### Extraction Patterns
- **As a... I want... so that...** format recognition
- Requirement keywords detection (should, must, need, want)
- Priority and dependency identification
- Acceptance criteria extraction

### Quality Assurance
- Confidence scoring (High/Medium/Low)
- Missing information flagging
- Clarification question generation
- Source text traceability

### Human-in-the-Loop
- Interactive refinement
- Story-by-story editing
- Approval workflow
- Conversation history

## Project Structure

```
Agent_Based_ADO_Automation/
├── venv/                           # Virtual environment
├── output/                         # Saved user stories (JSON)
├── user_story_extraction_agent.py  # Main agent implementation
├── requirements.txt                # Python dependencies
├── .env                            # Configuration (not in git)
├── .env.example                    # Example configuration
└── README.md                       # This file
```

## Troubleshooting

### Azure OpenAI Connection Issues
```bash
# Verify authentication
az account show

# Check your OpenAI resource
az cognitiveservices account show --name <your-resource-name> --resource-group <your-rg>
```

### Import Errors
```bash
# Ensure virtual environment is activated
.\venv\Scripts\Activate.ps1

# Reinstall dependencies
pip install -r requirements.txt
```

### Document Reading Errors
- Ensure file path is correct and accessible
- For `.docx` files, verify `python-docx` is installed
- Check file encoding for `.txt` files (should be UTF-8)

## Advanced Usage

### Programmatic API

```python
from user_story_extraction_agent import UserStoryExtractionAgent
import asyncio

async def extract_stories_programmatically():
    agent = UserStoryExtractionAgent()
    
    # Read document
    content = agent.read_document("meeting_transcript.txt")
    
    # Extract stories
    stories = await agent.extract_user_stories(content, "meeting_transcript.txt")
    
    # Refine specific story
    refined = await agent.refine_story("US-001", "Add more acceptance criteria")
    
    # Approve and save
    agent.approved = True
    agent.save_stories("final_stories.json")

asyncio.run(extract_stories_programmatically())
```

## Contributing

Suggestions and improvements welcome! Key areas:
- Additional document formats (PDF, Markdown)
- Integration with Azure DevOps API
- Export to other formats (CSV, Excel)
- Batch processing multiple documents

## License

MIT License

## Support

For issues with:
- **Microsoft Agent Framework**: [Agent Framework Docs](https://learn.microsoft.com/en-us/agent-framework/)
- **Azure OpenAI**: [Azure OpenAI Docs](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- **This Agent**: Open an issue in the repository

---

**Happy Story Extraction! 🎯**
