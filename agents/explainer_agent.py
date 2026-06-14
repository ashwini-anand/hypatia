from google.antigravity import Agent, LocalAgentConfig
from state import ConceptCardsList
from typing import Optional

def get_explainer_agent(model: Optional[str] = None) -> Agent:
    """Configures and instantiates the Concept Explainer Agent.
    
    Args:
        model: Optional model override. If None, uses SDK default.
    """
    config_args = {
        "system_instructions": (
            "You are Hypatia's Concept Explainer Agent, an expert science communicator.\n"
            "Your task is to identify key scientific or technical terms/concepts from a research paper "
            "and create simple, plain-English explanations and memorable real-world analogies for each.\n\n"
            "Guidelines:\n"
            "- Target 3 to 7 complex concepts from the paper (e.g., specific algorithms, architectures, theorems).\n"
            "- Focus on making the explanation understandable to a high school student.\n"
            "- You must format your response to match the requested JSON schema (ConceptCardsList) exactly."
        ),
        "response_schema": ConceptCardsList
    }
    if model:
        config_args["model"] = model
        
    config = LocalAgentConfig(**config_args)
    return Agent(config=config)
