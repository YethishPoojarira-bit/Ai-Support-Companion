"""
Semantic Kernel-based Corporate Goal Setting Agent
The agent uses SK plugins and planners to guide goal setting conversation.
"""

import asyncio
import os
import json
from dotenv import load_dotenv
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.functions import kernel_function

# Load environment variables
load_dotenv()

class GoalSettingPlugin:
    """Plugin for managing goal setting state and operations"""
    
    def __init__(self):
        self.goal_info = {
            "goal_type": "",
            "goal_description": "",
            "timeline": "",
            "key_metrics": []
        }
    
    @kernel_function( name="update_goal_type", description="Updates the type of corporate goal being set")
    def update_goal_type(self, goal_type: str) -> str:
        """Update the goal type"""
        self.goal_info["goal_type"] = goal_type
        return f"Goal type updated to: {goal_type}"
    
    @kernel_function(name="update_goal_description", description="Updates the detailed description of what the user wants to achieve with this goal")
    def update_goal_description(self, description: str) -> str:
        """Update the goal description"""
        self.goal_info["goal_description"] = description
        return f"Goal description updated"
    
    @kernel_function(name="update_timeline", description="Updates when the goal should be achieved (e.g., Q1 2026, 6 months, end of year)")
    def update_timeline(self, timeline: str) -> str:
        """Update the timeline"""
        self.goal_info["timeline"] = timeline
        return f"Timeline updated to: {timeline}"
    
    @kernel_function(name="add_metric", description="Adds a key metric to measure goal success")
    def add_metric(self, metric: str) -> str:
        """Add a key metric"""
        if metric not in self.goal_info["key_metrics"]:
            self.goal_info["key_metrics"].append(metric)
            return f"Added metric: {metric}"
        return f"Metric already exists: {metric}"
    
    @kernel_function(name="get_goal_status", description="Returns the current status of collected goal information")
    def get_goal_status(self) -> str:
        """Get current goal information status"""
        status = []
        status.append(f"Goal Type: {self.goal_info['goal_type'] or 'Not set'}")
        status.append(f"Description: {self.goal_info['goal_description'] or 'Not set'}")
        status.append(f"Timeline: {self.goal_info['timeline'] or 'Not set'}")
        status.append(f"Metrics: {', '.join(self.goal_info['key_metrics']) if self.goal_info['key_metrics'] else 'Not set'}")
        return "\n".join(status)
    
    @kernel_function(name="check_completeness", description="Checks if all required goal information has been collected")
    def check_completeness(self) -> str:
        """Check if goal information is complete"""
        missing = []
        if not self.goal_info["goal_type"]:
            missing.append("goal type")
        if not self.goal_info["goal_description"]:
            missing.append("description")
        if not self.goal_info["timeline"]:
            missing.append("timeline")
        if not self.goal_info["key_metrics"]:
            missing.append("metrics")
        
        if missing:
            return f"Missing: {', '.join(missing)}"
        return "complete"


class GoalSettingAgent:
    """Main agent for goal setting using Semantic Kernel"""
    
    def __init__(self):
        self.kernel = Kernel()
        self.plugin = GoalSettingPlugin()
        self.chat_history = ChatHistory()
        
        # Add Azure OpenAI chat completion service
        self.kernel.add_service(
            AzureChatCompletion(
                service_id="chat",
                deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
                endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION")
            )   
        )
        
        # Add the goal setting plugin
        self.kernel.add_plugin(self.plugin, plugin_name="goal_setting")
        
        # System message for the agent
        self.system_message = """You are a helpful corporate goal setting assistant.

Your job is to:
1. Have a natural conversation with the user about their corporate goal
2. Extract information from their responses and use the available functions to store it:
   - update_goal_type: Store the type of goal (Revenue, Customer Satisfaction, etc.)
   - update_goal_description: Store detailed description of what they want to achieve
   - update_timeline: Store when they want to achieve it
   - add_metric: Store each metric they mention to measure success
   - check_completeness: Check if all required information is collected

3. Use get_goal_status to see what information you already have
4. Ask natural follow-up questions for missing information
5. When all information is collected (check_completeness returns "complete"), provide a summary with action steps

Be conversational and intelligent. Extract information from what users say and call the appropriate functions.
Don't ask for the same information twice - use get_goal_status to see what you have.
"""
        self.chat_history.add_system_message(self.system_message)
    

    async def chat(self, user_input: str) -> str:
        """Process user input and get agent response"""
        
        # Add user message to history
        self.chat_history.add_user_message(user_input)
        
        # Get chat completion service
        chat_completion = self.kernel.get_service(service_id="chat")
        
        # Configure function calling
        execution_settings = chat_completion.get_prompt_execution_settings_class()(
            service_id="chat",
            temperature=0.7,
            max_tokens=1000,
            function_choice_behavior=FunctionChoiceBehavior.Auto()
        )
        
        # Get response with function calling
        response = await chat_completion.get_chat_message_contents(
            chat_history=self.chat_history,
            settings=execution_settings,
            kernel=self.kernel
        )
        
        # Extract the response
        if response:
            assistant_message = str(response[0])
            self.chat_history.add_assistant_message(assistant_message)
            return assistant_message
        
        return "I apologize, I couldn't process that. Could you try again?"
    

    async def run(self):
        """Main conversation loop"""
        
        print("\n🎯 Corporate Goal Setting Assistant (Semantic Kernel)")
        print("=" * 50)
        print("Let's set up your corporate goal! Type 'quit' to exit.\n")
        
        # Start conversation
        greeting = await self.chat("Greet the user and ask about their corporate goal.")
        print(f"🤖 Assistant: {greeting}\n")
        
        conversation_active = True
        
        while conversation_active:
            try:
                user_input = input("👤 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("\n👋 Thank you for using the Goal Setting Assistant!")
                    break
                
                if not user_input:
                    continue
                
                # Get response
                response = await self.chat(user_input)
                print(f"\n🤖 Assistant: {response}\n")
                
                # Check if goal is complete
                completeness = self.plugin.check_completeness()
                if completeness == "complete":
                    # Ask for final summary
                    summary_prompt = "All information collected. Provide a professional summary and 3-5 action steps."
                    summary = await self.chat(summary_prompt)
                    print(f"\n🤖 Assistant: {summary}\n")
                    print("=" * 50)
                    print("✅ Goal setting complete!\n")
                    
                    # Offer to save
                    save = input("💾 Would you like to save this goal to a file? (y/n): ").strip().lower()
                    if save == 'y':
                        self.save_goal()
                    
                    conversation_active = False
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goal setting cancelled. Come back anytime!")
                break
            except Exception as e:
                print(f"\n❌ An error occurred: {str(e)}")
                import traceback
                traceback.print_exc()
                break
    
    def save_goal(self):
        """Save goal to file"""
        try:
            with open("corporate_goal.txt", "w", encoding="utf-8") as f:
                f.write("CORPORATE GOAL SUMMARY\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Goal Type: {self.plugin.goal_info.get('goal_type', 'Not specified')}\n")
                f.write(f"Description: {self.plugin.goal_info.get('goal_description', 'Not specified')}\n")
                f.write(f"Timeline: {self.plugin.goal_info.get('timeline', 'Not specified')}\n")
                metrics = self.plugin.goal_info.get('key_metrics', [])
                f.write(f"Key Metrics: {', '.join(metrics) if metrics else 'Not specified'}\n")
            print("✅ Goal saved to corporate_goal.txt")
        except Exception as e:
            print(f"❌ Error saving file: {str(e)}")


async def main():
    # Create and run agent
    agent = GoalSettingAgent()
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())