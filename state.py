import pydantic
from typing import Optional, List, Dict, Any
import re
import json
import asyncio

class CandidatePaper(pydantic.BaseModel):
    title: str
    url: str
    authors: List[str]
    published: str
    abstract: str

    def get_folder_name(self) -> str:
        s = re.sub(r'[^a-zA-Z0-9\s\-_]', '', self.title)
        s = re.sub(r'[\s\-_]+', '_', s)
        return s.strip('_').lower()

class CandidatePapersList(pydantic.BaseModel):
    candidates: List[CandidatePaper] = pydantic.Field(description="List of candidate papers found matching the query.")

class PaperFacts(pydantic.BaseModel):
    novel_contributions: List[str] = pydantic.Field(description="The novel contributions of this paper compared to previous works.")
    key_findings: List[str] = pydantic.Field(description="The primary experimental results and key findings of the paper.")
    baselines_compared: List[str] = pydantic.Field(description="The control groups, reference standards, or comparative baselines the paper compared its results against.")
    datasets_used: List[str] = pydantic.Field(description="The specific benchmarks, datasets, samples, or experimental environments used.")
    methodology_steps: List[str] = pydantic.Field(description="A step-by-step breakdown of the proposed algorithm, framework, or mathematical method.")
    mathematical_proofs: List[str] = pydantic.Field(default_factory=list, description="Exact algebraic formulas, equations, lattice-theoretic properties, and logical operators (e.g., S subset T, relational algebra).")
    architectural_limitations: List[str] = pydantic.Field(default_factory=list, description="Deep edge-cases, physical limitations, complexity class boundaries (e.g., PTIME constraints, closed-world obstacles).")
    technical_implementation_details: List[str] = pydantic.Field(default_factory=list, description="Specific compiler toolchains, state management hacks, dataflow maps, or concrete programmatic workarounds mentioned.")

class ConceptCard(pydantic.BaseModel):
    concept: str = pydantic.Field(description="The technical or scientific concept name.")
    explanation: str = pydantic.Field(description="A clear, plain-english explanation of what this concept is.")
    analogy: str = pydantic.Field(description="A real-world analogy to make the concept click instantly for a beginner.")

class ConceptCardsList(pydantic.BaseModel):
    cards: List[ConceptCard] = pydantic.Field(description="List of concept explanations.")

class CritiqueResult(pydantic.BaseModel):
    approved: bool = pydantic.Field(description="Set to True if the drafts are accurate and free of hallucinations, False otherwise.")
    hallucinations_found: List[str] = pydantic.Field(description="List of any facts, metrics, or claims in the drafts that are incorrect or not supported by the paper.")
    corrections_required: str = pydantic.Field(description="Detailed instructions explaining what the writer needs to fix in the next iteration.")

class MemoryMapNode(pydantic.BaseModel):
    id: str
    level: int
    parent_id: Optional[str] = None
    child_ids: List[str] = []
    raw_text: str
    embedding: Optional[List[float]] = None

class HierarchicalMemoryMap(pydantic.BaseModel):
    nodes: Dict[str, MemoryMapNode] = pydantic.Field(default_factory=dict)
    
    async def save_checkpoint_async(self, filepath: str):
        # Synchronous deep copy to immunize against concurrent agent mutations (dirty writes)
        snapshot = self.model_copy(deep=True)
        payload = snapshot.model_dump_json(indent=2)
        
        loop = asyncio.get_event_loop()
        def write_file():
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(payload)
        await loop.run_in_executor(None, write_file)

class DocumentSection(pydantic.BaseModel):
    section: str = pydantic.Field(description="The section title or heading.")
    summary: str = pydantic.Field(description="A brief 1-2 sentence summary of what this section contains.")

class DocumentOutline(pydantic.BaseModel):
    title: str = pydantic.Field(description="The overall title of the document.")
    outline: List[DocumentSection] = pydantic.Field(description="The ordered list of sections forming the table of contents.")

class ResearchState(pydantic.BaseModel):
    user_query: Optional[str] = None
    paper_url: Optional[str] = None
    candidates: List[CandidatePaper] = []
    selected_paper: Optional[CandidatePaper] = None
    extracted_text: Optional[str] = None
    document_outline: Optional[DocumentOutline] = None
    extracted_facts: Optional[PaperFacts] = None
    concept_cards: List[ConceptCard] = []
    summary_draft: Optional[str] = None
    deep_dive_draft: Optional[str] = None
    critic_critique: Optional[CritiqueResult] = None
    iteration_count: int = 0
    # The decoupled State-Externalizing Harness
    memory_map: HierarchicalMemoryMap = pydantic.Field(default_factory=HierarchicalMemoryMap)
