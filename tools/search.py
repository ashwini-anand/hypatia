import arxiv
from typing import List, Dict, Any

def search_arxiv(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Queries the arXiv database for papers matching a specific topic.

    Args:
        query: The search query string (e.g., 'quantum mechanics', 'LLM transformers').
        max_results: The maximum number of paper candidates to return.
    """
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance
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
