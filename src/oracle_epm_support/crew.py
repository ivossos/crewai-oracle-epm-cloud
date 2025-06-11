from crewai import Agent, Task, Crew, Process

from langchain_anthropic import ChatAnthropic



from pathlib import Path

import yaml
import os

# Load Claude model with error handling
try:
    claude = ChatAnthropic(model="claude-opus-4-20250514")
except Exception as e:
    print(f"Failed to initialize Claude model: {e}")
    claude = None

CONFIG_PATH = Path(__file__).parent / "config"

def load_yaml(filename):
    with open(CONFIG_PATH / filename, "r") as f:
        return yaml.safe_load(f)

def create_agents(agent_configs):
    if claude is None:
        print("Warning: Claude model not initialized, using default LLM")
    return [
        Agent(
            role=cfg["role"],
            goal=cfg["goal"],
            backstory=cfg["backstory"],
            verbose=True,
            memory=True,
            llm=claude if claude else None
        ) for cfg in agent_configs.values()
    ]

def create_tasks(task_configs, agents):
    return [
        Task(
            description=cfg["description"],
            expected_output=cfg["expected_output"],
            agent=agents[i]
        ) for i, cfg in enumerate(task_configs.values())
    ]

def build_crew():
    agents_config = load_yaml("agents.yaml")
    tasks_config = load_yaml("tasks.yaml")

    agents = create_agents(agents_config)
    tasks = create_tasks(tasks_config, agents)

    # Optional: print for debug
    print("🧠 Agents loaded:", [a.role for a in agents])
    print("🛠 Tasks created:", [t.description[:50] for t in tasks])

    return Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential
    )