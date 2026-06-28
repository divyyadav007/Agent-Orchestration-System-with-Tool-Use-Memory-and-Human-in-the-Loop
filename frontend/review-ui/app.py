
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import streamlit as st
import sqlite3
import json
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.errors import GraphInterrupt
from src.core.graph import build_graph
from src.core.state import WorkflowState
from src.observability.tracer import GraphTracer
from src.tools import registry

st.set_page_config(page_title="Agent Dashboard", layout="wide")
st.title("🤖 Agent Orchestration System")
st.markdown("Multi‑agent system with Supervisor, Specialists, Reviewer & Human‑in‑the‑Loop")

# ---------- Sidebar ----------
with st.sidebar:
    st.header("Configuration")
    thread_id = st.text_input("Thread ID", value="dashboard_run_1", help="Unique run identifier for checkpointing.")
    st.write("Memory & Tracer included automatically.")
    st.write("---")
    st.write("Model: Groq / Mistral (from .env)")

# ---------- Main area ----------
user_request = st.text_area("Enter your request:", 
    value="I need a summary of recent news about AI regulations, then write a 200-word brief for my CEO, and save it to a file.",
    height=100)

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    run_btn = st.button("🚀 Run Agent", type="primary")
with col2:
    reset_btn = st.button("🔄 Reset State")

# ---------- Session state init ----------
if "graph_built" not in st.session_state:
    conn = sqlite3.connect("agent_checkpoints.db", check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    st.session_state.checkpointer = checkpointer
    st.session_state.app = build_graph(checkpointer=checkpointer)
    st.session_state.graph_built = True

if "tracer" not in st.session_state:
    st.session_state.tracer = GraphTracer()
    registry.set_tracer(st.session_state.tracer)

if "current_config" not in st.session_state:
    st.session_state.current_config = None

if "final_state" not in st.session_state:
    st.session_state.final_state = None

if "plan" not in st.session_state:
    st.session_state.plan = None

if "completed_tasks" not in st.session_state:
    st.session_state.completed_tasks = {}

if "human_required" not in st.session_state:
    st.session_state.human_required = False

if "paused_state" not in st.session_state:
    st.session_state.paused_state = None

# ---------- Reset ----------
if reset_btn:
    st.session_state.tracer.reset()
    st.session_state.final_state = None
    st.session_state.plan = None
    st.session_state.completed_tasks = {}
    st.session_state.human_required = False
    st.session_state.paused_state = None
    st.experimental_rerun()

# ---------- Run Graph ----------
if run_btn and user_request.strip():
    initial_state = {
        "messages": [],
        "user_request": user_request,
        "plan": None,
        "validation_errors": None,
        "retry_count": 0,
        "completed_tasks": {},
        "current_task_id": None,
        "current_task_description": None,
        "current_task_assigned_to": None,
        "current_task_output": None,
        "review_feedback": None,
        "current_task_retry_count": 0,
        "awaiting_human": False,
        "escalation_reason": None,
        "human_decision": None,
        "human_feedback": None
    }

    config = {"configurable": {"thread_id": thread_id}, "callbacks": [st.session_state.tracer]}
    st.session_state.current_config = config

    try:
        # Use stream to show progress
        with st.spinner("🔄 Running agent workflow..."):
            final_state = st.session_state.app.invoke(initial_state, config)  # invoke easier for display
            # Alternatively, you can stream and show intermediate states.
        st.session_state.final_state = final_state
        st.session_state.plan = final_state.get("plan")
        st.session_state.completed_tasks = final_state.get("completed_tasks", {})
        st.session_state.human_required = final_state.get("awaiting_human", False)
        st.success("✅ Workflow completed!")
    except GraphInterrupt:
        st.warning("⏸️ Graph paused for human input. Please review below.")
        # The state is already saved in checkpointer; fetch it.
        checkpoint = st.session_state.checkpointer.get(config)
        if checkpoint:
            st.session_state.paused_state = checkpoint
            st.session_state.human_required = True
            st.session_state.final_state = checkpoint  # so we can show progress

# ---------- Human decision section (if paused) ----------
if st.session_state.human_required and st.session_state.paused_state:
    state = st.session_state.paused_state
    st.header("🛑 Human Approval Required")
    st.write(f"**Escalation Reason:** {state.get('escalation_reason','N/A')}")
    st.write(f"**Task ID:** {state.get('current_task_id','')}")
    st.write(f"**Task Description:** {state.get('current_task_description','')}")
    st.text_area("Current Output:", value=state.get("current_task_output",""), height=200, disabled=True)

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("✅ Approve"):
            # Update state with decision
            state["human_decision"] = "approve"
            st.session_state.checkpointer.put(st.session_state.current_config, state)
            # Resume graph
            app = st.session_state.app
            config = st.session_state.current_config
            try:
                resumed_state = app.invoke(None, config)
                st.session_state.final_state = resumed_state
                st.session_state.completed_tasks = resumed_state.get("completed_tasks", {})
                st.session_state.human_required = False
                st.success("Approved and workflow resumed.")
            except Exception as e:
                st.error(f"Resume error: {e}")
    with col_b:
        if st.button("❌ Reject"):
            state["human_decision"] = "reject"
            st.session_state.checkpointer.put(st.session_state.current_config, state)
            app = st.session_state.app
            config = st.session_state.current_config
            try:
                resumed_state = app.invoke(None, config)
                st.session_state.final_state = resumed_state
                st.session_state.completed_tasks = resumed_state.get("completed_tasks", {})
                st.session_state.human_required = False
                st.success("Rejected and workflow resumed.")
            except Exception as e:
                st.error(f"Resume error: {e}")

# ---------- Show results ----------
if st.session_state.plan:
    st.subheader("📋 Execution Plan")
    plan = st.session_state.plan
    st.write(f"**Overall Goal:** {plan.overall_goal}")
    for task in plan.subtasks:
        st.markdown(f"- **{task.id}**: {task.description} → *{task.assigned_to}* (deps: {task.dependencies})")
    st.write(f"**Critical Path:** {plan.critical_path}")

if st.session_state.completed_tasks:
    st.subheader("✅ Completed Tasks")
    for task_id, task_data in st.session_state.completed_tasks.items():
        with st.expander(f"Task {task_id}: {task_data.get('assigned_to','unknown')} (score: {task_data.get('review_score','N/A')})"):
            st.text_area("Output", value=task_data.get("output",""), height=150, disabled=True)

    # Check if we have a file output (maybe from task that saved file)
    # For demo, show the latest task output that mentions file save.
    # Or attempt to read CEO_brief.txt if exists.
    import os
    if os.path.exists("CEO_brief.txt"):
        with open("CEO_brief.txt", "r") as f:
            content = f.read()
        st.subheader("📄 Generated File Content (CEO_brief.txt)")
        st.code(content, language="text")
    elif os.path.exists("ai_regulations_brief.txt"):
        with open("ai_regulations_brief.txt", "r") as f:
            content = f.read()
        st.code(content, language="text")

# ---------- Tracer tree ----------
if st.session_state.tracer and st.session_state.tracer.root.children:
    st.subheader("🔍 Execution Trace")
    from rich.console import Console
    from rich.tree import Tree
    console = Console()
    tree = st.session_state.tracer.get_tree()
    # Capture rich tree as string
    with console.capture() as capture:
        console.print(tree)
    trace_str = capture.get()
    st.text_area("Trace", value=trace_str, height=400, disabled=True)

# ---------- Helper: Reset tracer after run? Not needed. ----------