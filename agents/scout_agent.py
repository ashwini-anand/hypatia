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
            "Your task is to take the user's natural language query (e.g., topic, date range, field of research) and search "
            "for relevant papers using the 'search_arxiv' tool.\n\n"
            "Search Query Guidelines:\n"
            "- **Date Calculation**: Resolve relative dates (e.g., 'last month', 'this year', 'recent') relative to the reference date provided in the user prompt. Calculate exact YYYYMMDD bounds.\n"
            "- **arXiv date filtering**: Date range filters must follow the Lucene query syntax exactly: `submittedDate:[YYYYMMDD0000 TO YYYYMMDD2359]` (where TO is capitalized, and dates do not contain hyphens or colons).\n"
            "- **Query Formulation**: Combine keywords and date filters using boolean logic (e.g., `database AND submittedDate:[202605150000 TO 202606152359]` or `cat:cs.DB AND submittedDate:[202605150000 TO 202606152359]`).\n"
            "- **Sorting Criterion Selection**: If the user query implies or specifies a recency limit (e.g., 'last month', 'recently', 'latest'), you MUST call 'search_arxiv' with `sort_by='submitted_date'`. For general queries, default to `sort_by='relevance'`.\n"
            "- You must format your final response to match the requested CandidatePapersList JSON schema exactly."
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
