# src/research_crew/crew.py
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
import os

# Use LiteLLM for Azure (matches notebook behavior)
azure_llm = LLM(
    model="azure/gpt-4o-mini",
    api_key=os.getenv("AZURE_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY"),
    api_base=os.getenv("AZURE_API_BASE") or os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_API_VERSION") or "2024-12-01-preview",
    is_litellm=True
)

@CrewBase
class ResearchCrew():
    """Research crew for comprehensive topic analysis and reporting"""

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config['researcher'], # type: ignore[index]
            verbose=True,
            tools=[SerperDevTool()],
            llm=azure_llm
        )

    @agent
    def analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['analyst'], # type: ignore[index]
            verbose=True,
            llm=azure_llm
        )

    @task
    def research_task(self) -> Task:
        return Task(
            config=self.tasks_config['research_task'] # type: ignore[index]
        )

    @task
    def analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['analysis_task'], # type: ignore[index]
            output_file='output/report.md'
        )

    @crew
    def crew(self) -> Crew:
        """Creates the research crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )