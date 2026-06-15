import pydantic
from google.antigravity import Agent, LocalAgentConfig
from typing import Optional, Type

def get_explainer_agent(model: Optional[str] = None, schema: Optional[Type[pydantic.BaseModel]] = None, app_data_dir: Optional[str] = None) -> Agent:
    """Configures and instantiates the Concept Explainer Agent.
    
    Args:
        model: Optional model override. If None, uses SDK default.
        schema: Optional structured response schema class.
        app_data_dir: Optional custom application data directory.
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
        )
    }
    if model:
        config_args["model"] = model
    if schema:
        config_args["response_schema"] = schema
    if app_data_dir:
        config_args["app_data_dir"] = app_data_dir
        
    config = LocalAgentConfig(**config_args)
    return Agent(config=config)
