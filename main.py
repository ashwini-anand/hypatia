import asyncio
import os
import sys
from dotenv import load_dotenv
from state import ResearchState
from workflow import run_research_workflow
from tools.html_generator import convert_markdown_to_html

def print_banner():
    print(r"""
=========================================================
  _    _                  _   _       
 | |  | |                | | (_)      
 | |__| |_   _ _ __   __ _| |_ _  __ _ 
 |  __  | | | | '_ \ / _` | __| |/ _` |
 | |  | | |_| | |_) | (_| | |_| | (_| |
 |_|  |_|\__, | .__/ \__,_|\__|_|\__,_|
          __/ | |                      
         |___/|_|                      
     Multi-Agent Scientific Literature Assistant
=========================================================
    """)

async def main():
    # Load environment variables (API Keys)
    load_dotenv()
    if not os.getenv("GEMINI_API_KEY"):
        print("[!] Warning: GEMINI_API_KEY not found in environment or .env file.")
        api_key = input("Please enter your Gemini API Key: ").strip()
        if api_key:
            os.environ["GEMINI_API_KEY"] = api_key
        else:
            print("[!] Error: Gemini API Key is required to run the agents. Exiting.")
            return

    # Check for CLI flags in command-line arguments
    debug_mode = "--debug" in sys.argv
    lite_mode = "--lite" in sys.argv
    
    # Parse --model flag from command-line arguments
    model_override = None
    if "--model" in sys.argv:
        try:
            model_idx = sys.argv.index("--model")
            if model_idx + 1 < len(sys.argv):
                model_override = sys.argv[model_idx + 1]
        except ValueError:
            pass

    print_banner()
    if debug_mode:
        print("[🔧] Debug Mode Enabled: Detailed logs and agent thoughts will be streamed.")
    if lite_mode:
        print("[⚡] Lite Mode Enabled: Running with token-saving configurations and rate-limiting sleeps.")
    else:
        print("[📄] Full Context Mode Enabled: Running with full document context and no rate-limiting sleeps.")
    
    # Set default model if not overridden via CLI
    if not model_override:
        model_override = "gemini-3.5-flash"
    print(f"[🤖] Model Selected: {model_override}")

    print("\nHow would you like to load a paper?")
    print("1. Search arXiv using a query (e.g. 'distributed database consistency' or 'CRISPR gene editing')")
    print("2. Provide a direct URL to a paper PDF (e.g. 'https://arxiv.org/pdf/1901.01930')")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    state = ResearchState()
    
    if choice == "1":
        query = input("\nEnter your search query: ").strip()
        if not query:
            print("[!] Query cannot be empty. Exiting.")
            return
        state.user_query = query
    elif choice == "2":
        url = input("\nEnter the paper PDF URL: ").strip()
        if not url:
            print("[!] URL cannot be empty. Exiting.")
            return
        state.paper_url = url
    else:
        print("[!] Invalid choice. Exiting.")
        return

    # Create output directory
    os.makedirs("output", exist_ok=True)
    
    try:
        # Run the agentic workflow
        final_state = await run_research_workflow(
            state, 
            debug=debug_mode, 
            lite=lite_mode, 
            model=model_override
        )
        
        # Determine paper directory
        folder_name = final_state.selected_paper.get_folder_name() if final_state.selected_paper else "paper"
        paper_dir = os.path.join("output", folder_name)
        os.makedirs(paper_dir, exist_ok=True)
        
        # Save output Markdown files
        summary_path = os.path.join(paper_dir, "summary.md")
        deep_dive_path = os.path.join(paper_dir, "deep_dive.md")
        
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(final_state.summary_draft or "")
            
        with open(deep_dive_path, "w", encoding="utf-8") as f:
            f.write(final_state.deep_dive_draft or "")
            
        print(f"\n[+] Success! Summary saved to: {summary_path}")
        print(f"[+] Success! Deep Dive saved to: {deep_dive_path}")
        
        # Save output HTML files
        print("[*] Generating styled HTML documents...")
        summary_html_path = os.path.join(paper_dir, "summary.html")
        deep_dive_html_path = os.path.join(paper_dir, "deep_dive.html")
        
        paper_title = final_state.selected_paper.title if final_state.selected_paper else "Research Paper"
        convert_markdown_to_html(final_state.summary_draft or "", summary_html_path, title=f"Summary: {paper_title}")
        convert_markdown_to_html(final_state.deep_dive_draft or "", deep_dive_html_path, title=f"Deep Dive: {paper_title}")
        
        print(f"[+] Success! Summary HTML saved to: {summary_html_path}")
        print(f"[+] Success! Deep Dive HTML saved to: {deep_dive_html_path}")
        print(f"[+] Check the '{paper_dir}' directory for files.")
        
    except Exception as e:
        print(f"\n[!] An error occurred during workflow execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
