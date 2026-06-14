import fitz  # PyMuPDF
import httpx
import tempfile
import os
from typing import Optional

def download_and_parse_pdf(url: str, save_text_path: Optional[str] = None) -> str:
    """Downloads a PDF from a URL and extracts its text page-by-page using PyMuPDF.

    Args:
        url: The direct HTTP URL of the PDF research paper.
        save_text_path: Optional file path to save the extracted raw text to.
    """
    print(f"Downloading PDF from {url}...")
    
    # 1. Download the PDF file using httpx
    # Follow redirects to ensure we get the actual PDF
    with httpx.Client(follow_redirects=True) as client:
        response = client.get(url, timeout=30.0)
        response.raise_for_status()
        pdf_bytes = response.content

    # 2. Write the bytes to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        temp_pdf.write(pdf_bytes)
        temp_pdf_path = temp_pdf.name

    text = ""
    try:
        # 3. Open and parse with PyMuPDF
        doc = fitz.open(temp_pdf_path)
        for page_num, page in enumerate(doc):
            text += f"\n--- Page {page_num + 1} ---\n"
            text += page.get_text()
        doc.close()
    finally:
        # Clean up the temporary PDF file
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)

    # 4. Optionally save to a file
    if save_text_path:
        # Ensure parent directories exist
        os.makedirs(os.path.dirname(os.path.abspath(save_text_path)), exist_ok=True)
        with open(save_text_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Extracted paper text saved to: {save_text_path}")
        
    return text
