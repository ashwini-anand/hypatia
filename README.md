# Hypatia: Multi-Agent Scientific Literature Assistant

> **Disclaimer**: This is a personal project. The views, code, and opinions expressed are my own and do not represent those of my current or past employers.

---

Hypatia is a Python-based multi-agent application designed to search, parse, summarize, and explain academic literature. Powered by the **Google Antigravity SDK** and Gemini models, Hypatia converts research PDFs or search queries into text summaries and technical deep dives.

---

## 1. System Architecture

Hypatia is structured around a **Coordinator-Specialist (Orchestrator-Workers)** multi-agent topology. Rather than relying on a single prompt to parse, write, and verify, Hypatia coordinates a team of **6 specialized worker agents** and dedicated processing tools, using a Python-based asynchronous workflow engine to verify factual consistency and readability.

```mermaid
graph TD
    User([User Request]) --> Engine[Workflow Orchestrator Engine]
    Engine -->|Route request| Route{Link or Query?}
    
    Route -->|Query| Searcher[Searcher Agent]
    Searcher -->|arXiv API| Searcher
    Searcher -->|URL & Metadata| Engine
    
    Route -->|URL| Parser[PDF Parser Tool]
    Engine -->|URL| Parser
    Parser -->|PyMuPDF| Parser
    Parser -->|Raw Text| Engine
    
    Engine --> Analyst[Analyst Agent]
    Analyst -->|JSON facts| Engine
    
    Engine --> Summarizer[Summarizer Agent]
    Engine --> DeepDive[Deep-Dive Agent]
    Engine --> Explainer[Concept Explainer Agent]
    
    Summarizer -->|Summary Draft| Critic[Critic Agent]
    DeepDive -->|Deep Dive Draft| Critic
    Explainer -->|Glossaries| Critic
    
    Critic -->|search_paper_text tool| PaperText[(Raw Paper Text)]
    Critic -->|Critique JSON| Engine
    
    Engine -->|Loop if rejected| Summarizer
    Engine -->|Deliver final MD & HTML| User
```

### System Components

#### Orchestration & Parsing Tools
1.  **Workflow Orchestrator Engine (Python Code)**: The central asynchronous coordinator (`workflow.py`). It manages execution states, runs independent agents in parallel streams using `asyncio.gather`, and implements the critique-and-revision feedback loops.
2.  **PDF Parser Tool**: A python module (`tools/parser.py`) that downloads research PDFs and extracts raw page text cleanly using PyMuPDF.

#### The 6 Specialized Worker Agents
1.  **Searcher (Scout Agent)**: Uses the arXiv API to translate natural language queries into academic paper candidate links, abstracts, and metadata.
2.  **Analyst (Analyst Agent)**: Parses raw paper text to extract core, atomic facts (novelty, comparative standards, key metrics, methodology steps) into structured JSON.
3.  **Concept Explainer (Explainer Agent)**: Extracts complex scientific terms and creates plain-English definitions, analogies, and limitations for each.
4.  **Summarizer (Summarizer Agent)**: Synthesizes paper details into a highly scannable, direct, and structured high-level summary (Artifact 1).
5.  **Deep-Dive Writer (Deep-Dive Agent)**: Drafts a comprehensive technical document (Artifact 2) explaining equations, core mechanisms, experimental configurations, and implementation realities.
6.  **Critic (Peer Reviewer)**: Fact-checks drafts against the original paper text using local RAG keyword searches. Rejects drafts containing factual inconsistencies or omissions, passing detailed correction feedback to the writing agents.

---

## 2. Local Setup & Installation

Follow these steps to configure your local Python environment and run Hypatia.

### Prerequisites
*   **Python:** Version 3.10 or higher.
*   **Gemini API Key:** Required to connect to Gemini models. Obtain a key from [Google AI Studio](https://aistudio.google.com/app/api-keys).

### Installation
We recommend using **`uv`**, a Python package manager, to manage your virtual environment:

1.  Clone the repository and navigate to the project root:
    ```bash
    cd hypatia
    ```
2.  Create a virtual environment:
    ```bash
    uv venv
    ```
3.  Install the dependencies:
    ```bash
    uv pip install -r requirements.txt
    ```

### Environment Setup
Create a `.env` file in the root directory and add your Gemini API Key:
```env
GEMINI_API_KEY="your-gemini-api-key"
```

---

## 3. Running Hypatia

Hypatia provides two execution modes depending on your API key type and rate-limit allocations:

### Mode A: Full Context Mode (Default)
By default, Hypatia runs in **Full Context Mode**. It processes the full text of the research paper in every agent prompt. This requires a standard Gemini API key with sufficient rate limits.
```bash
.venv/bin/python main.py
```

### Mode B: Lite Mode (Token-Saving)
If you are running on a restricted **Gemini Free Tier** key, pass the `--lite` flag. This limits context length to 40,000 characters and switches the Critic agent to RAG mode to reduce input tokens. It also introduces a 12-second sleep cooldown between agent calls to respect rate limits.
```bash
.venv/bin/python main.py --lite
```

### Option C: Custom Model Selection
By default, Hypatia uses `gemini-3.5-flash`. You can specify a different model directly using the `--model` flag.

For example, to run with `gemini-3.5-pro` in lite mode:
```bash
.venv/bin/python main.py --lite --model gemini-3.5-pro
```

To run with `gemma-4-26b-a4b-it` (which should use `--lite` mode due to smaller context limits) with debug logging enabled:
```bash
.venv/bin/python main.py --lite --model gemma-4-26b-a4b-it --debug
```

### Option D: Real-time Debug Mode
To stream the internal reasoning steps (thoughts) of all agents in real-time to the console, append the `--debug` flag:
```bash
.venv/bin/python main.py --debug
.venv/bin/python main.py --lite --debug
```

### Example Inputs

When prompted by the CLI, you can load a paper using either a query or a direct URL:

*   **Option 1: Search Query**
    *   `Explain the most influential paper in database in last one month duration.`
*   **Option 2: Direct URL**
    *   `https://arxiv.org/pdf/1901.01930` (direct PDF link)

---

## 4. System Outputs

Once execution completes, Hypatia compiles both markdown drafts and styled HTML documents into the `output/` directory:

```text
output/<paper_name>/
├── raw_text.txt       # Clean parsed raw text of the paper PDF
├── summary.md         # High-level summary (Artifact 1)
├── summary.html       # Interactively styled HTML summary with dark/light theme
├── deep_dive.md       # In-depth technical guide (Artifact 2)
└── deep_dive.html     # Interactively styled HTML deep-dive with dark/light theme and live Mermaid rendering
```

The HTML files are rendered using a responsive CSS design system with standard typography, custom code block formatting, and live Mermaid.js diagram drawing.