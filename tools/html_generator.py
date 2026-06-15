import html
import os
import re

def markdown_to_html_rich(md_text: str) -> str:
    """A robust, lightweight Markdown-to-HTML parser that supports headers,
    bold text, lists, tables, fenced code blocks, and Mermaid diagrams.
    """
    lines = md_text.split("\n")
    html_lines = []
    in_list = False
    in_code_block = False
    code_block_lang = ""
    in_table = False
    table_headers = []
    table_rows = []
    
    # helper to close open lists or tables
    def close_structures():
        nonlocal in_list, in_table, table_headers, table_rows
        out = []
        if in_list:
            out.append("</ul>")
            in_list = False
        if in_table:
            out.append("<table>")
            if table_headers:
                out.append("<thead><tr>")
                for h in table_headers:
                    out.append(f"<th>{h}</th>")
                out.append("</tr></thead>")
            out.append("<tbody>")
            for r in table_rows:
                out.append("<tr>")
                for cell in r:
                    out.append(f"<td>{cell}</td>")
                out.append("</tr>")
            out.append("</tbody></table>")
            in_table = False
            table_headers = []
            table_rows = []
        return out

    for line in lines:
        line_strip = line.strip()
        
        # Code block handling
        if line_strip.startswith("```"):
            if in_code_block:
                html_lines.append("</code></pre>")
                in_code_block = False
            else:
                html_lines.extend(close_structures())
                lang = line_strip[3:].strip().lower()
                if lang == "mermaid":
                    html_lines.append('<pre class="mermaid">')
                else:
                    html_lines.append(f'<pre><code class="language-{lang or "text"}">')
                in_code_block = True
                code_block_lang = lang
            continue
            
        if in_code_block:
            # For mermaid blocks and code, escape HTML entities
            html_lines.append(html.escape(line))
            continue
            
        # Table handling
        if "|" in line_strip:
            is_separator = re.match(r'^[\s|:-]+$', line_strip) is not None
            
            cells = [cell.strip() for cell in line_strip.split("|")]
            if line_strip.startswith("|") and len(cells) > 0 and cells[0] == "":
                cells.pop(0)
            if line_strip.endswith("|") and len(cells) > 0 and cells[-1] == "":
                cells.pop()
                
            if is_separator:
                continue
                
            if not in_table:
                html_lines.extend(close_structures())
                in_table = True
                table_headers = [re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html.escape(c)) for c in cells]
            else:
                processed_cells = [re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html.escape(c)) for c in cells]
                table_rows.append(processed_cells)
            continue
        elif in_table:
            html_lines.extend(close_structures())
            
        # Empty line handling
        if not line_strip:
            html_lines.extend(close_structures())
            html_lines.append("<br/>")
            continue
            
        # Headers
        if line_strip.startswith("### "):
            html_lines.extend(close_structures())
            escaped_text = html.escape(line_strip[4:])
            escaped_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', escaped_text)
            html_lines.append(f"<h3>{escaped_text}</h3>")
        elif line_strip.startswith("## "):
            html_lines.extend(close_structures())
            escaped_text = html.escape(line_strip[3:])
            escaped_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', escaped_text)
            html_lines.append(f"<h2>{escaped_text}</h2>")
        elif line_strip.startswith("# "):
            html_lines.extend(close_structures())
            escaped_text = html.escape(line_strip[2:])
            escaped_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', escaped_text)
            html_lines.append(f"<h1>{escaped_text}</h1>")
        # List items
        elif line_strip.startswith("- ") or line_strip.startswith("* "):
            if not in_list:
                html_lines.extend(close_structures())
                html_lines.append("<ul>")
                in_list = True
            content = html.escape(line_strip[2:])
            content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
            html_lines.append(f"<li>{content}</li>")
        # Paragraphs
        else:
            html_lines.extend(close_structures())
            content = html.escape(line_strip)
            content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
            html_lines.append(f"<p>{content}</p>")
            
    html_lines.extend(close_structures())
    if in_code_block:
        html_lines.append("</code></pre>")
        
    return "\n".join(html_lines)


def convert_markdown_to_html(md_text: str, output_html_path: str, title: str = "Research Output"):
    """Converts a markdown string into a beautifully styled, standalone HTML document
    and saves it to the specified path.
    """
    body_content = markdown_to_html_rich(md_text)
    
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #f8fafc;
            --container-bg: #ffffff;
            --text-main: #0f172a;
            --text-muted: #475569;
            --primary: #4f46e5;
            --primary-hover: #4338ca;
            --border-color: #e2e8f0;
            --code-bg: #f1f5f9;
            --code-text: #0f172a;
            --table-header-bg: #f8fafc;
        }}

        @media (prefers-color-scheme: dark) {{
            :root {{
                --bg-color: #0b0f19;
                --container-bg: #111827;
                --text-main: #f3f4f6;
                --text-muted: #9ca3af;
                --primary: #6366f1;
                --primary-hover: #4f46e5;
                --border-color: #1f2937;
                --code-bg: #1f2937;
                --code-text: #f3f4f6;
                --table-header-bg: #1f2937;
            }}
        }}

        body {{
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            line-height: 1.6;
            margin: 0;
            padding: 40px 20px;
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
            background-color: var(--container-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
            padding: 40px;
        }}

        h1, h2, h3 {{
            font-weight: 700;
            color: var(--text-main);
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }}

        h1 {{
            font-size: 2.25rem;
            border-bottom: 2px solid var(--primary);
            padding-bottom: 12px;
            margin-top: 0;
        }}

        h2 {{
            font-size: 1.5rem;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 6px;
        }}

        h3 {{
            font-size: 1.2rem;
        }}

        p {{
            margin-bottom: 1.25rem;
            font-size: 1rem;
            color: var(--text-muted);
        }}

        a {{
            color: var(--primary);
            text-decoration: none;
        }}

        a:hover {{
            text-decoration: underline;
        }}

        ul {{
            margin-top: 0;
            margin-bottom: 1.25rem;
            padding-left: 1.5rem;
        }}

        li {{
            margin-bottom: 0.5rem;
            color: var(--text-muted);
        }}

        /* Tables styling */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 0.95rem;
        }}

        th, td {{
            border: 1px solid var(--border-color);
            padding: 12px 16px;
            text-align: left;
        }}

        th {{
            background-color: var(--table-header-bg);
            font-weight: 600;
        }}

        tr:nth-child(even) {{
            background-color: rgba(0, 0, 0, 0.02);
        }}

        /* Code Block Styling */
        pre {{
            background-color: var(--code-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px;
            overflow-x: auto;
            margin-bottom: 1.25rem;
        }}

        code {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
            color: var(--code-text);
        }}

        /* Mermaid styling */
        .mermaid {{
            display: flex;
            justify-content: center;
            background-color: transparent !important;
            border: none !important;
            padding: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        {body_content}
    </div>

    <!-- Mermaid.js integration -->
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ 
            startOnLoad: true, 
            theme: window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'neutral',
            securityLevel: 'loose'
        }});
    </script>
</body>
</html>
"""

    os.makedirs(os.path.dirname(os.path.abspath(output_html_path)), exist_ok=True)
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"Generated HTML page at: {output_html_path}")
