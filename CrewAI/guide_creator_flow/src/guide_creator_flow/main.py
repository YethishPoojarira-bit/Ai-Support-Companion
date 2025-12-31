#!/usr/bin/env python
import json
import os
import logging

# Monkey patch logging to suppress LiteLLM warnings
original_log = logging.Logger._log

def patched_log(self, level, msg, args, exc_info=None, extra=None, stack_info=False):
    # Suppress LiteLLM proxy-related warnings and errors
    msg_str = str(msg)
    if ('apscheduler' in msg_str or
        'proxy_server' in msg_str or
        'Missing dependency' in msg_str or
        'atexit after shutdown' in msg_str or
        'Error creating standard logging object' in msg_str):
        return
    return original_log(self, level, msg, args, exc_info, extra, stack_info)

logging.Logger._log = patched_log

from typing import List, Dict
from pydantic import BaseModel, Field
from crewai import LLM
from crewai.flow.flow import Flow, listen, start
from guide_creator_flow.crews.content_crew.content_crew import ContentCrew, azure_llm
import os

# Define our models for structured data
class Section(BaseModel):
    title: str = Field(description="Title of the section")
    description: str = Field(description="Brief description of what the section should cover")

class GuideOutline(BaseModel):
    title: str = Field(description="Title of the guide")
    introduction: str = Field(description="Introduction to the topic")
    target_audience: str = Field(description="Description of the target audience")
    sections: List[Section] = Field(description="List of sections in the guide")
    conclusion: str = Field(description="Conclusion or summary of the guide")

# Define our flow state
class GuideCreatorState(BaseModel):
    topic: str = ""
    audience_level: str = ""
    guide_outline: GuideOutline = None
    sections_content: Dict[str, str] = {}

class GuideCreatorFlow(Flow[GuideCreatorState]):
    """Flow for creating a comprehensive guide on any topic"""

    @start()
    def get_user_input(self):
        """Get input from the user about the guide topic and audience"""
        print("\n=== Create Your Comprehensive Guide ===\n")

        # Get user input
        self.state.topic = input("What topic would you like to create a guide for? ")

        # Get audience level with validation
        while True:
            audience = input("Who is your target audience? (beginner/intermediate/advanced) ").lower()
            if audience in ["beginner", "intermediate", "advanced"]:
                self.state.audience_level = audience
                break
            print("Please enter 'beginner', 'intermediate', or 'advanced'")

        print(f"\nCreating a guide on {self.state.topic} for {self.state.audience_level} audience...\n")
        return self.state

    @listen(get_user_input)
    def create_guide_outline(self, state):
        """Create a structured outline for the guide using a direct LLM call"""
        print("Creating guide outline...")

        # Initialize the LLM
        azure_llm = LLM(
            model="azure/gpt-4o-mini",
            api_key= os.getenv("AZURE_OPENAI_API_KEY"),
            api_base= os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            is_litellm=True
        )

        # Create the messages for the outline
        messages = [
            {"role": "system", "content": "You are a helpful assistant that creates structured outlines for educational guides. Always respond with valid JSON only, no markdown formatting."},
            {"role": "user", "content": f"""
Create a detailed outline for a comprehensive guide on "{state.topic}" for {state.audience_level} level learners.

Respond with a JSON object in this exact format:
{{
  "title": "Guide title as string",
  "introduction": "Introduction text as string",
  "target_audience": "Description of target audience as string",
  "sections": [
    {{"title": "Section 1 title", "description": "Section 1 description"}},
    {{"title": "Section 2 title", "description": "Section 2 description"}}
  ],
  "conclusion": "Conclusion text as string"
}}

The outline should include:
- A compelling title
- An introduction paragraph
- Target audience description
- 4-6 main sections with title and max of 100 words description each
- A conclusion paragraph of max 100 words
"""}
        ]

        # Make the LLM call with JSON response format
        response = azure_llm.call(messages=messages)

        # Parse the JSON response
        outline_dict = json.loads(response)
        self.state.guide_outline = GuideOutline(**outline_dict)

        # Ensure output directory exists before saving
        os.makedirs("output", exist_ok=True)

        # Save the outline to a file
        with open("output/guide_outline.json", "w") as f:
            json.dump(outline_dict, f, indent=2)

        print(f"Guide outline created with {len(self.state.guide_outline.sections)} sections")
        return self.state.guide_outline

    @listen(create_guide_outline)
    def write_and_compile_guide(self, outline):
        """Write all sections and compile the guide"""
        print("Writing guide sections and compiling...")
        completed_sections = []

        # Process sections one by one to maintain context flow
        for section in outline.sections:
            print(f"Processing section: {section.title}")

            # Build context from previous sections
            previous_sections_text = ""
            if completed_sections:
                previous_sections_text = "# Previously Written Sections\n\n"
                for title in completed_sections:
                    previous_sections_text += f"## {title}\n\n"
                    previous_sections_text += self.state.sections_content.get(title, "") + "\n\n"
            else:
                previous_sections_text = "No previous sections written yet."

            # Run the content crew for this section
            result = ContentCrew().crew().kickoff(inputs={
                "section_title": section.title,
                "section_description": section.description,
                "audience_level": self.state.audience_level,
                "previous_sections": previous_sections_text,
                "draft_content": ""
            })

            # Store the content
            self.state.sections_content[section.title] = result.raw
            completed_sections.append(section.title)
            print(f"Section completed: {section.title}")

        # Compile the final guide
        guide_content = f"# {outline.title}\n\n"
        guide_content += f"## Introduction\n\n{outline.introduction}\n\n"

        # Add each section in order
        for section in outline.sections:
            section_content = self.state.sections_content.get(section.title, "")
            guide_content += f"\n\n{section_content}\n\n"

        # Add conclusion
        guide_content += f"## Conclusion\n\n{outline.conclusion}\n\n"

        # Save the guide
        with open("output/complete_guide.md", "w") as f:
            f.write(guide_content)

        print("\nComplete guide compiled and saved to output/complete_guide.md")
        return "Guide creation completed successfully"

def kickoff():
    """Run the guide creator flow"""
    GuideCreatorFlow().kickoff()
    print("\n=== Flow Complete ===")
    print("Your comprehensive guide is ready in the output directory.")
    print("Open output/complete_guide.md to view it.")

def plot():
    """Generate a visualization of the flow"""
    flow = GuideCreatorFlow()
    flow.plot("guide_creator_flow")
    print("Flow visualization saved to guide_creator_flow.html")

if __name__ == "__main__":
    kickoff()
    # plot()