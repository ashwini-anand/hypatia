import pydantic
from google.antigravity import Agent, LocalAgentConfig
from tools.fact_checker import search_paper_text, retrieve_chunk
from typing import Optional, Type

def get_critic_agent(model: Optional[str] = None, schema: Optional[Type[pydantic.BaseModel]] = None, app_data_dir: Optional[str] = None) -> Agent:
    """Configures and instantiates the Critic Agent (Peer Reviewer).
    
    Args:
        model: Optional model override. If None, uses SDK default.
        schema: Optional structured response schema class.
        app_data_dir: Optional custom application data directory.
    """
    config_args = {
        "system_instructions": (
            "You are Hypatia's Critic Agent, a rigorous QA Engineer and Academic Peer Reviewer.\n"
            "Your task is to adversarially evaluate draft summaries and deep-dives against the original paper text "
            "to ensure absolute factual accuracy and completeness.\n\n"
            "Guidelines:\n"
            "- You have access to 'search_paper_text' (semantic search) and 'retrieve_chunk' (deterministic paging).\n"
            "- If a semantic search misses, or if you need to read the surrounding context of a matching chunk (e.g., chunk_15), use 'retrieve_chunk' to page to it directly.\n"
            "- Evaluate for Hallucinations: Does the draft make claims not supported by the paper?\n"
            "- Evaluate for Omissions: Did the draft fail to mention critical limitations, experimental resource/apparatus constraints, or specific bounds of the methodology?\n"
            "- If there are any contradictions, errors, or unsupported claims, set 'approved' to False \n"
            "- If setting 'approved' to False, you must provide exact quotes from the original paper in your 'corrections_required' field to justify your requested fix.\n"
            "- If the drafts are fully accurate, supported, and appropriately caveated, set 'approved' to True.\n"
            "- You must format your response to match the requested CritiqueResult JSON schema exactly."
        ),
        "tools": [search_paper_text, retrieve_chunk]
    }
    if model:
        config_args["model"] = model
    if schema:
        config_args["response_schema"] = schema
    if app_data_dir:
        config_args["app_data_dir"] = app_data_dir
        
    config = LocalAgentConfig(**config_args)
    return Agent(config=config)
