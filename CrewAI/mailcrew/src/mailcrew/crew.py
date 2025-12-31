import os
import sys
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

from crewai import Agent, Task, Crew
from crewai.llm import LLM
from crewai.project import crew, agent, task, CrewBase

# Use LiteLLM for Azure (matches notebook behavior)
azure_llm = LLM(
    model="azure/gpt-4o-mini",
    api_key= os.getenv("AZURE_OPENAI_API_KEY"),
    api_base= os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    is_litellm=True
)
# print(azure_llm.call("hello, how are you?"))

@CrewBase
class MailCrew():
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def textExpansionAgent(self) -> Agent:
        return Agent(
            config=self.agents_config['textExpansionAgentConfig'], # type: ignore[index]
            llm=azure_llm,
            verbose=True
        )

    @agent
    def emailDraftingAgent(self) -> Agent:
        return Agent(
            config=self.agents_config['emailDraftingAgentConfig'], # type: ignore[index]
            llm=azure_llm,
            verbose=True
        )


    @agent
    def summarizeMailAgent(self) -> Agent:
        return Agent(
            config=self.agents_config['summarizeMailAgentConfig'], # type: ignore[index]
            llm=azure_llm,
            verbose=True
        )
    

    @task
    def text_expansion(self) -> Task:
        return Task(
            config = self.tasks_config['text_expansion'], # type: ignore[index]
            agent = self.textExpansionAgent()
        )

    @task
    def email_composition(self) -> Task:
        return Task(
            config = self.tasks_config['email_composition'], # type: ignore[index]
            agent = self.emailDraftingAgent(),
            context = [self.text_expansion()],
            output_file = 'output/drafted_emails.json'
        )

    @task
    def summarize_mail(self) -> Task:
        return Task(
            config = self.tasks_config['email_summarization'], # type: ignore[index]
            agent = self.summarizeMailAgent(),
            output_file = 'output/summarized_emails.json',
            context = [self.email_composition()]
        )
    

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.textExpansionAgent(), self.emailDraftingAgent(), self.summarizeMailAgent()],
            tasks=[self.text_expansion(), self.email_composition(), self.summarize_mail()]
         )