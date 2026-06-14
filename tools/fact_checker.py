from google.antigravity import ToolContext
import re
from typing import List

_ACTIVE_PAPER_TEXT = ""

def set_active_paper_text(text: str):
    """Sets the active paper text globally for the fact-checking tool fallback."""
    global _ACTIVE_PAPER_TEXT
    _ACTIVE_PAPER_TEXT = text

def search_paper_text(query: str, ctx: ToolContext) -> str:
    """Searches the original text of the research paper for passages containing matching terms.

    Args:
        query: The search keywords or specific claim to check (e.g., 'ResNet-50', 'learning rate', 'Table 1').
        ctx: The ToolContext injected by the Antigravity SDK.
    """
    # 1. Retrieve the parsed paper text from the shared tool state or fallback to global
    paper_text = ctx.get_state("original_paper_text", "")
    if not paper_text:
        paper_text = _ACTIVE_PAPER_TEXT
        
    if not paper_text:
        return "Error: Original paper text is not loaded in the context or global fallback."

    # 2. Preprocess the search terms
    # Extract alphanumeric words longer than 2 characters as search terms
    terms = [term.lower() for term in re.findall(r'[a-zA-Z0-9_-]+', query) if len(term) > 2]
    if not terms:
        return f"No searchable keywords extracted from query: '{query}'"

    # 3. Create overlapping chunks of text to search over
    chunk_size = 1500
    overlap = 300
    chunks = []
    
    start = 0
    while start < len(paper_text):
        end = start + chunk_size
        chunk_content = paper_text[start:end]
        
        # Determine the page number for the start of this chunk
        page_num = 1
        markers = list(re.finditer(r'--- Page (\d+) ---', paper_text[:start]))
        if markers:
            page_num = int(markers[-1].group(1))
            
        chunks.append({
            "content": chunk_content,
            "page": page_num,
            "start_idx": start
        })
        start += (chunk_size - overlap)

    # 4. Search chunks and count unique keyword matches
    matches = []
    for chunk in chunks:
        match_count = sum(1 for term in terms if term in chunk["content"].lower())
        if match_count > 0:
            matches.append((match_count, chunk))

    # 5. Sort matches by the number of matching terms in descending order
    matches.sort(key=lambda x: x[0], reverse=True)

    if not matches:
        return f"No matching passages found in the paper for keywords: {terms}"

    # 6. Format and return the top 5 most relevant passages
    results_header = f"Found {len(matches)} matching passages. Showing the top {min(5, len(matches))} matches:\n"
    formatted_matches = []
    
    for i, (count, chunk) in enumerate(matches[:5]):
        # Clean up whitespace inside chunk for readability
        clean_content = " ".join(chunk["content"].split())
        formatted_matches.append(f"[Match {i+1}] (Page {chunk['page']}, Keywords matched: {count}):\n... {clean_content} ...")

    return results_header + "\n\n".join(formatted_matches)
