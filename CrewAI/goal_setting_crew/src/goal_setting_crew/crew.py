"""
Goal Setting Crew - Human Interactive Goal Setting System
Uses CrewAI to guide users through setting corporate goals with natural conversation.
"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
# from langchain_openai import AzureChatOpenAI
from crewai.llm import LLM
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@CrewBase
class GoalSettingCrew():
    """Goal Setting Crew for interactive goal setting"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self):
        """Initialize the crew with Azure OpenAI"""
        # Initialize Azure OpenAI LLM
        self.llm =  LLM(
            model="azure/gpt-4o-mini",  # azure/<deployment-name>
            temperature=0.2,
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            base_url=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version="2024-12-01-preview",
            is_litellm=True  # Force using LiteLLM
        )

    @agent
    def goal_analyst(self) -> Agent:
        """Create the goal analyst agent"""
        return Agent(
            config=self.agents_config['goal_analyst'],
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

    @agent
    def goal_summarizer(self) -> Agent:
        """Create the goal summarizer agent"""
        return Agent(
            config=self.agents_config['goal_summarizer'],
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

    @task
    def gather_goal_type(self) -> Task:
        """Task to gather goal type through human interaction"""
        return Task(
            config=self.tasks_config['gather_goal_type'],
            agent=self.goal_analyst(),
            human_input=True  # This enables human interaction
        )

    @task
    def gather_goal_description(self) -> Task:
        """Task to gather goal description through human interaction"""
        return Task(
            config=self.tasks_config['gather_goal_description'],
            agent=self.goal_analyst(),
            human_input=True
        )

    @task
    def gather_timeline(self) -> Task:
        """Task to gather timeline through human interaction"""
        return Task(
            config=self.tasks_config['gather_timeline'],
            agent=self.goal_analyst(),
            human_input=True
        )

    @task
    def gather_metrics(self) -> Task:
        """Task to gather metrics through human interaction"""
        return Task(
            config=self.tasks_config['gather_metrics'],
            agent=self.goal_analyst(),
            human_input=True
        )

    @task
    def create_goal_summary(self) -> Task:
        """Task to create final goal summary"""
        return Task(
            config=self.tasks_config['create_goal_summary'],
            agent=self.goal_summarizer(),
            output_file='output/goal_summary.md'
        )

    @crew
    def crew(self) -> Crew:
        """Create the Goal Setting crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )
