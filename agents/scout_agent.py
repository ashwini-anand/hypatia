import pydantic
from google.antigravity import Agent, LocalAgentConfig
from tools.search import search_arxiv
from typing import Optional, Type

def get_scout_agent(model: Optional[str] = None, schema: Optional[Type[pydantic.BaseModel]] = None, app_data_dir: Optional[str] = None) -> Agent:
    """Configures and instantiates the Searcher (Scout) Agent.
    
    Args:
        model: Optional model override. If None, uses SDK default.
        schema: Optional structured response schema class.
        app_data_dir: Optional custom application data directory.
    """
    config_args = {
        "system_instructions": (
            "You are Hypatia's Searcher Agent (aka Scout), an academic librarian specializing in locating research papers.\n"
            "Your task is to take the user's natural language query (e.g. topic, date range, field of research) and search "
            "for relevant research papers using your 'search_arxiv' tool.\n\n"
            "Guidelines:\n"
            "- Always call the 'search_arxiv' tool with a clear search query derived from the user's prompt.\n"
            "- You must format your final output to match the requested CandidatePapersList JSON schema exactly."
        ),
        "tools": [search_arxiv]
    }
    if model:
        config_args["model"] = model
    if schema:
        config_args["response_schema"] = schema
    if app_data_dir:
        config_args["app_data_dir"] = app_data_dir
        
    config = LocalAgentConfig(**config_args)
    return Agent(config=config)
