"""
Main entry point for the Goal Setting Crew
Run this to start the interactive goal setting conversation
"""

import sys
import os
from dotenv import load_dotenv
from goal_setting_crew.crew import GoalSettingCrew

# Load environment variables
load_dotenv()


def save_goal_to_file(result):
    """Save the goal summary to a text file"""
    try:
        # Also save in a simple text format like the other implementations
        with open("output/corporate_goal.txt", "w", encoding="utf-8") as f:
            f.write("CORPORATE GOAL SUMMARY\n")
            f.write("=" * 50 + "\n\n")
            f.write(str(result))
        print("\n✅ Goal saved to output/corporate_goal.txt and output/goal_summary.md")
    except Exception as e:
        print(f"❌ Error saving additional file: {str(e)}")


def run():
    """
    Run the goal setting crew
    """
    # Check for API key
    if not os.getenv("AZURE_OPENAI_API_KEY"):
        print("⚠️  Please set your Azure OpenAI credentials in the .env file")
        return

    print("\n🎯 Corporate Goal Setting Assistant (CrewAI)")
    print("=" * 50)
    print("Welcome! Let's set up your corporate goal together.")
    print("The AI assistant will guide you through a series of questions.")
    print("Answer naturally and conversationally.\n")
    print("=" * 50 + "\n")

    try:
        # Initialize and run the crew
        goal_crew = GoalSettingCrew()
        
        print("🚀 Starting goal setting conversation...\n")
        
        # Run the crew - it will handle human interaction automatically
        result = goal_crew.crew().kickoff()
        
        print("\n" + "=" * 50)
        print("✅ Goal Setting Complete!")
        print("=" * 50)
        print("\n📋 Final Goal Summary:\n")
        print(result)
        
        # Save to additional file
        save_option = input("\n\n💾 Goal summary has been saved. Press Enter to finish...")
        save_goal_to_file(result)
        
        print("\n👋 Thank you for using the Goal Setting Assistant!")
        print("Your goals have been saved to the output folder.\n")

    except KeyboardInterrupt:
        print("\n\n👋 Goal setting cancelled. Come back anytime!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {}
    try:
        goal_crew = GoalSettingCrew()
        goal_crew.crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")


def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        goal_crew = GoalSettingCrew()
        goal_crew.crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")


def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {}
    try:
        goal_crew = GoalSettingCrew()
        goal_crew.crew().test(n_iterations=int(sys.argv[1]), openai_model_name=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")


if __name__ == "__main__":
    run()