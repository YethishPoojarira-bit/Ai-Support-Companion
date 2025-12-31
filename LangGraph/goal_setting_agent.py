"""
LangGraph-based Corporate Goal Setting Agent
The LLM intelligently guides conversation and extracts goal information.
"""

from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Azure OpenAI LLM
llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    temperature=0.7,
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY")
)


class GoalInformation(BaseModel):
    """Structured goal information extracted from conversation"""
    goal_type: str = Field(default="", description="Type of corporate goal (e.g., Revenue, Customer Satisfaction)")
    goal_description: str = Field(default="", description="Detailed description of what to achieve")
    timeline: str = Field(default="", description="When the goal should be achieved")
    key_metrics: list[str] = Field(default_factory=list, description="Metrics to measure success")


class GoalState(TypedDict):
    """State for the goal setting conversation"""
    messages: list
    goal_info: dict
    conversation_complete: bool


def conversation_node(state: GoalState) -> GoalState:
    """Main conversation node - handles interaction and extracts information"""
    
    # Build conversation history
    conversation_history = []
    for msg in state["messages"]:
        if msg["role"] == "assistant":
            conversation_history.append(AIMessage(content=msg["content"]))
        else:
            conversation_history.append(HumanMessage(content=msg["content"]))
    
    # System prompt for intelligent goal extraction
    system_prompt = f"""You are a corporate goal setting assistant. Your job is to:
1. Have a natural conversation with the user to understand their corporate goal
2. Extract and structure goal information from the conversation
3. Ask follow-up questions only when needed

Current goal information collected:
{json.dumps(state['goal_info'], indent=2)}

Based on the conversation, determine:
- What information is still missing (goal_type, goal_description, timeline, key_metrics)
- What question to ask next, OR if you have enough information to complete

If information is missing, ask ONE natural question to fill in the gaps.
If you have all the information needed, acknowledge completion.

Be conversational, not mechanical. Extract information intelligently from what the user says.
"""
    
    # If first message, greet the user
    if not state["messages"]:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content="Greet the user and ask them about their corporate goal in a natural way.")
        ])
        
        print("\n🎯 Corporate Goal Setting Assistant")
        print("=" * 50)
        print(f"\n🤖 Assistant: {response.content}")
        
        user_input = input("\n👤 You: ").strip()
        
        state["messages"].append({"role": "assistant", "content": response.content})
        state["messages"].append({"role": "user", "content": user_input})
        
        return state
    
    # Continue conversation with user's latest input
    conversation_history.insert(0, SystemMessage(content=system_prompt))
    response = llm.invoke(conversation_history)
    
    print(f"\n🤖 Assistant: {response.content}")
    
    # Check if conversation should continue
    user_input = input("\n👤 You: ").strip()
    
    state["messages"].append({"role": "assistant", "content": response.content})
    state["messages"].append({"role": "user", "content": user_input})
    
    return state


def extract_information_node(state: GoalState) -> GoalState:
    """Extract structured information from the conversation"""
    
    # Build full conversation context
    conversation_text = "\n".join([
        f"{msg['role']}: {msg['content']}" for msg in state["messages"]
    ])
    
    extraction_prompt = f"""Based on the following conversation, extract structured goal information.
Fill in as much as you can from what the user has said. Leave fields empty if not mentioned.

Conversation:
{conversation_text}

Extract and return JSON with these fields:
- goal_type: The type of goal (e.g., "Revenue Growth", "Customer Satisfaction")
- goal_description: Detailed description of what they want to achieve
- timeline: When they want to achieve it
- key_metrics: List of metrics to measure success (as array)

Return ONLY valid JSON, no other text.
"""
    
    response = llm.invoke([
        SystemMessage(content="You are a data extraction expert. Return only valid JSON."),
        HumanMessage(content=extraction_prompt)
    ])
    
    # Parse the response
    try:
        # Clean the response to extract JSON
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        extracted_info = json.loads(content)
        
        # Update state with extracted information
        state["goal_info"]["goal_type"] = extracted_info.get("goal_type", state["goal_info"].get("goal_type", ""))
        state["goal_info"]["goal_description"] = extracted_info.get("goal_description", state["goal_info"].get("goal_description", ""))
        state["goal_info"]["timeline"] = extracted_info.get("timeline", state["goal_info"].get("timeline", ""))
        
        # Handle metrics - ensure it's a list
        metrics = extracted_info.get("key_metrics", state["goal_info"].get("key_metrics", []))
        if isinstance(metrics, str):
            metrics = [m.strip() for m in metrics.split(",") if m.strip()]
        state["goal_info"]["key_metrics"] = metrics
        
    except Exception as e:
        print(f"\n[Debug] Extraction error: {e}")
        # Keep existing information if extraction fails
        pass
    
    return state


def decide_next_step(state: GoalState) -> Literal["conversation", "summary", "end"]:
    """LLM decides what to do next based on conversation and collected information"""
    
    goal_info = state["goal_info"]
    
    # Check if we have all required information
    has_goal_type = bool(goal_info.get("goal_type", "").strip())
    has_description = bool(goal_info.get("goal_description", "").strip())
    has_timeline = bool(goal_info.get("timeline", "").strip())
    has_metrics = bool(goal_info.get("key_metrics", []))
    
    # Build context for decision
    decision_prompt = f"""Based on the conversation and collected information, decide the next action.

Collected Information:
- Goal Type: {'✓' if has_goal_type else '✗'} {goal_info.get('goal_type', 'Missing')}
- Description: {'✓' if has_description else '✗'} {goal_info.get('goal_description', 'Missing')}
- Timeline: {'✓' if has_timeline else '✗'} {goal_info.get('timeline', 'Missing')}
- Metrics: {'✓' if has_metrics else '✗'} {goal_info.get('key_metrics', [])}

Recent conversation:
{state['messages'][-2:] if len(state['messages']) >= 2 else state['messages']}

Decide the next action:
- "conversation" - if any critical information is missing, continue asking
- "summary" - if all key information is collected, provide summary
- "end" - if user wants to end

Return ONLY ONE WORD: conversation, summary, or end
"""
    
    response = llm.invoke([
        SystemMessage(content="You are a decision-making assistant. Return only one word."),
        HumanMessage(content=decision_prompt)
    ])
    
    decision = response.content.strip().lower()
    
    # Check for completion indicators
    if all([has_goal_type, has_description, has_timeline, has_metrics]):
        return "summary"
    
    # Parse LLM decision
    if "end" in decision or "finish" in decision or "complete" in decision:
        if all([has_goal_type, has_description]):  # Minimum requirements
            return "summary"
        else:
            return "conversation"
    elif "summary" in decision:
        return "summary"
    else:
        return "conversation"


def summary_node(state: GoalState) -> GoalState:
    """Provide final summary and action steps"""
    
    goal_info = state["goal_info"]
    
    summary_prompt = f"""Based on the collected goal information, provide a professional summary 
and 3-5 concrete action steps to get started.

Goal Information:
- Type: {goal_info.get('goal_type', 'Not specified')}
- Description: {goal_info.get('goal_description', 'Not specified')}
- Timeline: {goal_info.get('timeline', 'Not specified')}
- Key Metrics: {', '.join(goal_info.get('key_metrics', [])) if goal_info.get('key_metrics') else 'Not specified'}

Format your response in a clear, structured way with:
1. A brief summary of the goal
2. Numbered action steps
3. Encouragement

Be professional and actionable.
"""
    
    response = llm.invoke([
        SystemMessage(content="You are a professional goal setting advisor."),
        HumanMessage(content=summary_prompt)
    ])
    
    print(f"\n🤖 Assistant:\n{response.content}")
    print("\n" + "=" * 50)
    print("✅ Goal setting complete!")
    
    state["messages"].append({"role": "assistant", "content": response.content})
    state["conversation_complete"] = True
    
    return state


# Build the graph
def create_goal_setting_workflow():
    """Create the LangGraph workflow for goal setting"""
    
    workflow = StateGraph(GoalState)
    
    # Add nodes
    workflow.add_node("conversation", conversation_node)
    workflow.add_node("extract", extract_information_node)
    workflow.add_node("summary", summary_node)
    
    # Set entry point
    workflow.set_entry_point("conversation")
    
    # Add edges - conversation always goes to extract, then extract decides next
    workflow.add_edge("conversation", "extract")
    
    workflow.add_conditional_edges(
        "extract",
        decide_next_step,
        {
            "conversation": "conversation",
            "summary": "summary",
            "end": END
        }
    )
    
    workflow.add_edge("summary", END)
    
    return workflow.compile()


def main():
    """Main function to run the goal setting agent"""
    
    # Check for API key
    if not os.getenv("AZURE_OPENAI_API_KEY"):
        print("⚠️  Please set your Azure OpenAI credentials in the .env file")
        return
    
    # Initialize state
    initial_state = {
        "messages": [],
        "goal_info": {
            "goal_type": "",
            "goal_description": "",
            "timeline": "",
            "key_metrics": []
        },
        "conversation_complete": False
    }
    
    # Create and run the workflow
    app = create_goal_setting_workflow()
    
    try:
        final_state = app.invoke(initial_state)
        
        # Save the goal to a file
        save_option = input("\n\n💾 Would you like to save this goal to a file? (y/n): ").strip().lower()
        if save_option == 'y':
            goal_info = final_state['goal_info']
            with open("corporate_goal.txt", "w", encoding="utf-8") as f:
                f.write("CORPORATE GOAL SUMMARY\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Goal Type: {goal_info.get('goal_type', 'Not specified')}\n")
                f.write(f"Description: {goal_info.get('goal_description', 'Not specified')}\n")
                f.write(f"Timeline: {goal_info.get('timeline', 'Not specified')}\n")
                metrics = goal_info.get('key_metrics', [])
                f.write(f"Key Metrics: {', '.join(metrics) if metrics else 'Not specified'}\n")
            print("✅ Goal saved to corporate_goal.txt")
    
    except KeyboardInterrupt:
        print("\n\n👋 Goal setting cancelled. Come back anytime!")
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()