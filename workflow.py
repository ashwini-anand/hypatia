import asyncio
import os
import json
import re
from state import ResearchState, CandidatePaper, CandidatePapersList, PaperFacts, ConceptCardsList, CritiqueResult, ConceptCard, HierarchicalMemoryMap, MemoryMapNode, DocumentOutline
from tools.parser import download_and_parse_pdf, chunk_and_embed
from tools.fact_checker import set_active_memory_map
from agents.scout_agent import get_scout_agent
from agents.analyst_agent import get_analyst_agent
from agents.explainer_agent import get_explainer_agent
from agents.summarizer_agent import get_summarizer_agent
from agents.deep_dive_agent import get_deep_dive_agent
from agents.critic_agent import get_critic_agent
from typing import Optional, Type
import pydantic

async def log_agent_thoughts(response, agent_name: str, debug: bool, model: Optional[str] = None):
    """Utility to print thoughts stream when debug is enabled."""
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
    """Safely extracts structured output. Fallback to regex text parsing."""
    try:
        structured_data = await response.structured_output()
        if structured_data is not None:
            return model_class(**structured_data)
    except Exception as e:
        pass

    raw_text = await response.text()
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
    """Orchestrates the research and drafting pipeline using specialized agents."""
    model_name = model or "gemini-3.5-flash"
    
    print("\n==================================================")
    print("🚀 Starting Hypatia Scientific Research Workflow")
    print(f"[🤖] Model: {model_name}")
    print("==================================================")

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
            state.selected_paper = state.candidates[0]
            state.paper_url = state.selected_paper.url
            print(f"[+] Found paper candidate: '{state.selected_paper.title}'")
            print(f"[+] Download link: {state.paper_url}")
    else:
        print(f"[*] Direct paper URL provided: {state.paper_url}")

    # --------------------------------------------------
    # Step 2: Download, Parse PDF, and Build Memory Map
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
            title=filename, url=state.paper_url, authors=[], published="", abstract=""
        )

    folder_name = state.selected_paper.get_folder_name()
    paper_dir = os.path.join("output", folder_name)
    os.makedirs(paper_dir, exist_ok=True)
    
    raw_text_path = os.path.join(paper_dir, "raw_text.txt")
    extracted_text = download_and_parse_pdf(state.paper_url, save_text_path=raw_text_path)
    state.extracted_text = extracted_text

    print("[*] Extracting Document Outline (Hybrid Payload)...")
    abs_paper_dir = os.path.abspath(paper_dir)
    outliner_agent = get_explainer_agent(model, schema=DocumentOutline if is_gemini else None, app_data_dir=abs_paper_dir)
    async with outliner_agent:
        schema_str_outline = json.dumps(DocumentOutline.model_json_schema(), indent=2)
        outline_prompt = (
            f"Scan the following research paper and extract its high-level Document Outline (Table of Contents).\n"
            f"For each section, provide a brief 1-2 sentence summary of its contents.\n"
            f"You MUST format your final response as a JSON object matching this schema:\n{schema_str_outline}\n\n"
            f"Paper Content:\n{extracted_text[:40000]}"
        )
        outline_response = await outliner_agent.chat(outline_prompt)
        state.document_outline = await parse_structured_output(outline_response, DocumentOutline, "Outliner Agent")
        if state.document_outline and state.document_outline.outline:
            print(f"    [+] Extracted outline with {len(state.document_outline.outline)} sections.")

    print("[*] Generating RAPTOR Chunks & Batch Embeddings...")
    chunks_data = chunk_and_embed(extracted_text)
    
    for i, c in enumerate(chunks_data):
        node_id = f"chunk_{i}"
        state.memory_map.nodes[node_id] = MemoryMapNode(
            id=node_id,
            level=0,
            raw_text=c["content"],
            embedding=c["embedding"]
        )
        
    # Store memory map globally for the Critic's paging tool
    set_active_memory_map(state.memory_map)
    await state.memory_map.save_checkpoint_async(os.path.join(paper_dir, "state.json"))

    # --------------------------------------------------
    # Step 3 & 4: Parallel Extraction & Consolidation
    # --------------------------------------------------
    print("[*] Running parallel Analyst ingestion and generating concept cards...")
    analyst_schema = PaperFacts if is_gemini else None
    explainer_schema = ConceptCardsList if is_gemini else None
    
    abs_paper_dir = os.path.abspath(paper_dir)
    analyst_agent = get_analyst_agent(model, schema=analyst_schema, app_data_dir=abs_paper_dir)
    explainer_agent = get_explainer_agent(model, schema=explainer_schema, app_data_dir=abs_paper_dir)
    
    async with analyst_agent, explainer_agent:
        schema_str_analyst = json.dumps(PaperFacts.model_json_schema(), indent=2)
        analyst_tasks = []
        
        sem = asyncio.Semaphore(2)
        
        async def run_analyst(node_id: str, raw_text: str, stagger_delay: float):
            await asyncio.sleep(stagger_delay)
            async with sem:
                analyst_prompt = (
                    f"Analyze the following paper chunk and extract key scientific facts.\n"
                    f"CRITICAL: Do not overly simplify mathematical formulas or system limitations. If you see formal algebra, lattice-theoretic properties, complexity constraints, or compiler toolchain names, extract them precisely into the appropriate schema fields.\n"
                    f"You MUST format your final response as a JSON object matching this schema:\n{schema_str_analyst}\n\n"
                    f"Paper Chunk ({node_id}):\n{raw_text}"
                )
                return await analyst_agent.chat(analyst_prompt)
        
        # Fan-out parallel parsing tasks for each chunk
        current_delay = 0.0
        for node_id, node in state.memory_map.nodes.items():
            if node.level == 0:
                analyst_tasks.append(run_analyst(node_id, node.raw_text, current_delay))
                current_delay += 2.0  # Stagger each request by 2 seconds to avoid 503 spikes
                
        schema_str_explainer = json.dumps(ConceptCardsList.model_json_schema(), indent=2)
        explainer_prompt = (
            f"Scan the paper text and explain 3 to 5 key complex terms or math constructs.\n"
            f"You MUST format your final response as a JSON object matching this schema:\n{schema_str_explainer}\n\n"
            f"Paper Content:\n{extracted_text[:40000]}"
        )
        explainer_task = explainer_agent.chat(explainer_prompt)
        
        print(f"    [->] Queued {len(analyst_tasks)} Analyst agents (staggered to avoid API spikes)...")
        results = await asyncio.gather(*analyst_tasks, explainer_task)
        
        analyst_responses = results[:-1]
        explainer_response = results[-1]
        
        print("    [->] Running Map-Reduce Consolidator...")
        all_facts_json = []
        for i, resp in enumerate(analyst_responses):
            facts_local = await parse_structured_output(resp, PaperFacts, f"Analyst Chunk {i}")
            all_facts_json.append(facts_local.model_dump_json())
            
        consolidator_prompt = (
            f"You are the Consolidator. Merge and deduplicate the following {len(all_facts_json)} local fact extractions into a single, highly dense summary.\n"
            f"Discard duplicate boilerplate. CRITICAL: You must preserve ALL exact mathematical equations, algebraic proofs, and edge-case limitations. Do not delete them during deduplication.\n"
            f"Format as JSON matching the PaperFacts schema:\n{schema_str_analyst}\n\n"
            + "\n".join(all_facts_json)
        )
        
        consolidator_response = await analyst_agent.chat(consolidator_prompt)
        consolidated_facts = await parse_structured_output(consolidator_response, PaperFacts, "Consolidator")
        state.extracted_facts = consolidated_facts
        
        # Save Level 2 Root node
        state.memory_map.nodes["root_facts"] = MemoryMapNode(
            id="root_facts",
            level=2,
            raw_text=consolidated_facts.model_dump_json()
        )
        
        cards_list = await parse_structured_output(explainer_response, ConceptCardsList, "Explainer Agent")
        state.concept_cards = cards_list.cards if cards_list.cards else []
        
        novel_count = len(consolidated_facts.novel_contributions) if consolidated_facts.novel_contributions else 0
        methodology_count = len(consolidated_facts.methodology_steps) if consolidated_facts.methodology_steps else 0
        print(f"[+] Consolidated {novel_count} novel contributions and {methodology_count} methodology steps.")
        print(f"[+] Generated {len(state.concept_cards)} concept explanation cards.")

    await state.memory_map.save_checkpoint_async(os.path.join(paper_dir, "state.json"))

    # --------------------------------------------------
    # Step 5: Draft & Critique Loop (Stateless Execution)
    # --------------------------------------------------
    print("\n--------------------------------------------------")
    print("✍️  Starting Drafting & Critique Revision Loop")
    print("--------------------------------------------------")
    
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
            
            # Agents receive ONLY compressed snapshots, not raw paper text
            facts_json = state.extracted_facts.model_dump_json() if state.extracted_facts else "{}"
            outline_json = state.document_outline.model_dump_json() if state.document_outline else "{}"
            
            sum_prompt = (
                f"Write a highly clear, easy-to-understand, and engaging summary of the research paper (Artifact 1).\n"
                f"Use this Document Outline as your structural roadmap:\n{outline_json}\n\n"
                f"Use these deduplicated core facts (Level 2 Snapshot) to guide your writing:\n{facts_json}\n\n"
                f"Critic feedback to address (if any):\n{feedback_context}"
            )
            
            cards_str = "\n".join([f"- {c.concept}: {c.explanation} (Analogy: {c.analogy})" for c in state.concept_cards])
            dive_prompt = (
                f"Write an advanced, production-grade architectural deep-dive of the research paper (Artifact 2).\n"
                f"Use this Document Outline as your structural roadmap:\n{outline_json}\n\n"
                f"Explain these prerequisite concepts inside your explanation:\n{cards_str}\n\n"
                f"Use these extracted core facts to guide your technical analysis:\n{facts_json}\n\n"
                f"Critic feedback to address (if any):\n{feedback_context}"
            )
            
            print("    [->] Drafting high-level summary and technical deep dive concurrently...")
            sum_task = summarizer_agent.chat(sum_prompt)
            dive_task = deep_dive_agent.chat(dive_prompt)
            
            sum_response, dive_response = await asyncio.gather(sum_task, dive_task)
            
            await log_agent_thoughts(sum_response, "Summarizer Agent", debug, model)
            await log_agent_thoughts(dive_response, "Deep-Dive Agent", debug, model)
            
            state.summary_draft = await sum_response.text()
            state.deep_dive_draft = await dive_response.text()
            
            print("    [->] Double-checking drafts for accuracy (Critic)...")
            schema_str = json.dumps(CritiqueResult.model_json_schema(), indent=2)
            schema_inst = f"You MUST format your final response as a JSON object matching this schema:\n{schema_str}\n\n"
            
            critic_prompt = (
                f"Review the draft summary and deep-dive for accuracy.\n"
                f"You DO NOT have the full paper in your context window. You MUST use your 'search_paper_text' tool to page in specific paragraphs to verify claims.\n\n"
                f"{schema_inst}"
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
        
        await state.memory_map.save_checkpoint_async(os.path.join(paper_dir, "state.json"))

    print("\n==================================================")
    print("🎉 Hypatia Workflow Completed Successfully!")
    print("==================================================")
    return state
