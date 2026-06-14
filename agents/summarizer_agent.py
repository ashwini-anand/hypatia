from google.antigravity import Agent, LocalAgentConfig
from typing import Optional

def get_summarizer_agent(model: Optional[str] = None) -> Agent:
    """Configures and instantiates the Summarizer Agent.
    
    Args:
        model: Optional model override. If None, uses SDK default.
    """
    config_args = {
        "system_instructions": (
            "You are Hypatia's Summarizer Agent, an expert science journalist.\n"
            "Your task is to write a highly clear, easy-to-understand, and engaging summary (Artifact 1) "
            "of a research paper based on the structured facts extracted by the Analyst Agent.\n\n"
            "Formatting & Content Guidelines:\n"
            "- Write in clean, professional Markdown.\n"
            "- Focus on answering three fundamental questions clearly: 'What is this paper about?', 'Why is it important?', and 'What did the authors accomplish/find?'.\n"
            "- Use bold terms, bullet points, and short paragraphs to make it highly scannable.\n"
            "- Incorporate feedback from the Critic Agent if this is a revision loop, specifically fixing any flagged issues."
        )
    }
    if model:
        config_args["model"] = model
        
    config = LocalAgentConfig(**config_args)
    return Agent(config=config)
