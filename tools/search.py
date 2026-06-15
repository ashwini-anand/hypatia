import arxiv
from typing import List, Dict, Any

def search_arxiv(query: str, max_results: int = 5, sort_by: str = "relevance") -> List[Dict[str, Any]]:
    """Queries the arXiv database for papers matching a specific topic.

    Args:
        query: The search query string (e.g., 'quantum mechanics', 'LLM transformers').
        max_results: The maximum number of paper candidates to return.
        sort_by: The criterion to sort results. Values: 'relevance', 'submitted_date', 'last_updated_date'.
    """
    client = arxiv.Client()
    
    criterion = arxiv.SortCriterion.Relevance
    sb = sort_by.strip().lower()
    if sb == "submitted_date":
        criterion = arxiv.SortCriterion.SubmittedDate
    elif sb == "last_updated_date":
        criterion = arxiv.SortCriterion.LastUpdatedDate
        
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=criterion,
        sort_order=arxiv.SortOrder.Descending
    )
    
    results = []
    try:
        for result in client.results(search):
            results.append({
                "title": result.title,
                "url": result.pdf_url,
                "authors": [author.name for author in result.authors],
                "published": result.published.strftime("%Y-%m-%d"),
                "abstract": result.summary
            })
    except Exception as e:
        print(f"Error querying arXiv: {e}")
        
    return results
