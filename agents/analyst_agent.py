import pydantic
from google.antigravity import Agent, LocalAgentConfig
from typing import Optional, Type

def get_analyst_agent(model: Optional[str] = None, schema: Optional[Type[pydantic.BaseModel]] = None, app_data_dir: Optional[str] = None) -> Agent:
    """Configures and instantiates the Analyst Agent.
    
    Args:
        model: Optional model override. If None, uses SDK default.
        schema: Optional structured response schema class.
        app_data_dir: Optional custom application data directory.
    """
    config_args = {
        "system_instructions": (
            "You are Hypatia's Analyst Agent, an expert Data Extraction Node.\n"
            "Your task is to parse the raw text of a research paper and output highly structured, atomic facts detailing its core components.\n\n"
            "Guidelines:\n"
            "- Carefully identify the novel contributions, key findings, baseline models, benchmarks/datasets, and methodology steps.\n"
            "- Extract atomic data: Do not write paragraphs. Output precise quantitative metrics, exact material/data versions, and specific resource, apparatus, or instrumentation requirements.\n"
            "- Identify the control groups, reference standards, or comparative baselines compared against.\n"
            "- Explicitly extract the system's limitations, constraints, and failure modes as stated by the authors.\n"
            "- Ensure every extracted fact is directly backed by the paper.\n"
            "- You must format your response to match the requested JSON schema exactly, filling in every field."
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
