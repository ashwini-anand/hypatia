import pydantic
from typing import Optional, List, Dict, Any

import re

class CandidatePaper(pydantic.BaseModel):
    title: str
    url: str
    authors: List[str]
    published: str
    abstract: str

    def get_folder_name(self) -> str:
        # Sanitize name: alphanumeric, spaces, hyphens, underscores only
        s = re.sub(r'[^a-zA-Z0-9\s\-_]', '', self.title)
        s = re.sub(r'[\s\-_]+', '_', s)
        return s.strip('_').lower()

class CandidatePapersList(pydantic.BaseModel):
    candidates: List[CandidatePaper] = pydantic.Field(description="List of candidate papers found matching the query.")

class PaperFacts(pydantic.BaseModel):
    novel_contributions: List[str] = pydantic.Field(description="The novel contributions of this paper compared to previous works.")
    key_findings: List[str] = pydantic.Field(description="The primary experimental results and key findings of the paper.")
    baselines_compared: List[str] = pydantic.Field(description="The baseline models or methodologies the paper compared its results against.")
    datasets_used: List[str] = pydantic.Field(description="The specific benchmarks, datasets, or experimental environments used.")
    methodology_steps: List[str] = pydantic.Field(description="A step-by-step breakdown of the proposed algorithm, framework, or mathematical method.")

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

class ResearchState(pydantic.BaseModel):
    user_query: Optional[str] = None
    paper_url: Optional[str] = None
    candidates: List[CandidatePaper] = []
    selected_paper: Optional[CandidatePaper] = None
    extracted_text: Optional[str] = None
    extracted_facts: Optional[PaperFacts] = None
    concept_cards: List[ConceptCard] = []
    summary_draft: Optional[str] = None
    deep_dive_draft: Optional[str] = None
    critic_critique: Optional[CritiqueResult] = None
    iteration_count: int = 0
