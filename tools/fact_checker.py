from google.antigravity import ToolContext
import re
from typing import List, Dict, Any
import math

# We will store a reference to the active memory map here so the tool can access it
_ACTIVE_MEMORY_MAP = None

def set_active_memory_map(memory_map):
    """Sets the active HierarchicalMemoryMap for the tool to search over."""
    global _ACTIVE_MEMORY_MAP
    _ACTIVE_MEMORY_MAP = memory_map

def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Computes cosine similarity between two vectors."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a > 0 and norm_b > 0:
        return dot / (norm_a * norm_b)
    return 0.0

def search_paper_text(query: str, ctx: ToolContext) -> str:
    """Searches the HierarchicalMemoryMap for passages containing matching terms using Reciprocal Rank Fusion (RRF).

    Args:
        query: The search keywords or specific claim to check (e.g., 'ResNet-50', 'learning rate', 'Table 1').
        ctx: The ToolContext injected by the Antigravity SDK.
    """
    global _ACTIVE_MEMORY_MAP
    if not _ACTIVE_MEMORY_MAP:
        return "Error: Memory Map not loaded in the harness."

    # Preprocess lexical query
    terms = [term.lower() for term in re.findall(r'[a-zA-Z0-9_-]+', query) if len(term) > 2]
    
    # 1. Lexical Search
    lexical_scores = {}
    for node_id, node in _ACTIVE_MEMORY_MAP.nodes.items():
        if node.level == 0:
            count = sum(1 for term in terms if term in node.raw_text.lower())
            if count > 0:
                lexical_scores[node_id] = count

    # 2. Semantic Vector Search
    semantic_scores = {}
    try:
        from google import genai
        client = genai.Client()
        response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=query
        )
        query_emb = response.embeddings[0].values
        
        for node_id, node in _ACTIVE_MEMORY_MAP.nodes.items():
            if node.level == 0 and node.embedding:
                sim = cosine_similarity(query_emb, node.embedding)
                semantic_scores[node_id] = sim
    except Exception as e:
        print(f"Warning: Semantic search failed, falling back to pure lexical: {e}")

    # 3. Reciprocal Rank Fusion (RRF)
    lexical_ranked = sorted(lexical_scores.items(), key=lambda x: x[1], reverse=True)
    semantic_ranked = sorted(semantic_scores.items(), key=lambda x: x[1], reverse=True)
    
    rrf_scores = {}
    k = 60
    
    for rank, (node_id, score) in enumerate(lexical_ranked):
        rrf_scores[node_id] = rrf_scores.get(node_id, 0) + 1 / (k + rank + 1)
        
    for rank, (node_id, score) in enumerate(semantic_ranked):
        rrf_scores[node_id] = rrf_scores.get(node_id, 0) + 1 / (k + rank + 1)
        
    final_ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    if not final_ranked:
        return f"No matches found in the Memory Map for keywords: {terms}"

    # 4. Format the top 3 most relevant passages for the Critic
    results_header = f"Found {len(final_ranked)} matching passages. Showing top {min(3, len(final_ranked))} RRF matches:\n"
    formatted = []
    
    for i, (node_id, score) in enumerate(final_ranked[:3]):
        node = _ACTIVE_MEMORY_MAP.nodes[node_id]
        clean_content = " ".join(node.raw_text.split())
        formatted.append(f"[Match {i+1}] (Node ID: {node_id}, RRF Score: {score:.4f}):\n... {clean_content} ...")

    return results_header + "\n\n".join(formatted)

def retrieve_chunk(chunk_index: int, ctx: ToolContext) -> str:
    """Retrieves a specific chunk of the paper text deterministically by its index (e.g. 0, 1, 15).
    
    Args:
        chunk_index: The numerical index of the chunk to retrieve (e.g., if you want chunk_15, pass 15).
        ctx: The ToolContext injected by the Antigravity SDK.
    """
    global _ACTIVE_MEMORY_MAP
    if not _ACTIVE_MEMORY_MAP:
        return "Error: Memory Map not loaded in the harness."
        
    node_id = f"chunk_{chunk_index}"
    if node_id not in _ACTIVE_MEMORY_MAP.nodes:
        return f"Error: {node_id} does not exist. The document might have fewer chunks."
        
    node = _ACTIVE_MEMORY_MAP.nodes[node_id]
    return f"--- {node_id} ---\n{node.raw_text}"
