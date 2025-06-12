from crewai import Agent, Task, Crew, Process

from langchain_anthropic import ChatAnthropic



from pathlib import Path

import yaml
import os
from .rag_system import SimpleRAGSystem

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

def create_tasks(task_configs, agents, rag_system=None):
    tasks = []
    for i, (task_name, cfg) in enumerate(task_configs.items()):
        # Enhance task description with RAG context if available
        description = cfg["description"]
        if rag_system:
            # Extract module from task name
            module = task_name.split('_')[0] if '_' in task_name else None
            # Get problem from description (assuming it's in the format "Problem: {problem}")
            problem_text = description.split("Problem: ")[-1] if "Problem: " in description else description
            context = rag_system.retrieve_relevant_context(problem_text, module)
            if context:
                description = rag_system.enhance_prompt_with_context(description, context)
        
        tasks.append(Task(
            description=description,
            expected_output=cfg["expected_output"],
            agent=agents[i]
        ))
    return tasks

def build_crew():
    agents_config = load_yaml("agents.yaml")
    tasks_config = load_yaml("tasks.yaml")

    # Initialize RAG system
    rag_system = SimpleRAGSystem()

    agents = create_agents(agents_config)
    tasks = create_tasks(tasks_config, agents, rag_system)

    # Optional: print for debug
    print("🧠 Agents loaded:", [a.role for a in agents])
    print("🛠 Tasks created:", [t.description[:50] for t in tasks])
    print("📚 RAG system initialized with Oracle EPM knowledge base")

    return Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential
    )