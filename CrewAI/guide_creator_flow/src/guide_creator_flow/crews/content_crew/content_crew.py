# src/guide_creator_flow/crews/content_crew/content_crew.py
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from crewai.llm import LLM
import os 

azure_llm = LLM(
    model="azure/gpt-4o-mini",
    api_key= os.getenv("AZURE_OPENAI_API_KEY"),
    api_base= os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    is_litellm=True
)


@CrewBase
class ContentCrew():
    """Content writing crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def content_writer(self) -> Agent:
        return Agent(
            config=self.agents_config['content_writer'], # type: ignore[index]
            verbose=True,
            llm = azure_llm
        )

    @agent
    def content_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config['content_reviewer'], # type: ignore[index]
            verbose=True,
            llm = azure_llm
        )

    @task
    def write_section_task(self) -> Task:
        return Task(
            config=self.tasks_config['write_section_task'] # type: ignore[index]
        )

    @task
    def review_section_task(self) -> Task:
        return Task(
            config=self.tasks_config['review_section_task'], # type: ignore[index]
            context=[self.write_section_task()]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the content writing crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,     # Or sequential/autonomous
            verbose=True,
        )
'''
    Agent Assignment Behavior
    - Sequential Process: Tasks execute in order, but without assigned agents, CrewAI will assign the first available agent from the crew's agent list to each task.
    - Hierarchical Process: The manager agent assigns tasks to worker agents automatically.
    - Autonomous Mode: CrewAI uses AI to determine the best agent for each task based on agent descriptions and task requirements.

    When to Use Agentless Tasks
    When you want CrewAI to make intelligent agent assignments
    For dynamic workflows where agent roles aren't fixed
    When using hierarchical or autonomous processes
    For simpler crew configurations where agent specialization is less critical
'''