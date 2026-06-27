import fitz  # PyMuPDF
import httpx
import tempfile
import os
import re
from typing import Optional, List, Dict
from google import genai

def download_and_parse_pdf(url: str, save_text_path: Optional[str] = None) -> str:
    """Downloads a PDF from a URL and extracts its text page-by-page using PyMuPDF."""
    print(f"Downloading PDF from {url}...")
    
    with httpx.Client(follow_redirects=True) as client:
        response = client.get(url, timeout=30.0)
        response.raise_for_status()
        pdf_bytes = response.content

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        temp_pdf.write(pdf_bytes)
        temp_pdf_path = temp_pdf.name

    text = ""
    try:
        doc = fitz.open(temp_pdf_path)
        for page_num, page in enumerate(doc):
            text += f"\n--- Page {page_num + 1} ---\n"
            text += page.get_text()
        doc.close()
    finally:
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)

    if save_text_path:
        os.makedirs(os.path.dirname(os.path.abspath(save_text_path)), exist_ok=True)
        with open(save_text_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Extracted paper text saved to: {save_text_path}")
        
    return text

def chunk_and_embed(text: str, chunk_size: int = 2000, overlap: int = 300) -> List[Dict]:
    """RAPTOR-style sliding window chunking and batch embeddings via Gemini."""
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = start + chunk_size
        chunk_content = text[start:end]
        
        # Determine the page number for the start of this chunk
        page_num = 1
        markers = list(re.finditer(r'--- Page (\d+) ---', text[:start]))
        if markers:
            page_num = int(markers[-1].group(1))
            
        chunks.append({
            "content": chunk_content,
            "page": page_num,
            "start_idx": start
        })
        start += (chunk_size - overlap)
        
    print(f"[*] Generated {len(chunks)} overlapping chunks. Executing Batch Embedding...")
    
    # 2. Single Batch API Call
    try:
        client = genai.Client()
        contents = [c["content"] for c in chunks]
        
        # Pass the entire list of strings in a single call
        response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=contents
        )
        
        # Map returned embeddings back to chunks
        for i, c in enumerate(chunks):
            c["embedding"] = response.embeddings[i].values
    except Exception as e:
        print(f"    [!] Warning: Failed to generate batch embeddings: {e}")
        for c in chunks:
            c["embedding"] = None
            
    return chunks
