import pymupdf
import re
import html
import os

def markdown_to_html(md_text: str) -> str:
    """A lightweight, robust parser that converts Markdown text to styled HTML
    for PyMuPDF Story rendering.
    """
    lines = md_text.split("\n")
    html_lines = []
    in_list = False
    
    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("<br/>")
            continue
            
        # Headers
        if line_strip.startswith("### "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            escaped_text = html.escape(line_strip[4:])
            # parse bold in headers
            escaped_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', escaped_text)
            html_lines.append(f"<h3>{escaped_text}</h3>")
        elif line_strip.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            escaped_text = html.escape(line_strip[3:])
            escaped_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', escaped_text)
            html_lines.append(f"<h2>{escaped_text}</h2>")
        elif line_strip.startswith("# "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            escaped_text = html.escape(line_strip[2:])
            escaped_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', escaped_text)
            html_lines.append(f"<h1>{escaped_text}</h1>")
        # List items
        elif line_strip.startswith("- ") or line_strip.startswith("* "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            content = html.escape(line_strip[2:])
            # bold in lists
            content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
            html_lines.append(f"<li>{content}</li>")
        # Paragraphs
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            content = html.escape(line_strip)
            content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
            html_lines.append(f"<p>{content}</p>")
            
    if in_list:
        html_lines.append("</ul>")
        
    body = "\n".join(html_lines)
    
    # Wrap in standard CSS
    return f"""
    <html>
    <head>
    <style>
        body {{
            font-family: sans-serif;
            line-height: 1.5;
            color: #333333;
            margin: 40px;
        }}
        h1 {{ color: #1a365d; border-bottom: 2px solid #1a365d; padding-bottom: 8px; font-size: 24px; }}
        h2 {{ color: #2c5282; margin-top: 24px; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; font-size: 18px; }}
        h3 {{ color: #2b6cb0; margin-top: 16px; font-size: 15px; }}
        li {{ margin-bottom: 6px; font-size: 12px; }}
        strong {{ color: #1a202c; }}
        p {{ margin-bottom: 12px; font-size: 12px; }}
        ul {{ margin-top: 4px; margin-bottom: 12px; padding-left: 20px; }}
    </style>
    </head>
    <body>
        {body}
    </body>
    </html>
    """

def convert_markdown_to_pdf(md_text: str, output_pdf_path: str):
    """Converts a markdown string into a styled PDF document using PyMuPDF Story.
    """
    html_content = markdown_to_html(md_text)
    
    # Page setup (Standard Letter size)
    mediabox = pymupdf.paper_rect("letter")
    # Margin layout: left, top, right, bottom margins (0.75 inch margins = 54 pt)
    where = mediabox + (54, 54, -54, -54)
    
    # Create the Story and DocumentWriter
    story = pymupdf.Story(html=html_content)
    writer = pymupdf.DocumentWriter(output_pdf_path)
    
    more = 1
    page_count = 0
    while more:
        device = writer.begin_page(mediabox)
        more, _ = story.place(where)
        story.draw(device)
        writer.end_page()
        page_count += 1
        
    writer.close()
    print(f"Generated PDF with {page_count} pages at: {output_pdf_path}")
