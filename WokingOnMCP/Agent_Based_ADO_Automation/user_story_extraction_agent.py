"""
User Story Extraction Agent using Microsoft Agent Framework
Extracts user stories from meeting transcripts with human-in-the-loop verification.
"""
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Import Microsoft Agent Framework
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential
from agent_framework import ChatMessage, TextContent, Role, ai_function
from typing import Annotated, List, Dict, Optional
from pydantic import Field, BaseModel
from docx import Document

load_dotenv()

# Pydantic models for structured response validation
class UserStory(BaseModel):
    """Model for a single user story."""
    id: str
    title: str
    description: str
    acceptance_criteria: List[str]
    priority: str
    notes: str = ""
    confidence: str
    clarifications_needed: List[str] = []


class ExtractionResponse(BaseModel):
    """Model for the complete extraction response."""
    user_stories: List[UserStory]
    questions: List[str] = []


# Configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") or os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./output"))
OUTPUT_DIR.mkdir(exist_ok=True)


class UserStoryTools:
    """Tools for managing user stories during the conversation."""
    
    def __init__(self, agent_instance):
        """Initialize tools with reference to the parent agent."""
        self.agent = agent_instance
    
    @ai_function(name="save_user_stories", description="Saves the current user stories to a JSON file with optional approval status")
    def save_stories(
        self,
        approved: Annotated[bool, Field(description="Whether the user has approved these stories. Set to True if user confirms approval.")] = False,
        filename: Annotated[Optional[str], Field(description="Optional custom filename for the output. If not provided, a timestamp-based name will be used.")] = None
    ) -> str:
        """Save user stories to JSON file."""
        if not self.agent.extracted_stories:
            return "❌ Error: No user stories to save. Extract stories first."
        
        self.agent.approved = approved
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = filename or f"user_stories_{timestamp}.json"
        output_path = OUTPUT_DIR / file_name
        
        # Add metadata
        output_data = {
            "metadata": {
                "extracted_at": datetime.now().isoformat(),
                "approved": self.agent.approved,
                "agent": "UserStoryExtractionAgent",
                "total_stories": len(self.agent.extracted_stories.get("user_stories", []))
            },
            **self.agent.extracted_stories
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        approval_status = "✅ APPROVED" if approved else "💾 NOT APPROVED"
        result = f"{approval_status} - User stories saved to: {output_path}\n\nTotal stories: {len(self.agent.extracted_stories.get('user_stories', []))}"
        
        # Signal to exit if approved
        if approved:
            result += "\n\n👋 Session complete. Program will exit."
            self.agent.should_exit = True
        
        return result
    
    @ai_function(name="update_user_story", description="Updates a specific user story by ID with new information")
    def update_story(
        self,
        story_id: Annotated[str, Field(description="The ID of the user story to update (e.g., 'US-001', 'US-002')")],
        field: Annotated[str, Field(description="The field to update: 'title', 'description', 'priority', 'notes', 'acceptance_criteria', or 'confidence'")],
        new_value: Annotated[str, Field(description="The new value for the field. For acceptance_criteria, provide as comma-separated list.")]
    ) -> str:
        """Update a specific field in a user story."""
        if not self.agent.extracted_stories or "user_stories" not in self.agent.extracted_stories:
            return "❌ Error: No user stories available to update."
        
        # Find the story
        story_found = False
        for story in self.agent.extracted_stories["user_stories"]:
            if story.get("id") == story_id:
                story_found = True
                old_value = story.get(field, "Not set")
                
                # Handle acceptance criteria as list
                if field == "acceptance_criteria":
                    story[field] = [item.strip() for item in new_value.split(",")]
                else:
                    story[field] = new_value
                
                return f"✅ Updated {story_id} - {field}:\n  Old: {old_value}\n  New: {story[field]}\n\n📋 Current story:\n{json.dumps(story, indent=2)}"
        
        if not story_found:
            available_ids = [s.get("id") for s in self.agent.extracted_stories["user_stories"]]
            return f"❌ Error: Story '{story_id}' not found. Available IDs: {', '.join(available_ids)}"
      
    @ai_function(name="remove_user_story", description="Removes a user story from the list by its ID")
    def remove_story(
        self,
        story_id: Annotated[str, Field(description="The ID of the user story to remove (e.g., 'US-001')")]
    ) -> str:
        """Remove a user story from the list."""
        if not self.agent.extracted_stories or "user_stories" not in self.agent.extracted_stories:
            return "❌ Error: No user stories available."
        
        initial_count = len(self.agent.extracted_stories["user_stories"])
        removed_story = None
        
        # Filter out the story
        self.agent.extracted_stories["user_stories"] = [
            story for story in self.agent.extracted_stories["user_stories"]
            if story.get("id") != story_id or (removed_story := story) is None
        ]
        
        final_count = len(self.agent.extracted_stories["user_stories"])
        
        if initial_count == final_count:
            available_ids = [s.get("id") for s in self.agent.extracted_stories["user_stories"]]
            return f"❌ Error: Story '{story_id}' not found. Available IDs: {', '.join(available_ids)}"
        
        return f"✅ Removed user story: {story_id}\n\nRemaining stories: {final_count}\n\n🗑️ Removed story details:\n{json.dumps(removed_story, indent=2) if removed_story else 'N/A'}"
    
    @ai_function(name="add_user_story", description="Adds a new user story to the current list")
    def add_story(
        self,
        title: Annotated[str, Field(description="Short descriptive title for the user story")],
        description: Annotated[str, Field(description="Detailed description, preferably in 'As a [role], I want [feature] so that [benefit]' format")],
        priority: Annotated[str, Field(description="Priority level: High, Medium, or Low")] = "Medium",
        acceptance_criteria: Annotated[str, Field(description="Comma-separated list of acceptance criteria")] = "",
        notes: Annotated[str, Field(description="Additional notes or context")] = ""
    ) -> str:
        """Add a new user story to the list."""
        if not self.agent.extracted_stories:
            self.agent.extracted_stories = {"user_stories": [], "summary": "", "questions": []}
        
        if "user_stories" not in self.agent.extracted_stories:
            self.agent.extracted_stories["user_stories"] = []
        
        # Generate new ID
        existing_ids = [s.get("id", "") for s in self.agent.extracted_stories["user_stories"]]
        story_numbers = [int(id.replace("US-", "")) for id in existing_ids if id.startswith("US-")]
        next_number = max(story_numbers, default=0) + 1
        new_id = f"US-{next_number:03d}"
        
        # Create new story
        new_story = {
            "id": new_id,
            "title": title,
            "description": description,
            "acceptance_criteria": [item.strip() for item in acceptance_criteria.split(",")] if acceptance_criteria else [],
            "priority": priority,
            "notes": notes,
            "confidence": "High",
            "clarifications_needed": []
        }
        
        self.agent.extracted_stories["user_stories"].append(new_story)
        
        total_stories = len(self.agent.extracted_stories["user_stories"])
        return f"✅ Added new user story: {new_id}\n\nTotal stories: {total_stories}\n\n📋 New story details:\n{json.dumps(new_story, indent=2)}"
    
    @ai_function(name="list_all_stories", description="Lists all current user stories with their IDs and titles")
    def list_stories(self) -> str:
        """List all current user stories."""
        if not self.agent.extracted_stories or "user_stories" not in self.agent.extracted_stories:
            return "❌ No user stories available."
        
        stories = self.agent.extracted_stories["user_stories"]
        if not stories:
            return "❌ No user stories in the list."
        
        output = f"📋 **Current User Stories ({len(stories)} total)**\n\n"
        for story in stories:
            story_id = story.get("id", "N/A")
            title = story.get("title", "Untitled")
            priority = story.get("priority", "Not set")
            confidence = story.get("confidence", "Not specified")
            output += f"🎯 {story_id}: {title}\n   Priority: {priority} | Confidence: {confidence}\n\n"
        
        return output
     
    @ai_function(name="get_story_details", description="Gets detailed information about a specific user story by ID")
    def get_story_details(
        self,
        story_id: Annotated[str, Field(description="The ID of the user story to retrieve (e.g., 'US-001')")]
    ) -> str:
        """Get detailed information about a specific story."""
        if not self.agent.extracted_stories or "user_stories" not in self.agent.extracted_stories:
            return "❌ Error: No user stories available."
        
        for story in self.agent.extracted_stories["user_stories"]:
            if story.get("id") == story_id:
                return f"📋 **User Story Details: {story_id}**\n\n{json.dumps(story, indent=2)}"
        
        available_ids = [s.get("id") for s in self.agent.extracted_stories["user_stories"]]
        return f"❌ Error: Story '{story_id}' not found. Available IDs: {', '.join(available_ids)}"
    
    @ai_function(name="clarification_decision", description="Agent declares whether clarification is complete and what should happen next")
    def clarification_decision(
        self,
        story_id: Annotated[str, Field(description="The ID of the user story being clarified (e.g., 'US-001')")],
        status: Annotated[str, Field(description="Decision status: 'needs_more_info', 'ready_to_update', or 'no_update_needed'")],
        summary: Annotated[str, Field(description="Brief summary of the clarification discussion and current understanding")],
        proposed_changes: Annotated[Optional[Dict], Field(description="Proposed changes to the user story if status is 'ready_to_update'. Should be a dict with fields to update.")] = None,
        follow_up_question: Annotated[Optional[str], Field(description="If status is 'needs_more_info', the specific follow-up question to ask the user")] = None
    ) -> Dict:
        """
        Agent declares whether clarification is complete and what should happen next.
        This is a decision checkpoint - it does not mutate the story.
        """
        return {
            "story_id": story_id,
            "status": status,
            "summary": summary,
            "proposed_changes": proposed_changes,
            "follow_up_question": follow_up_question
        }


class UserStoryExtractionAgent:
    """Agent that extracts and validates user stories from documents."""
    
    def __init__(self):
        """Initialize the agent with Azure OpenAI configuration."""
        # Initialize user story tools
        
        # Create Azure OpenAI chat client with appropriate authentication
        client = AzureOpenAIChatClient(
            endpoint=AZURE_OPENAI_ENDPOINT,
            deployment=AZURE_OPENAI_DEPLOYMENT,
            credential=AZURE_OPENAI_API_KEY
        )
        
        self.tools = UserStoryTools(self)

        # Create the agent with detailed instructions and tools
        self.agent = client.create_agent(
            name="UserStoryExtractor",
            instructions="""You are an expert Business Analyst specializing in extracting and structuring user stories from meeting transcripts and documents.
        
Your responsibilities:
1. Carefully read the provided document/transcript
2. Identify all potential user stories, features, and requirements
3. Extract each user story with:
   - A clear, concise title (max 100 characters)
   - A detailed description in "As a [role], I want [feature] so that [benefit]" format when possible
   - Acceptance criteria (specific, testable conditions)
   - Priority estimation (High/Medium/Low)
   - Any dependencies or technical notes mentioned

4. If information is unclear or missing:
   - Ask specific clarifying questions
   - Don't make assumptions
   - Flag incomplete items for user review

5. Structure your output as JSON with this schema:
{
  "user_stories": [
    {
      "id": "US-001",
      "title": "Short descriptive title",
      "description": "As a user, I want [feature] so that [benefit]",
      "acceptance_criteria": ["Criterion 1", "Criterion 2"],
      "priority": "High|Medium|Low",
      "notes": "Any additional context or dependencies",
      "confidence": "High|Medium|Low",
      "clarifications_needed": ["Question 1", "Question 2"]
    }
  ],
  "summary": "Brief summary of extracted stories",
  "questions": ["Overall questions about the document"]
}


CONVERSATION FLOW:
1. After extracting user stories, engage in conversation with the user
2. For clarification questions, use the clarification_decision tool to declare completion status
3. When user approves stories, use save_user_stories with approved=True
4. Always confirm actions before using tools
5. Be conversational and helpful

CRITICAL RULE:
- Return ONLY valid JSON matching the schema.
- If the user asks to change, update, delete, add, or save a user story,
  you MUST call the appropriate tool.
- You are NOT allowed to describe changes in text.
- You MUST perform the action via tool invocation.
- If required information is missing, ask a clarification question instead of responding in text.


IMPORTANT: 
- Be thorough but don't invent requirements
- Flag ambiguities and ask for clarification
- If confidence is Low, explain why
- Use tools to make changes when the user requests them
- Always show the user which tool you are using and what changed.
- Always show the user what changed after using a tool
""",
            tools=[
                self.tools.save_stories,
                self.tools.update_story,
                self.tools.remove_story,
                self.tools.add_story,
                self.tools.list_stories,
                self.tools.get_story_details,
                self.tools.clarification_decision
            ]
        )

        # Create a separate conversational agent without response_model for tool interactions
        self.conversational_agent = client.create_agent(
            name="UserStoryConversational",
            instructions="""You are a helpful assistant for managing user stories. When users ask to save, update, add, remove, or list user stories, you MUST use the appropriate tools. Do not respond with text descriptions - call the tools directly.

Commands you should recognize:
- "save" -> call save_user_stories tool
- "update [story_id]" -> call update_user_story tool  
- "add story" -> call add_user_story tool
- "remove [story_id]" -> call remove_user_story tool
- "list" -> call list_all_stories tool
- "show [story_id]" -> call get_story_details tool

Always call tools when users request these actions. Never describe what you would do - just do it by calling the tool.""",
            tools=[
                self.tools.save_stories,
                self.tools.update_story,
                self.tools.remove_story,
                self.tools.add_story,
                self.tools.list_stories,
                self.tools.get_story_details,
                self.tools.clarification_decision
            ]
        )

        self.conversation_history = []
        self.extracted_stories = None
        self.approved = False
        self.should_exit = False
    
    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self, title: str, subtitle: str = ""):
        """Print a clean header."""
        self.clear_screen()
        print(f"\n{'='*60}")
        print(f"🤖 {title}")
        if subtitle:
            print(f"   {subtitle}")
        print(f"{'='*60}\n")
    
    def read_document(self, file_path: str) -> str:
        """Read content from .txt or .docx file."""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_ext = path.suffix.lower()
        
        if file_ext == ".txt":
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        
        elif file_ext == ".docx":
            doc = Document(path)
            return "\n".join([para.text for para in doc.paragraphs])
        
        else:
            raise ValueError(f"Unsupported file type: {file_ext}. Use .txt or .docx")
    
    async def extract_user_stories(self, document_content: str, file_name: str = "document") -> dict:
        """
        Extract user stories from document using the agent.
        
        Args:
            document_content: The text content to analyze
            file_name: Name of the source document for reference
            
        Returns:
            dict: Parsed JSON response with extracted user stories
        """
        print(f"\n🤖 Agent analyzing '{file_name}'...")
        print(f"📄 Document length: {len(document_content)} characters\n")
        
        # Create the extraction prompt
        extraction_prompt = f"""Please analyze the following meeting transcript/document and extract all user stories following the JSON schema provided in your instructions.

Source Document: {file_name}

---DOCUMENT START---
{document_content}
---DOCUMENT END---

Extract all user stories, requirements, and features. For each one, provide:
- A unique ID (US-001, US-002, etc.)
- Clear title and description
- Acceptance criteria
- Priority
- Any clarification questions

Return ONLY valid JSON matching the schema. Be thorough.
"""

        # Call the agent
        try:
            result = await self.agent.run(extraction_prompt)

            if result is None:
                return {
                    "error": "Agent returned None - check agent configuration",
                    "raw_response": "No response from agent"
                }

            response_text = result.text

            # Use Pydantic's model_validate_json for direct parsing and validation
            extraction_response = ExtractionResponse.model_validate_json(response_text)
            validated_response = extraction_response.model_dump()
            self.extracted_stories = validated_response

            # Store in conversation history
            self.conversation_history.append({
                "role": "user",
                "content": extraction_prompt[:500] + "..." if len(extraction_prompt) > 500 else extraction_prompt
            })
            self.conversation_history.append({
                "role": "assistant",
                "content": json.dumps(validated_response, indent=2)
            })

            return validated_response
        
        except Exception as e:
            error_msg = f"Extraction failed: {str(e)}"
            return {
                "error": error_msg,
                "raw_response": str(e)
            }
       
    async def ask_clarification(self, question: str) -> str:
        """
        Ask the agent a clarification question.
        
        Args:
            question: The question to ask
            
        Returns:
            str: Agent's response
        """
        print(f"\n❓ User: {question}")
        result = await self.agent.run(question)
        response = result.text
        
        self.conversation_history.append({"role": "user", "content": question})
        self.conversation_history.append({"role": "assistant", "content": response})
        
        print(f"🤖 Agent: {response}\n")
        return response
       
    async def refine_story(self, story_id: str, refinement_request: str) -> dict:
        """
        Refine a specific user story based on user feedback.
        
        Args:
            story_id: ID of the story to refine (e.g., "US-001")
            refinement_request: Description of changes needed
            
        Returns:
            dict: Updated user story
        """
        refinement_prompt = f"""Based on our previous conversation, please refine user story {story_id}.

Refinement request: {refinement_request}

Return ONLY the updated user story in JSON format with the same schema."""

        result = await self.agent.run(refinement_prompt)
        response_text = result.text
        
        # Parse the refined story
        try:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                # Use Pydantic to validate the refined user story
                user_story = UserStory.model_validate_json(json_text)
                refined_story = user_story.model_dump()
                
                # Update in extracted_stories if available
                if self.extracted_stories and "user_stories" in self.extracted_stories:
                    for idx, story in enumerate(self.extracted_stories["user_stories"]):
                        if story.get("id") == story_id:
                            self.extracted_stories["user_stories"][idx] = refined_story
                            break
                
                return refined_story
            else:
                return {"error": "Could not parse refined story", "raw_response": response_text}
        except Exception as e:
            return {"error": f"Validation or parse error: {str(e)}", "raw_response": response_text}
    
    def display_stories(self, stories_data: dict):
        """
        Display extracted user stories in a clean, professional format.
        
        Args:
            stories_data: Dictionary containing user stories and metadata
        """
        if "error" in stories_data:
            print(f"\n❌ EXTRACTION ERROR")
            print(f"{'─'*50}")
            print(f"{stories_data['error']}")
            if "raw_response" in stories_data:
                print(f"\n📄 Raw Response (first 300 chars):")
                print(f"{stories_data['raw_response'][:300]}...")
            return
        
        user_stories = stories_data.get("user_stories", [])
        
        print(f"\n📋 USER STORIES ({len(user_stories)} total)")
        print(f"{'─'*50}")
        
        # Individual stories
        for idx, story in enumerate(user_stories, 1):
            story_id = story.get('id', 'N/A')
            title = story.get('title', 'Untitled')
            priority = story.get('priority', 'Medium')
            confidence = story.get('confidence', 'Medium')
            description = story.get('description', 'No description')
            
            # Priority and confidence indicators
            priority_icon = {'High': '🔴', 'Medium': '🟡', 'Low': '🟢'}.get(priority, '⚪')
            confidence_icon = {'High': '💯', 'Medium': '🎯', 'Low': '❓'}.get(confidence, '❔')
            
            print(f"\n{idx}. {story_id}: {title}")
            print(f"   {priority_icon} Priority: {priority} | {confidence_icon} Confidence: {confidence}")
            print(f"   📝 {description}")
            
            # Acceptance Criteria
            criteria = story.get('acceptance_criteria', [])
            if criteria:
                print(f"   ✅ Acceptance Criteria:")
                for ac_idx, criterion in enumerate(criteria, 1):
                    print(f"      {ac_idx}. {criterion}")
            
            # Notes
            notes = story.get('notes', '').strip()
            if notes:
                print(f"   📌 Notes: {notes}")
            
            # Clarifications needed
            clarifications = story.get('clarifications_needed', [])
            if clarifications:
                print(f"   ⚠️  Needs Clarification:")
                for clarification in clarifications:
                    print(f"      • {clarification}")
            
            print()  # Empty line between stories
        
        # Summary section
        summary = stories_data.get('summary', '').strip()
        if summary:
            print(f"📝 SUMMARY")
            print(f"{'─'*50}")
            print(f"{summary}\n")
        
        # Questions section
        questions = stories_data.get('questions', [])
        if questions:
            print(f"❓ OUTSTANDING QUESTIONS")
            print(f"{'─'*50}")
            for q_idx, question in enumerate(questions, 1):
                print(f"{q_idx}. {question}")
            print()
    
    def _format_badge(self, value: str, badge_type: str) -> str:
        """
        Format a badge for priority or confidence.
        
        Args:
            value: The value to display
            badge_type: Type of badge ('priority' or 'confidence')
            
        Returns:
            str: Formatted badge string
        """
        if badge_type == 'priority':
            emoji_map = {'High': '🔴', 'Medium': '🟡', 'Low': '🟢'}
            emoji = emoji_map.get(value, '⚪')
            return f"{emoji} Priority: {value}"
        elif badge_type == 'confidence':
            emoji_map = {'High': '💯', 'Medium': '🎯', 'Low': '❓'}
            emoji = emoji_map.get(value, '❔')
            return f"{emoji} Confidence: {value}"
        return value
    
    def _wrap_text(self, text: str, width: int) -> list:
        """
        Wrap text to specified width, preserving word boundaries.
        
        Args:
            text: Text to wrap
            width: Maximum width per line
            
        Returns:
            list: List of wrapped lines
        """
        if not text:
            return [""]
        
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            if len(current_line) + len(word) + 1 <= width:
                current_line += (word + " ")
            else:
                if current_line:
                    lines.append(current_line.rstrip())
                current_line = word + " "
        
        if current_line:
            lines.append(current_line.rstrip())
        
        return lines if lines else [""]
    
    def save_stories(self, file_name: str = None) -> Path:
        """
        Save extracted and approved user stories to JSON file.
        
        Args:
            file_name: Optional custom filename
            
        Returns:
            Path: Path to saved file
        """
        if not self.extracted_stories:
            raise ValueError("No user stories to save. Extract stories first.")
        
        if not self.approved:
            print("⚠️  Warning: Stories not yet approved by user")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = file_name or f"user_stories_{timestamp}.json"
        output_path = OUTPUT_DIR / file_name
        
        # Add metadata
        output_data = {
            "metadata": {
                "extracted_at": datetime.now().isoformat(),
                "approved": self.approved,
                "agent": "UserStoryExtractionAgent",
                "total_stories": len(self.extracted_stories.get("user_stories", []))
            },
            **self.extracted_stories
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ User stories saved to: {output_path}")
        return output_path


async def conversational_mode(file_path: str):
    """
    Conversational workflow where the agent uses tools to manage user stories.
    
    Args:
        file_path: Path to the document file (.txt or .docx)
    """
    try:
        # Initialize agent
        agent = UserStoryExtractionAgent()
        
        # Read document
        print(f"📖 Reading document: {file_path}")
        content = agent.read_document(file_path)
        
        # Extract user stories
        print(f"\n🤖 Analyzing document...")
        stories_data = await agent.extract_user_stories(content, Path(file_path).name)
        
        # Display extracted stories
        agent.display_stories(stories_data)
        
        # Check for errors
        if "error" in stories_data:
            print("\n❌ Extraction failed. Please review the error above.")
            return
        
        # Proactive clarification phase
        all_clarifications = []
        for story in stories_data.get("user_stories", []):
            story_id = story.get("id")
            clarifications = story.get("clarifications_needed", [])
            for clarification in clarifications:
                all_clarifications.append({
                    "story_id": story_id,
                    "question": clarification
                })

        if all_clarifications:
            print(f"❓ CLARIFICATION PHASE ({len(all_clarifications)} questions)")
            print(f"{'─'*50}")

            for idx, clarification in enumerate(all_clarifications, 1):
                story_id = clarification["story_id"]
                question = clarification["question"]

                print(f"\nQuestion {idx}/{len(all_clarifications)} for {story_id}:")
                print(f"🤖 {question}")

                # Get user response
                user_response = input("\n💬 You: ").strip()

                if not user_response:
                    print("⚠️  Please provide a response.")
                    continue

                if user_response.lower() in ['skip', 'pass', 'next']:
                    print("⏭️  Skipped")
                    continue

                # Send to agent for decision
                print(f"\n🤖 Processing...")
                clarification_prompt = f"""You are clarifying user story {story_id}.

Analyze the user's response and decide what to do.

RULES:
- If the response provides useful information, set status to 'ready_to_update' and propose changes.
- If more information is needed, set status to 'needs_more_info' and ask a follow-up question.
- If no changes are needed, set status to 'no_update_needed'.

ALWAYS call the clarification_decision tool with your decision.

Conversation:
Question: "{question}"
User response: "{user_response}"

Call clarification_decision now:"""

                # Get agent decision
                decision = None
                full_response = ""
                async for update in agent.conversational_agent.run_stream(clarification_prompt):
                    if update.text:
                        full_response += update.text
                    if hasattr(update, 'tool_call') and update.tool_call and update.tool_call.name == "clarification_decision":
                        decision = update.tool_call.arguments

                # Parse decision if not from tool call
                if not decision:
                    try:
                        parsed = json.loads(full_response.strip())
                        if isinstance(parsed, dict) and "status" in parsed:
                            decision = parsed
                    except:
                        pass

                if not decision:
                    print("❌ Agent failed to make decision, skipping...")
                    continue

                # Handle decision
                status = decision["status"]

                if status == "needs_more_info":
                    follow_up = decision.get("follow_up_question", "Can you provide more details?")
                    print(f"🤖 {follow_up}")
                    continue

                elif status == "ready_to_update":
                    print(f"✅ Ready to update {story_id}")
                    print(f"Summary: {decision.get('summary', '')}")

                    confirm = input("Apply changes? (y/n): ").strip().lower()
                    if confirm == "y":
                        changes = decision.get("proposed_changes", {})
                        if changes:
                            for field, value in changes.items():
                                update_prompt = f"Update {story_id} field '{field}' to: {value}"
                                await agent.agent.run(update_prompt)
                        print(f"✅ Updated {story_id}")
                    else:
                        print("❌ Skipped update")

                elif status == "no_update_needed":
                    print(f"✅ No update needed for {story_id}")
                    print(f"Summary: {decision.get('summary', '')}")

                else:
                    print(f"❌ Unknown status: {status}")

            # After all clarifications
            print(f"\n✅ All clarifications completed!")

            review = input("\n📋 Review updated stories? (y/n): ").strip().lower()
            if review == "y":
                agent.display_stories(agent.extracted_stories)
        
        # Start conversational loop
        print(f"\n💬 CONVERSATIONAL MODE")
        print(f"{'─'*50}")
        print(f"Commands: update, add, remove, list, save, exit")
        print(f"Type naturally or use commands.\n")
        
        # Initialize context
        context_prompt = f"""User stories in memory: {len(agent.extracted_stories.get('user_stories', []))} total.

Help the user refine these stories. Use tools when they request changes."""
        await agent.conversational_agent.run(context_prompt)
        
        while True:
            user_input = input("💬 You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("\n👋 Goodbye!")
                break
            
            # Send to conversational agent (which will use tools)
            print(f"🤖 ", end="")
            async for update in agent.conversational_agent.run_stream(user_input):
                if update.text:
                    print(update.text, end="")
                # Handle tool calls
                if hasattr(update, 'tool_call') and update.tool_call:
                    tool_name = update.tool_call.name
                    tool_args = update.tool_call.arguments
                    print(f"\n🔧 Calling tool: {tool_name}")
                    
                    # Execute the tool based on name
                    if tool_name == "save_user_stories":
                        approved = tool_args.get("approved", False)
                        filename = tool_args.get("filename")
                        result = agent.tools.save_stories(approved=approved, filename=filename)
                        print(f"📄 {result}")
                    elif tool_name == "update_user_story":
                        story_id = tool_args.get("story_id")
                        field = tool_args.get("field")
                        new_value = tool_args.get("new_value")
                        result = agent.tools.update_story(story_id=story_id, field=field, new_value=new_value)
                        print(f"✏️ {result}")
                    elif tool_name == "remove_user_story":
                        story_id = tool_args.get("story_id")
                        result = agent.tools.remove_story(story_id=story_id)
                        print(f"🗑️ {result}")
                    elif tool_name == "add_user_story":
                        title = tool_args.get("title")
                        description = tool_args.get("description")
                        priority = tool_args.get("priority", "Medium")
                        acceptance_criteria = tool_args.get("acceptance_criteria", "")
                        notes = tool_args.get("notes", "")
                        result = agent.tools.add_story(
                            title=title, description=description, priority=priority,
                            acceptance_criteria=acceptance_criteria, notes=notes
                        )
                        print(f"➕ {result}")
                    elif tool_name == "list_all_stories":
                        result = agent.tools.list_stories()
                        print(f"\n{result}")
                    elif tool_name == "get_story_details":
                        story_id = tool_args.get("story_id")
                        result = agent.tools.get_story_details(story_id=story_id)
                        print(f"\n{result}")
            print()
            
            # Check if agent signaled to exit (after approved save)
            if agent.should_exit:
                print("\n✨ Thank you for using the User Story Extraction Agent!")
                break
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


async def main():
    """Main entry point."""
    agent = UserStoryExtractionAgent()
    agent.print_header("USER STORY EXTRACTION AGENT", "Microsoft Agent Framework with Function Tools")
    
    # Get file path from user
    file_path = input("📂 Document path (.txt or .docx): ").strip()
    
    if not file_path:
        print("❌ No file path provided.")
        return
    
    # Remove quotes if user copied path with quotes
    file_path = file_path.strip('"').strip("'")
    
    # Start conversational mode
    await conversational_mode(file_path)


if __name__ == "__main__":
    asyncio.run(main())