import asyncio
import os
import json
import re
from state import ResearchState, CandidatePaper, CandidatePapersList, PaperFacts, ConceptCardsList, CritiqueResult, ConceptCard
from tools.parser import download_and_parse_pdf
from tools.fact_checker import set_active_paper_text
from agents.scout_agent import get_scout_agent
from agents.analyst_agent import get_analyst_agent
from agents.explainer_agent import get_explainer_agent
from agents.summarizer_agent import get_summarizer_agent
from agents.deep_dive_agent import get_deep_dive_agent
from agents.critic_agent import get_critic_agent
from typing import Optional, Type
import pydantic

async def log_agent_thoughts(response, agent_name: str, debug: bool, model: Optional[str] = None):
    """Utility to print thoughts stream when debug is enabled.
    """
    if not debug:
        return
        
    print(f"\n🧠 [{agent_name} Thought Process]: ", end="", flush=True)
    try:
        async for thought in response.thoughts:
            print(thought, end="", flush=True)
    except Exception as e:
        print(f" (Error streaming thoughts: {e})", end="")
    print("\n")


async def parse_structured_output(response, model_class: Type[pydantic.BaseModel], agent_name: str) -> pydantic.BaseModel:
    """Safely extracts structured output. If the model does not support native schema restrictions
    (e.g., Gemma), extracts JSON from raw text using regex.
    """
    try:
        # 1. Attempt native SDK structured extraction
        structured_data = await response.structured_output()
        if structured_data is not None:
            return model_class(**structured_data)
    except Exception as e:
        # Fallback to text parsing
        pass

    # 2. Text Parsing Fallback
    raw_text = await response.text()
    
    # Locate JSON block inside markdown formatting if present
    json_match = re.search(r"```json\s*(.*?)\s*```", raw_text, re.DOTALL)
    json_str = json_match.group(1) if json_match else raw_text
    
    try:
        parsed_dict = json.loads(json_str.strip())
        return model_class(**parsed_dict)
    except Exception as e:
        print(f"[!] Warning: Failed to parse structured output for {agent_name}. Error: {e}")
        return model_class.model_construct()

async def run_research_workflow(
    state: ResearchState, 
    debug: bool = False, 
    lite: bool = False, 
    model: Optional[str] = None
) -> ResearchState:
    """Orchestrates the research and drafting pipeline using specialized agents.
    
    Args:
        state: The current ResearchState.
        debug: If True, prints additional logs and streams agent thoughts.
        lite: If True, runs in token-saving mode (truncates paper text and uses RAG for the Critic).
              If False (Default), runs in Full Context Mode (passes full paper text for analysis).
        model: Optional model override string (e.g. 'gemini-3.5-pro').
    """
    model_name = model or "gemini-3.5-flash"
    
    print("\n==================================================")
    print("🚀 Starting Hypatia Scientific Research Workflow")
    if lite:
        print("[⚡] Mode: Lite (Low Token / Rate-Limit Safe)")
    else:
        print("[📄] Mode: Full Context (Full Document Analysis)")
    print(f"[🤖] Model: {model_name}")
    print("==================================================")

    # Context Check for Gemma: Warn the user if they try to run a Gemma model in Full Context Mode
    if "gemma" in model_name.lower() and not lite:
        print("\n⚠️  [Warning]")
        print("Gemma models (like gemma-4-26b-a4b-it) have smaller context windows (typically 8K tokens)")
        print("compared to Gemini models (1M+ tokens). Running in Full Context Mode (passing the entire paper)")
        print("is highly likely to exceed Gemma's context window limit and cause it to hang or fail.")
        print("-> It is strongly recommended to run Gemma models in '--lite' mode.")
        print("Continuing in 5 seconds...")
        await asyncio.sleep(5)

    is_gemini = "gemma" not in model_name.lower()

    # --------------------------------------------------
    # Step 1: Scout / Searcher Phase
    # --------------------------------------------------
    if not state.paper_url:
        print(f"[*] Querying arXiv database for: '{state.user_query}'...")
        scout_schema = CandidatePapersList if is_gemini else None
        scout_agent = get_scout_agent(model, schema=scout_schema, app_data_dir=os.path.abspath("output"))
        async with scout_agent:
            import datetime
            current_date = datetime.datetime.now().strftime("%Y-%m-%d")
            schema_str = json.dumps(CandidatePapersList.model_json_schema(), indent=2)
            scout_prompt = (
                f"Search and list papers for this query: '{state.user_query}'.\n"
                f"Today's date is: {current_date} (reference date for any relative date calculation).\n"
                f"You MUST format your final response as a JSON object matching this schema:\n{schema_str}"
            )
            response = await scout_agent.chat(scout_prompt)
            
            candidates_data = await parse_structured_output(response, CandidatePapersList, "Scout Agent")
            
            if not candidates_data or not candidates_data.candidates:
                raise ValueError(f"No research papers found for the query: '{state.user_query}'")
            
            state.candidates = candidates_data.candidates
            # Select the top candidate automatically
            state.selected_paper = state.candidates[0]
            state.paper_url = state.selected_paper.url
            print(f"[+] Found paper candidate: '{state.selected_paper.title}'")
            print(f"[+] Download link: {state.paper_url}")
            
        if lite:
            print("[*] Cooling down for 12 seconds to respect API rate limits...")
            await asyncio.sleep(12)
    else:
        print(f"[*] Direct paper URL provided: {state.paper_url}")

    # --------------------------------------------------
    # Step 2: Download and Parse PDF Text
    # --------------------------------------------------
    print("[*] Retrieving and extracting text from PDF...")
    if "arxiv.org/abs/" in state.paper_url:
        state.paper_url = state.paper_url.replace("arxiv.org/abs/", "arxiv.org/pdf/") + ".pdf"
        
    if not state.selected_paper:
        url_path = state.paper_url.split("?")[0]
        filename = os.path.basename(url_path)
        if filename.endswith(".pdf"):
            filename = filename[:-4]
        if not filename:
            filename = "paper"
            
        state.selected_paper = CandidatePaper(
            title=filename,
            url=state.paper_url,
            authors=[],
            published="",
            abstract=""
        )

    folder_name = state.selected_paper.get_folder_name()
    paper_dir = os.path.join("output", folder_name)
    os.makedirs(paper_dir, exist_ok=True)
    
    raw_text_path = os.path.join(paper_dir, "raw_text.txt")
    extracted_text = download_and_parse_pdf(state.paper_url, save_text_path=raw_text_path)
    state.extracted_text = extracted_text
    
    # Store text in global tool state for Critic fact-checking fallback
    set_active_paper_text(extracted_text)

    # --------------------------------------------------
    # Step 3 & 4: Detail Extraction & Technical Glossary (Analyst & Concept Explainer Agents)
    # --------------------------------------------------
    text_slice = extracted_text[:40000] if lite else extracted_text
    
    print("[*] Analyzing paper content and extracting core facts & generating concept cards...")
    analyst_schema = PaperFacts if is_gemini else None
    explainer_schema = ConceptCardsList if is_gemini else None
    
    abs_paper_dir = os.path.abspath(paper_dir)
    analyst_agent = get_analyst_agent(model, schema=analyst_schema, app_data_dir=abs_paper_dir)
    explainer_agent = get_explainer_agent(model, schema=explainer_schema, app_data_dir=abs_paper_dir)
    
    async with analyst_agent, explainer_agent:
        schema_str_analyst = json.dumps(PaperFacts.model_json_schema(), indent=2)
        analyst_prompt = (
            f"Analyze the following paper content and extract key scientific facts.\n"
            f"You MUST format your final response as a JSON object matching this schema:\n{schema_str_analyst}\n\n"
            f"Paper Content:\n{text_slice}"
        )
        
        schema_str_explainer = json.dumps(ConceptCardsList.model_json_schema(), indent=2)
        explainer_prompt = (
            f"Scan the paper text and explain 3 to 5 key complex terms or math constructs.\n"
            f"You MUST format your final response as a JSON object matching this schema:\n{schema_str_explainer}\n\n"
            f"Paper Content:\n{text_slice}"
        )
        
        # Run chat calls concurrently
        analyst_task = analyst_agent.chat(analyst_prompt)
        explainer_task = explainer_agent.chat(explainer_prompt)
        
        print("    [->] Running Analyst and Explainer agents concurrently...")
        analyst_response, explainer_response = await asyncio.gather(analyst_task, explainer_task)
        
        # Parse outputs
        facts = await parse_structured_output(analyst_response, PaperFacts, "Analyst Agent")
        state.extracted_facts = facts
        
        cards_list = await parse_structured_output(explainer_response, ConceptCardsList, "Explainer Agent")
        state.concept_cards = cards_list.cards if cards_list.cards else []
        
        novel_count = len(facts.novel_contributions) if facts.novel_contributions else 0
        methodology_count = len(facts.methodology_steps) if facts.methodology_steps else 0
        print(f"[+] Extracted {novel_count} novel contributions and {methodology_count} methodology steps.")
        print(f"[+] Generated {len(state.concept_cards)} concept explanation cards.")

    if lite:
        print("[*] Cooling down for 12 seconds to respect API rate limits...")
        await asyncio.sleep(12)

    # --------------------------------------------------
    # Step 5: Draft & Critique Loop
    # --------------------------------------------------
    print("\n--------------------------------------------------")
    print("✍️  Starting Drafting & Critique Revision Loop")
    print("--------------------------------------------------")
    
    abs_paper_dir = os.path.abspath(paper_dir)
    summarizer_agent = get_summarizer_agent(model, app_data_dir=abs_paper_dir)
    deep_dive_agent = get_deep_dive_agent(model, app_data_dir=abs_paper_dir)
    
    critic_schema = CritiqueResult if is_gemini else None
    critic_agent = get_critic_agent(model, schema=critic_schema, app_data_dir=abs_paper_dir)
    
    feedback_context = "This is the initial draft. No feedback yet."
    max_iterations = 3
    
    async with summarizer_agent, deep_dive_agent, critic_agent:
        while state.iteration_count < max_iterations:
            state.iteration_count += 1
            print(f"\n[*] Iteration {state.iteration_count}/{max_iterations}:")
            
            # A. Prepare Prompts (injecting text_slice for higher quality drafts)
            facts_json = state.extracted_facts.model_dump_json() if state.extracted_facts else "{}"
            sum_prompt = (
                f"Write a highly clear, easy-to-understand, and engaging summary of the research paper (Artifact 1).\n\n"
                f"Use these extracted core facts to guide your writing:\n{facts_json}\n\n"
                f"Here is the text of the paper to draw deep context and explanations from:\n{text_slice}\n\n"
                f"Critic feedback to address (if any):\n{feedback_context}"
            )
            
            cards_str = "\n".join([f"- {c.concept}: {c.explanation} (Analogy: {c.analogy})" for c in state.concept_cards])
            dive_prompt = (
                f"Write an educational technical deep-dive explanation of the research paper (Artifact 2).\n\n"
                f"Explain these prerequisite concepts inside your explanation:\n{cards_str}\n\n"
                f"Use these extracted core facts to guide your technical analysis:\n{facts_json}\n\n"
                f"Here is the text of the paper containing the actual formulas, details, and context:\n{text_slice}\n\n"
                f"Critic feedback to address (if any):\n{feedback_context}"
            )
            
            # B. Run Drafting concurrently
            print("    [->] Drafting high-level summary and technical deep dive concurrently...")
            sum_task = summarizer_agent.chat(sum_prompt)
            dive_task = deep_dive_agent.chat(dive_prompt)
            
            sum_response, dive_response = await asyncio.gather(sum_task, dive_task)
            
            await log_agent_thoughts(sum_response, "Summarizer Agent", debug, model)
            await log_agent_thoughts(dive_response, "Deep-Dive Agent", debug, model)
            
            state.summary_draft = await sum_response.text()
            state.deep_dive_draft = await dive_response.text()
            
            if lite:
                print("    [*] Cooling down for 12 seconds to respect API rate limits...")
                await asyncio.sleep(12)
            
            # C. Critique
            print("    [->] Double-checking drafts for accuracy (Critic)...")
            schema_str = json.dumps(CritiqueResult.model_json_schema(), indent=2)
            schema_inst = f"You MUST format your final response as a JSON object matching this schema:\n{schema_str}\n\n"
            if lite:
                critic_prompt = (
                    f"Review the draft summary and deep-dive for accuracy. Compare them directly with the paper text below (truncated to fit context).\n"
                    f"Use your 'search_paper_text' tool only if you need to look up facts not found in the text below.\n\n"
                    f"{schema_inst}"
                    f"--- ORIGINAL PAPER TEXT (TRUNCATED) ---\n{text_slice}\n\n"
                    f"--- DRAFT SUMMARY ---\n{state.summary_draft}\n\n"
                    f"--- DRAFT DEEP DIVE ---\n{state.deep_dive_draft}"
                )
            else:
                critic_prompt = (
                    f"Review the draft summary and deep-dive for accuracy. Compare it directly with the original paper text below.\n\n"
                    f"{schema_inst}"
                    f"--- ORIGINAL PAPER TEXT ---\n{extracted_text}\n\n"
                    f"--- DRAFT SUMMARY ---\n{state.summary_draft}\n\n"
                    f"--- DRAFT DEEP DIVE ---\n{state.deep_dive_draft}"
                )
                
            critic_response = await critic_agent.chat(critic_prompt)
            
            critique = await parse_structured_output(response=critic_response, model_class=CritiqueResult, agent_name="Critic Agent")
            state.critic_critique = critique
            
            is_approved = critique.approved if critique.approved is not None else True
            
            if is_approved:
                print("    [+] Critic Approved the drafts! No hallucinations found.")
                break
            else:
                hallucinations = critique.hallucinations_found if critique.hallucinations_found else []
                corrections = critique.corrections_required if critique.corrections_required else "Fix errors."
                
                print("    [!] Critic Rejected the drafts.")
                print(f"    [!] Hallucinations found: {hallucinations}")
                print(f"    [!] Required corrections: {corrections}")
                feedback_context = (
                    f"Draft was REJECTED. Please correct the following issues:\n"
                    f"Hallucinations detected: {hallucinations}\n"
                    f"Feedback: {corrections}"
                )
                
                if lite:
                    print("    [*] Cooling down for 12 seconds to respect API rate limits...")
                    await asyncio.sleep(12)

    print("\n==================================================")
    print("🎉 Hypatia Workflow Completed Successfully!")
    print("==================================================")
    return state
