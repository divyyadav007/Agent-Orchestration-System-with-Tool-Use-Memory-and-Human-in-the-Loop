# Agent Orchestration System (AOS)

A stateful multi-agent LLM orchestration framework built on **LangGraph** featuring supervisor planning, autonomous specialist execution, double-loop quality review, hybrid memory, and human-in-the-loop escalation.

---

## Overview

The **Agent Orchestration System (AOS)** coordinates specialized AI agents using a directed cyclic graph state machine. 

### What Problem It Solves
Single LLMs often struggle with complex, multi-step requests, hallucinations, or executing tasks without verification. AOS solves this by breaking user requests down into dependency-ordered subtasks, executing them through targeted specialists, scoring outputs with an automated reviewer agent, and escalating persistent failures to a human operator.

### Who Should Use It
Developers, researchers, and AI engineers building stateful multi-agent applications that require structured planning, tool usage, quality control, and human oversight.

---

## Features

- **Stateful Supervisor Planner**: Decomposes natural language requests into structured JSON execution plans with subtask IDs, specialist assignments, and dependency chains.
- **Specialist Agent Network**:
  - 🔍 **Research Specialist**: Generates targeted search queries and searches the live web via Tavily API.
  - ✍️ **Writing Specialist**: Synthesizes research into professional briefs, reports, and markdown summaries.
  - 📊 **Data Specialist**: Processes text-based calculations, formatting, and transformations.
  - 💻 **Code Specialist**: Handles workspace file operations and text persistence.
- **Automated Double-Loop Quality Verification**: Reviewer agent scores specialist outputs (0.0 to 1.0) against task requirements; outputs scoring below 0.7 are automatically returned for retry with actionable feedback.
- **Human-in-the-Loop (HITL) Escalation**: Uses LangGraph interrupts to pause execution when subtasks fail review multiple times, exposing state to the Streamlit UI dashboard for human approval or rejection.
- **Hybrid Memory Architecture**:
  - **Short-Term Memory**: Caches in-progress state graphs in Redis (with automatic in-memory dictionary fallback).
  - **Long-Term Memory**: Semantically indexes completed tasks in ChromaDB to supply historical context to the supervisor planner.
- **Execution Trace Visualizer**: Captures step durations, token usage counts, and tool calls in a hierarchical console tree layout.

---

## Architecture Overview

The system processes incoming requests through a directed graph consisting of planning, selection, specialist execution, review, and escalation nodes:

```mermaid
graph TD
    User([User Request]) --> Supervisor[Supervisor Planner]
    LongMemory[(ChromaDB Long-Term Memory)] <--> |Semantic Context| Supervisor
    Supervisor --> |Structured Plan| Validation{Plan Validation}
    Validation -->|Errors & Retries < 3| Supervisor
    Validation -->|Valid Plan| Selector[Selector Node]
    
    Selector --> |Active Subtask| SpecialistRouter{Specialist Router}
    
    SpecialistRouter --> |Research Task| ResearchAgent[Research Specialist]
    SpecialistRouter --> |Writing Task| WritingAgent[Writing Specialist]
    SpecialistRouter --> |Data Task| DataAgent[Data Specialist]
    SpecialistRouter --> |Code Task| CodeAgent[Code Specialist]
    
    ResearchAgent --> Reviewer[Reviewer Agent]
    WritingAgent --> Reviewer
    DataAgent --> Reviewer
    CodeAgent --> Reviewer
    
    Reviewer --> |Score >= 0.7 (Pass)| Selector
    Reviewer --> |Score < 0.7 & Retries < 2| SpecialistRouter
    Reviewer --> |Score < 0.7 & Retries >= 2| Escalation[Escalation Node]
    
    Escalation --> |Yield Interrupt| StreamlitUI[Streamlit UI Dashboard]
    StreamlitUI --> |Approve / Reject| Selector
    
    Selector --> |All Subtasks Complete| End([Workflow Complete])
```

---

## Tech Stack

- **Languages**: Python 3.10+ (Core orchestration & multi-agent system logic)
- **Frameworks**: 
  - **LangGraph**: Directed cyclic graph state machine & checkpointing engine
  - **LangChain**: LLM client bindings, message structures, and prompt templates
  - **Streamlit**: Web-based dashboard frontend
- **AI / ML**: 
  - **Groq API / OpenAI API**: Fast LLM inference gateway (`llama-3.1-8b-instant`, `gpt-oss-120b`)
  - **Sentence Transformers**: `all-MiniLM-L6-v2` for ChromaDB vector embeddings
- **Database / Storage**: 
  - **ChromaDB**: Persistent vector database for long-term memory semantic indexing
  - **Redis**: Key-value cache for short-term state snapshots
  - **SQLite**: `agent_checkpoints.db` database for LangGraph state persistence
- **Tools & Infrastructure**:
  - **Tavily API**: LLM-optimized web search engine
  - **Docker & Docker Compose**: Service containerization infrastructure

---

## Folder Structure

```text
Multi-Agent-Orchestration-System/
├── frontend/
│   └── review-ui/
│       └── app.py              # Streamlit web dashboard interface
├── src/
│   ├── core/
│   │   ├── specialists/        # Specialist agent implementations (Research, Writing, Data, Code)
│   │   ├── graph.py            # StateGraph builder and router logic
│   │   ├── human_loop.py       # Human-in-the-loop escalation node
│   │   ├── models.py           # Pydantic data models (SubTask, ExecutionPlan)
│   │   ├── reviewer.py         # Automated quality reviewer node
│   │   ├── selector.py         # Subtask dependency router node
│   │   ├── state.py            # Global WorkflowState schema
│   │   └── supervisor.py       # Supervisor task planner node
│   ├── memory/
│   │   ├── long_term.py        # ChromaDB vector store interface
│   │   ├── manager.py          # Memory orchestrator facade
│   │   └── short_term.py       # Redis state store with local fallback
│   ├── observability/
│   │   └── tracer.py           # Hierarchical execution tracer
│   ├── tools/
│   │   ├── file_io.py          # Workspace file saving tool
│   │   ├── registry.py        # Central tool registry engine
│   │   └── web_search.py       # Tavily search tool implementation
│   └── utils/
│       └── llm.py              # LLM client setup and rate-limit backoff handler
├── tests/                      # Unit and integration test suite
├── docker-compose.yml          # Container configuration for Redis service
├── Dockerfile                  # Container image build file
└── requirements.txt            # Python dependencies manifest
```

---

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/divyyadav007/Agent-Orchestration-System-with-Tool-Use-Memory-and-Human-in-the-Loop.git
cd Agent-Orchestration-System-with-Tool-Use-Memory-and-Human-in-the-Loop
```

### 2. Create Virtual Environment
```bash
python -m venv myvenv
# On Windows (PowerShell):
.\myvenv\Scripts\Activate.ps1
# On Linux/macOS:
source myvenv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env` and populate your API credentials:
```bash
cp .env.example .env
```

### 5. Run Web Interface
```bash
python -m streamlit run frontend/review-ui/app.py
```
Open your browser and navigate to `http://localhost:8501`.

### 6. Run Services via Docker (Optional)
To launch the Redis cache service or containerized stack:
```bash
docker-compose up -d
```

---

## Environment Variables

| Variable | Description | Required |
| :--- | :--- | :---: |
| `GROQ_API_KEY` | API key for Groq LLM inference gateway access | Yes |
| `TAVILY_API_KEY` | API key for Tavily web search tool execution | Yes |
| `LLM_MODEL` | LLM model identifier string (e.g., `llama-3.1-8b-instant`) | No |
| `CHROMA_DB_PATH` | Local disk directory path for ChromaDB vector store (default: `./chroma_data`) | No |
| `REDIS_URL` | Connection URL for Redis short-term cache (default: `redis://localhost:6379/0`) | No |
| `REDIS_TTL` | Time-to-live in seconds for short-term state keys (default: `3600`) | No |

---

## Usage

1. Launch the Streamlit dashboard by running:
   ```bash
   python -m streamlit run frontend/review-ui/app.py
   ```
2. Enter a Thread ID in the sidebar (e.g., `dashboard_run_1`) to isolate run state and checkpoints.
3. Enter your request prompt into the main text box (e.g., *"Research recent AI regulations, write a 200-word executive summary, and save it to a text file"*).
4. Click **`🚀 Run Agent`**.
5. Monitor real-time execution in the UI:
   - **Plan Timeline**: Shows subtasks, assigned specialists, and completion status.
   - **Output Logs**: Displays outputs generated by specialists and reviewer scores.
   - **Trace Terminal**: Renders hierarchical execution spans and token usage metrics.
6. **Human Approval Flow**: If a task fails review 2+ times, the UI presents an escalation card prompting you to **Approve** or **Reject** the subtask.

---

## Screenshots

<!-- Screenshot Placeholders -->
![Main Dashboard Overview](docs/screenshots/dashboard_overview.png)
*Figure 1: Streamlit User Dashboard and Configuration Sidebar.*

![Execution Plan Timeline](docs/screenshots/execution_plan.png)
*Figure 2: Real-time Subtask Execution Timeline and Reviewer Scores.*

![Human-in-the-Loop Escalation](docs/screenshots/human_escalation.png)
*Figure 3: Human-in-the-Loop Approval Interface for Escalated Subtasks.*

---

## Future Improvements

- Add support for alternative search providers (e.g., DuckDuckGo, Serper API).
- Implement multi-modal specialist agents (e.g., vision analysis and chart generation).
- Expose a FastAPI REST API server for programmatic headless graph execution.
- Expand parallel subtask execution for independent graph branches.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.