# Agent Orchestration System (AOS)

Hey everyone! 👋 Welcome to my fourth-year engineering project: the **Agent Orchestration System (AOS)**. 

## What is this?
AOS is a stateful multi-agent AI framework built using **LangGraph**. Think of it as a smart, autonomous manager that takes a big, complex problem, breaks it down into smaller manageable tasks, and hands them off to specialized AI "workers". If the workers mess up, an AI "reviewer" checks their work. If they keep messing up, the system pauses and asks a human (you!) for help.

## Why I Built This 💡
While playing around with standard LLMs, I noticed they often struggle with complex, multi-step requests. They hallucinate, lose track of the goal, or just confidently give the wrong answer. Single-prompt AI isn't enough for real-world tasks. 

I built AOS to solve this by introducing **planning, specialized roles, quality control, and human oversight**. It mimics how a real engineering team works!

## Key Features 🚀
- **The Supervisor**: A boss AI that creates an execution plan, figures out dependencies, and assigns tasks to the right agents.
- **Specialist Workers**: 
  - 🔍 **Research Agent**: Surfs the web using the Tavily API to find relevant, up-to-date information.
  - ✍️ **Writing Agent**: Synthesizes information and writes clean, structured reports or markdown files.
  - 📊 **Data Agent**: Crunches numbers, processes text, and formats data.
  - 💻 **Code Agent**: Saves outputs to files directly in the workspace.
- **Automated AI Reviewer**: Double-checks the work and gives it a score (out of 1.0). Passes good work, sends back bad work for a retry with actionable feedback.
- **Human-in-the-Loop (HITL)**: If an agent fails a task too many times, the system pauses. It exposes the current state to a nice web dashboard and asks you to approve or reject the work.
- **Memory System**: Remembers past tasks using ChromaDB (long-term semantic memory) and Redis (short-term cache). This means it gets smarter and has better context over time.

## How It Works Under the Hood ⚙️
1. **User Request**: You type in a complex task.
2. **Planning**: The Supervisor breaks it down into a JSON plan.
3. **Execution**: The LangGraph state machine routes each subtask to the correct Specialist Agent.
4. **Review**: The output is sent to the Reviewer. If it fails, it retries.
5. **Escalation**: If it fails repeatedly, the graph interrupts and waits for your approval on the UI.
6. **Completion**: Once all subtasks are done, the final result is presented to you!

## Tech Stack 🛠️
- **Language**: Python 3.10+
- **Core Frameworks**: LangGraph (for the state machine) & LangChain
- **Frontend UI**: Streamlit (for the human-in-the-loop dashboard)
- **AI Models**: Groq API / OpenAI
- **Databases**: ChromaDB (Vector DB), Redis (Caching), SQLite (State checkpoints)

## How to Run It 💻

### 1. Clone & Setup
```bash
git clone https://github.com/divyyadav007/Multi-Agent-Orchestration-System.git
cd Multi-Agent-Orchestration-System

# Create a virtual environment
python -m venv myvenv

# Activate it
# Windows:
.\myvenv\Scripts\Activate.ps1
# Mac/Linux:
source myvenv/bin/activate

# Install the required packages
pip install -r requirements.txt
```

### 2. Environment Variables
Copy the `.env.example` file to `.env` and add your API keys:
```bash
cp .env.example .env
```
*(You'll need at least `GROQ_API_KEY` and `TAVILY_API_KEY`)*

### 3. Start the Web Dashboard
```bash
python -m streamlit run frontend/review-ui/app.py
```
Then just open `http://localhost:8501` in your browser!

*(Optional) Start Redis using Docker if you want short-term caching:*
```bash
docker-compose up -d
```

## How to Use It 🎮
1. Open the Streamlit dashboard in your browser.
2. Enter a Thread ID on the sidebar (e.g., `run_1`) so it knows where to save checkpoints.
3. Type a request (e.g., *"Research latest AI news and write a summary"*).
4. Hit **Run Agent** and watch the magic happen! You'll see the plan timeline, the agent logs, and the review scores in real-time.
5. If an agent gets stuck or fails a review 2+ times, the UI will pause and ask you to step in and approve/reject.

## What's Next? (Future Scope) 🌱
- Adding more specialized agents (like a Vision Agent for charts/images).
- Supporting other search tools like DuckDuckGo or Serper API.
- Turning it into a headless REST API with FastAPI so other apps can easily plug into it.

Enjoy! Feel free to explore the code in the `src/` folder to see how multi-agent systems work under the hood.

## License
MIT License