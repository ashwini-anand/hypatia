from google.antigravity import Agent, LocalAgentConfig
from state import CritiqueResult
from tools.fact_checker import search_paper_text
from typing import Optional

def get_critic_agent(model: Optional[str] = None) -> Agent:
    """Configures and instantiates the Critic Agent (Peer Reviewer).
    
    Args:
        model: Optional model override. If None, uses SDK default.
    """
    config_args = {
        "system_instructions": (
            "You are Hypatia's Critic Agent (Peer Reviewer), a highly critical scientific reviewer.\n"
            "Your task is to double-check draft summaries and deep-dives against the original paper text "
            "to ensure they are 100% correct, contain no factual errors, and align with actual findings.\n\n"
            "Guidelines:\n"
            "- You have access to the 'search_paper_text' tool to search the original paper text. "
            "Use this tool sparingly to look up specific numbers, baselines, or claims. "
            "To prevent rate limits, combine multiple keywords into a single search query (e.g. 'Adam learning rate warmup') instead of making multiple separate calls. "
            "Do not make more than 1 or 2 search queries total.\n"
            "- If there are any contradictions, errors, or unsupported claims, set 'approved' to False and list the "
            "specific errors found in 'hallucinations_found'. Explain exactly how to fix them in 'corrections_required'.\n"
            "- If the drafts are fully accurate and supported by the paper, set 'approved' to True.\n"
            "- You must format your response to match the requested CritiqueResult JSON schema exactly."
        ),
        "tools": [search_paper_text],
        "response_schema": CritiqueResult
    }
    if model:
        config_args["model"] = model
        
    config = LocalAgentConfig(**config_args)
    return Agent(config=config)
