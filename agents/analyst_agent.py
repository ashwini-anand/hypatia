from google.antigravity import Agent, LocalAgentConfig
from typing import Optional

def get_analyst_agent(model: Optional[str] = None) -> Agent:
    """Configures and instantiates the Analyst Agent.
    
    Args:
        model: Optional model override. If None, uses SDK default.
    """
    config_args = {
        "system_instructions": (
            "You are Hypatia's Analyst Agent, an expert scientific research analyst.\n"
            "Your task is to analyze the raw text of a research paper and extract its core findings and methodologies.\n\n"
            "Guidelines:\n"
            "- Carefully identify the novel contributions, key findings, baseline models, benchmarks/datasets, and methodology steps.\n"
            "- Ensure that every extracted fact is accurate and directly backed by the paper's text.\n"
            "- You must format your response to match the requested JSON schema exactly. Fill in every field."
        )
    }
    if model:
        config_args["model"] = model
        
    config = LocalAgentConfig(**config_args)
    return Agent(config=config)
