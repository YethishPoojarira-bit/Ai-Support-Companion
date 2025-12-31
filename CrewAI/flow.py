from crewai.flow.flow import Flow, listen, start, router, or_
from crewai.flow.persistence import persist
import asyncio
from pydantic import BaseModel, Field
import random

class AppState(BaseModel):
    value: int = Field(default=0, description="An integer value representing some state.")
    name: str = Field(default="", description="A name associated with the state.")
    count: int = Field(default=0, description="A counter for tracking purposes.")


class StructuredStateFlow(Flow[AppState]):
    def __init__(self, name="unknown"):
        super().__init__()
        self.name = name

    @start()
    def initialize_state(self):
        self.state.value = random.randint(1, 2)
        self.state.name = self.name
        self.state.count += 1
        print(f"Initialized state value to {self.state.value} for {self.state.name}.")
        return f"Value is {self.state.value}"
    
    @router(initialize_state)
    def routing_logic(self):
        self.state.count += 1
        print(f"DEBUG: routing_logic called with state value {self.state.value}")
        return "Path A" if self.state.value == 1 else "Path B"

    @listen("Path A")
    def path_A(self):
        self.state.count += 1
        return f"Executed Path A for {self.state.name}."
    
    @listen("Path B")
    @persist()
    def path_B(self):
        self.state.count += 1
        return f"Executed Path B for {self.state.name}."
    
    @listen(or_("path_A", "path_B"))
    @persist()
    def finalize(self, message):
        with open("debug.log", "a") as f:
            f.write(f"FINAL MESSAGE: {message}\n {self.state}\n")

# Async execution for notebook compatibility - pass name as constructor parameter
StructuredStateFlow(name="Alice").kickoff()
StructuredStateFlow(name="Bob").kickoff()