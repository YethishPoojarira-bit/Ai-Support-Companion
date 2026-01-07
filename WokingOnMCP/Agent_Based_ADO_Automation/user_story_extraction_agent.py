"""
User Story Extraction Agent using Microsoft Agent Framework
Extracts user stories from meeting transcripts with human-in-the-loop verification.
"""
import asyncio
import os
import json
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
    summary: str
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
        return f"{approval_status} - User stories saved to: {output_path}\n\nTotal stories: {len(self.agent.extracted_stories.get('user_stories', []))}"
    
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
            response_model=ExtractionResponse,
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

AVAILABLE TOOLS:
You have access to the following tools to help manage user stories during conversation:
- save_user_stories: Save the current stories to a JSON file (use when user approves or requests to save)
- update_user_story: Update specific fields of a user story (use when user requests changes)
- remove_user_story: Remove a user story from the list (use when user wants to delete a story)
- add_user_story: Add a new user story to the list (use when user provides new requirements)
- list_all_stories: Show all current user stories with IDs and titles
- get_story_details: Get detailed information about a specific user story

CONVERSATION FLOW:
1. After extracting user stories, engage in conversation with the user
2. Ask clarifying questions about unclear requirements
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
- Return ONLY valid JSON matching the schema.
- Be thorough but don't invent requirements
- Flag ambiguities and ask for clarification
- Maintain traceability to source text
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
                self.tools.get_story_details
            ]
        )

        self.conversation_history = []
        self.extracted_stories = None
        self.approved = False
    
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
        Display extracted user stories in a beautiful, consistent format.
        
        Args:
            stories_data: Dictionary containing user stories and metadata
        """
        if "error" in stories_data:
            print(f"\n{'='*80}")
            print(f"❌ EXTRACTION ERROR")
            print(f"{'='*80}")
            print(f"\n{stories_data['error']}\n")
            if "raw_response" in stories_data:
                print(f"Raw response (first 500 chars):")
                print(f"{'-'*80}")
                print(f"{stories_data['raw_response'][:500]}...")
                print(f"{'-'*80}\n")
            return
        
        user_stories = stories_data.get("user_stories", [])
        
        # Header
        print(f"\n{'='*80}")
        print(f"📋 EXTRACTED USER STORIES")
        print(f"{'='*80}")
        print(f"Total Stories: {len(user_stories)}")
        print(f"{'='*80}\n")
        
        # Individual stories
        for idx, story in enumerate(user_stories, 1):
            story_id = story.get('id', 'N/A')
            title = story.get('title', 'Untitled')
            priority = story.get('priority', 'Not set')
            confidence = story.get('confidence', 'Not specified')
            description = story.get('description', 'No description provided')
            
            # Story header with ID and title
            print(f"┌{'─'*78}┐")
            print(f"│ {idx}. {story_id}: {title[:60]}{' '*(60-len(title[:60]))} │")
            print(f"├{'─'*78}┤")
            
            # Priority and confidence badges
            priority_badge = self._format_badge(priority, 'priority')
            confidence_badge = self._format_badge(confidence, 'confidence')
            print(f"│ {priority_badge}  {confidence_badge}{' '*(78-len(priority_badge)-len(confidence_badge)-3)}│")
            print(f"├{'─'*78}┤")
            
            # Description
            print(f"│ 📝 DESCRIPTION:{' '*63}│")
            desc_lines = self._wrap_text(description, 74)
            for line in desc_lines:
                print(f"│ {line}{' '*(76-len(line))}│")
            
            # Acceptance Criteria
            criteria = story.get('acceptance_criteria', [])
            if criteria:
                print(f"├{'─'*78}┤")
                print(f"│ ✅ ACCEPTANCE CRITERIA:{' '*54}│")
                for ac_idx, criterion in enumerate(criteria, 1):
                    criterion_text = f"{ac_idx}. {criterion}"
                    criterion_lines = self._wrap_text(criterion_text, 74)
                    for line in criterion_lines:
                        print(f"│ {line}{' '*(76-len(line))}│")
            
            # Notes
            notes = story.get('notes', '').strip()
            if notes:
                print(f"├{'─'*78}┤")
                print(f"│ 📌 NOTES:{' '*66}│")
                notes_lines = self._wrap_text(notes, 74)
                for line in notes_lines:
                    print(f"│ {line}{' '*(76-len(line))}│")
            
            # Clarifications needed
            clarifications = story.get('clarifications_needed', [])
            if clarifications:
                print(f"├{'─'*78}┤")
                print(f"│ ⚠️  CLARIFICATIONS NEEDED:{' '*52}│")
                for clarification in clarifications:
                    clarif_lines = self._wrap_text(f"• {clarification}", 74)
                    for line in clarif_lines:
                        print(f"│ {line}{' '*(76-len(line))}│")
            
            print(f"└{'─'*78}┘\n")
        
        # Summary section
        summary = stories_data.get('summary', '').strip()
        if summary:
            print(f"{'─'*80}")
            print(f"📝 OVERALL SUMMARY")
            print(f"{'─'*80}")
            summary_lines = self._wrap_text(summary, 78)
            for line in summary_lines:
                print(line)
            print(f"{'─'*80}\n")
        
        # Questions section
        questions = stories_data.get('questions', [])
        if questions:
            print(f"{'─'*80}")
            print(f"❓ OUTSTANDING QUESTIONS")
            print(f"{'─'*80}")
            for q_idx, question in enumerate(questions, 1):
                print(f"{q_idx}. {question}")
            print(f"{'─'*80}\n")
        
        # Footer
        print(f"{'='*80}")
        print(f"✨ End of User Stories Report")
        print(f"{'='*80}\n")
    

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
        stories_data = await agent.extract_user_stories(content, Path(file_path).name)
        
        # Display extracted stories
        agent.display_stories(stories_data)
        
        # Check for errors
        if "error" in stories_data:
            print("\n❌ Extraction failed. Please review the raw response above.")
            return
        
        # Proactive clarification phase - traverse through all clarifications_needed
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
            print("\n" + "="*80)
            print("❓ CLARIFICATION PHASE - Agent needs your input on specific user stories")
            print("="*80)
            print(f"\nI have {len(all_clarifications)} clarification question(s) to help refine the user stories.")
            print("Let me ask them one by one...\n")

            for idx, clarification in enumerate(all_clarifications, 1):
                story_id = clarification["story_id"]
                question = clarification["question"]

                print(f"\n{'─'*80}")
                print(f"Question {idx}/{len(all_clarifications)} for {story_id}:")
                print(f"🤖 Agent: {question}")
                print(f"{'─'*80}")

                # Human-in-the-loop conversation for this specific question
                conversation_complete = False
                while not conversation_complete:
                    user_response = input("\n💬 You: ").strip()

                    if not user_response:
                        print("⚠️  Please provide a response to continue.")
                        continue

                    if user_response.lower() in ['skip', 'pass', 'next']:
                        print("⏭️  Skipping this clarification...")
                        break

                    # Send the user's response to the agent for conversational processing
                    clarification_prompt = f"""Regarding user story {story_id}, I asked: "{question}"

The user responded: "{user_response}"

Please engage in natural conversation about this clarification. You can:
- Ask follow-up questions if you need more information
- Discuss the implications of their response
- Suggest how this affects the user story
- Ask for confirmation before making changes

Do NOT automatically update the user story. Have a conversation first and only use tools when the user explicitly asks you to make changes or when you have enough information to proceed.

Keep your response conversational and helpful."""

                    print("\n🤖 Agent: ", end="", flush=True)
                    agent_response = ""
                    async for update in agent.agent.run_stream(clarification_prompt):
                        if update.text:
                            print(update.text, end="", flush=True)
                            agent_response += update.text
                    print()

                    # Check if the agent seems satisfied or needs more info
                    response_lower = agent_response.lower()
                    if any(phrase in response_lower for phrase in [
                        "thank you", "got it", "understood", "that clarifies",
                        "i think that's sufficient", "clear now", "that helps"
                    ]):
                        # Agent seems satisfied, ask if they want to update the story
                        update_choice = input(f"\n🤖 Should I update user story {story_id} based on this clarification? (yes/no): ").strip().lower()
                        if update_choice in ['yes', 'y']:
                            # Now use the tool to update
                            update_prompt = f"""Based on the clarification conversation above for user story {story_id}, please update the user story with the new information. Use the update_user_story tool to make the appropriate changes."""
                            print("\n🤖 Updating user story...")
                            async for update in agent.agent.run_stream(update_prompt):
                                if update.text:
                                    print(update.text, end="", flush=True)
                            print()
                        conversation_complete = True
                    elif any(phrase in response_lower for phrase in [
                        "could you", "can you", "what about", "tell me",
                        "please clarify", "need more", "additional info"
                    ]):
                        # Agent is asking another question, continue conversation
                        print(f"\n🔄 Continuing conversation for {story_id}...")
                    else:
                        # Ask user if they want to continue or complete this clarification
                        continue_choice = input(f"\n🤖 Continue conversation for {story_id}, or complete this clarification? (continue/complete): ").strip().lower()
                        if continue_choice not in ['continue', 'c']:
                            conversation_complete = True

            # After all clarifications are addressed, offer to review updated stories
            print("\n" + "="*80)
            print("✅ All clarification questions addressed!")
            print("="*80)

            review_choice = input("\n📋 Would you like to review the updated user stories? (yes/no): ").strip().lower()
            if review_choice in ['yes', 'y']:
                print("\n🔄 Displaying updated user stories...\n")
                agent.display_stories(agent.extracted_stories)
        
        # Start conversational loop
        print("\n" + "="*80)
        print("💬 CONVERSATIONAL MODE - Chat with the agent to refine your user stories")
        print("="*80)
        print("\nThe agent can now:")
        print("  • Answer clarification questions")
        print("  • Update user stories based on your feedback")
        print("  • Add new user stories as you discuss requirements")
        print("  • Remove stories that aren't needed")
        print("  • Save the final user stories when you approve them")
        print("\nJust chat naturally! Type 'exit' or 'quit' to end the conversation.\n")
        
        # Initialize conversational context with extracted stories
        context_prompt = f"""I have extracted the following user stories from the document. These are now in my memory and I can help you refine them:

{json.dumps(agent.extracted_stories, indent=2)}

I'm ready to help you refine these user stories. You can ask me questions, request updates, or discuss any aspects of the requirements. What would you like to do?"""
        
        # Send context to agent (silently, to establish context)
        await agent.agent.run(context_prompt)
        
        while True:
            user_input = input("\n💬 You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("\n👋 Ending conversation. Goodbye!")
                break
            
            # Send message to agent (agent will use tools as needed)
            print("\n🤖 Agent: ", end="", flush=True)
            async for update in agent.agent.run_stream(user_input):
                if update.text:
                    print(update.text, end="", flush=True)
            print()  # New line after streaming is complete
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


async def main():
    """Main entry point."""
    print("\n" + "="*80)
    print("🤖 USER STORY EXTRACTION AGENT")
    print("   Microsoft Agent Framework with Function Tools")
    print("="*80)
    
    # Get file path from user
    file_path = input("\n📂 Enter path to document (.txt or .docx): ").strip()
    
    if not file_path:
        print("❌ No file path provided. Exiting.")
        return
    
    # Remove quotes if user copied path with quotes
    file_path = file_path.strip('"').strip("'")
    
    # Start conversational mode directly
    await conversational_mode(file_path)


if __name__ == "__main__":
    asyncio.run(main())