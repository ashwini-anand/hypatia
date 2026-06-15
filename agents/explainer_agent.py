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
            "You are Hypatia's Concept Explainer Agent, a Technical Educator.\n"
            "Your task is to identify 3 to 7 highly complex scientific or technical terms from a research paper "
            "and create clear, plain-English explanations and systemic analogies for each.\n\n"
            "Guidelines:\n"
            "- Target audience: A software engineer who is unfamiliar with this specific sub-field.\n"
            "- For each concept, provide: 1) A concise technical definition, 2) A physical or systemic analogy, and 3) An explicit statement of where the analogy breaks down or fails to capture the technical reality.\n"
            "- You must format your response to match the requested JSON schema (ConceptCardsList) exactly."
        ),
        "tools": []
    }
    if model:
        config_args["model"] = model
    if schema:
        config_args["response_schema"] = schema
    if app_data_dir:
        config_args["app_data_dir"] = app_data_dir
        
    config = LocalAgentConfig(**config_args)
    return Agent(config=config)
