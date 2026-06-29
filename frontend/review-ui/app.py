
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

# Custom CSS for rich professional aesthetics
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

/* Force Outfit font globally */
html, body, [class*="css"], .stMarkdown {
    font-family: 'Outfit', sans-serif !important;
}

h1, h2, h3 {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 700 !important;
}

h1 {
    background: linear-gradient(135deg, #a78bfa, #3b82f6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 2.8em !important;
    padding-bottom: 0.1em;
}

/* Timeline/stepper cards for plan */
.timeline-container {
    padding: 10px 0;
}
.timeline-card {
    border-left: 3px solid rgba(59, 130, 246, 0.4);
    padding-left: 20px;
    margin-left: 10px;
    margin-bottom: 20px;
    position: relative;
    transition: all 0.3s ease;
}
.timeline-card:hover {
    border-left: 3px solid #3b82f6;
    background-color: rgba(59, 130, 246, 0.03);
}
.timeline-card::before {
    content: '';
    position: absolute;
    width: 12px;
    height: 12px;
    background-color: #3b82f6;
    border-radius: 50%;
    left: -8px;
    top: 5px;
    box-shadow: 0 0 8px #3b82f6;
}

/* Badge pills */
.badge {
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 0.8em;
    font-weight: 600;
    text-transform: uppercase;
    display: inline-block;
    margin-bottom: 8px;
}
.badge-research { background-color: rgba(59, 130, 246, 0.15) !important; color: #3b82f6 !important; border: 1px solid rgba(59, 130, 246, 0.3); }
.badge-writing { background-color: rgba(167, 139, 250, 0.15) !important; color: #a78bfa !important; border: 1px solid rgba(167, 139, 250, 0.3); }
.badge-code { background-color: rgba(249, 115, 22, 0.15) !important; color: #f97316 !important; border: 1px solid rgba(249, 115, 22, 0.3); }
.badge-data { background-color: rgba(16, 185, 129, 0.15) !important; color: #10b981 !important; border: 1px solid rgba(16, 185, 129, 0.3); }
.badge-unknown { background-color: rgba(100, 116, 139, 0.15) !important; color: #64748b !important; border: 1px solid rgba(100, 116, 139, 0.3); }

/* Custom trace card */
.trace-terminal {
    font-family: 'JetBrains Mono', monospace !important;
    background-color: #0b0f19;
    border: 1px solid #1e293b;
    border-left: 4px solid #8b5cf6;
    border-radius: 8px;
    padding: 18px;
    color: #cbd5e1;
    max-height: 450px;
    overflow-y: auto;
    white-space: pre-wrap;
    box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.8);
    font-size: 0.9em;
    line-height: 1.4;
}
</style>
""", unsafe_allow_html=True)

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

# ---------- Load active state from database on startup ----------
if st.session_state.plan is None and st.session_state.final_state is None:
    config = {"configurable": {"thread_id": thread_id}}
    st.session_state.current_config = config
    try:
        state_snapshot = st.session_state.app.get_state(config)
        if state_snapshot and state_snapshot.values:
            st.session_state.plan = state_snapshot.values.get("plan")
            st.session_state.completed_tasks = state_snapshot.values.get("completed_tasks", {})
            
            # Check if currently paused/interrupted
            if state_snapshot.next:
                interrupt_payload = {}
                if state_snapshot.tasks and state_snapshot.tasks[0].interrupts:
                    interrupt_payload = state_snapshot.tasks[0].interrupts[0].value
                
                st.session_state.paused_state = dict(state_snapshot.values)
                if isinstance(interrupt_payload, dict):
                    st.session_state.paused_state['escalation_reason'] = interrupt_payload.get("escalation_reason", "N/A")
                
                st.session_state.human_required = True
            else:
                st.session_state.human_required = False
                st.session_state.final_state = state_snapshot.values
    except Exception as e:
        pass

# ---------- Reset ----------
if reset_btn:
    st.session_state.tracer.reset()
    st.session_state.final_state = None
    st.session_state.plan = None
    st.session_state.completed_tasks = {}
    st.session_state.human_required = False
    st.session_state.paused_state = None
    
    try:
        conn = sqlite3.connect("agent_checkpoints.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
        cursor.execute("DELETE FROM writes WHERE thread_id = ?", (thread_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Error clearing database: {e}")
        
    st.rerun()

# ---------- Run Graph ----------
if run_btn and user_request.strip():
    try:
        conn = sqlite3.connect("agent_checkpoints.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
        cursor.execute("DELETE FROM writes WHERE thread_id = ?", (thread_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        st.warning(f"Warning clearing database: {e}")

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
            
        state_snapshot = st.session_state.app.get_state(config)
        if state_snapshot and state_snapshot.next:
            interrupt_payload = {}
            if state_snapshot.tasks and state_snapshot.tasks[0].interrupts:
                interrupt_payload = state_snapshot.tasks[0].interrupts[0].value
            
            st.session_state.paused_state = dict(state_snapshot.values)
            if isinstance(interrupt_payload, dict):
                st.session_state.paused_state['escalation_reason'] = interrupt_payload.get("escalation_reason", "N/A")
            
            st.session_state.human_required = True
            st.session_state.final_state = state_snapshot.values
            st.session_state.plan = state_snapshot.values.get("plan")
            st.session_state.completed_tasks = state_snapshot.values.get("completed_tasks", {})
            st.rerun()
        else:
            st.session_state.final_state = final_state
            st.session_state.plan = final_state.get("plan")
            st.session_state.completed_tasks = final_state.get("completed_tasks", {})
            st.session_state.human_required = False
            st.success("✅ Workflow completed!")
            st.rerun()
    except GraphInterrupt:
        state_snapshot = st.session_state.app.get_state(config)
        if state_snapshot and state_snapshot.next:
            interrupt_payload = {}
            if state_snapshot.tasks and state_snapshot.tasks[0].interrupts:
                interrupt_payload = state_snapshot.tasks[0].interrupts[0].value
            
            st.session_state.paused_state = dict(state_snapshot.values)
            if isinstance(interrupt_payload, dict):
                st.session_state.paused_state['escalation_reason'] = interrupt_payload.get("escalation_reason", "N/A")
            
            st.session_state.human_required = True
            st.session_state.final_state = state_snapshot.values
            st.session_state.plan = state_snapshot.values.get("plan")
            st.session_state.completed_tasks = state_snapshot.values.get("completed_tasks", {})
            st.rerun()
    except Exception as e:
        st.error(f"Error during workflow execution: {e}")

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
            app = st.session_state.app
            config = st.session_state.current_config
            try:
                # Update state using LangGraph API
                app.update_state(config, {"human_decision": "approve"})
                # Resume graph with spinner
                with st.spinner("🔄 Resuming workflow with approval..."):
                    resumed_state = app.invoke(None, config)
                
                state_snapshot = app.get_state(config)
                if state_snapshot and state_snapshot.next:
                    interrupt_payload = {}
                    if state_snapshot.tasks and state_snapshot.tasks[0].interrupts:
                        interrupt_payload = state_snapshot.tasks[0].interrupts[0].value
                    st.session_state.paused_state = dict(state_snapshot.values)
                    if isinstance(interrupt_payload, dict):
                        st.session_state.paused_state['escalation_reason'] = interrupt_payload.get("escalation_reason", "N/A")
                    st.session_state.human_required = True
                    st.session_state.final_state = state_snapshot.values
                    st.session_state.plan = state_snapshot.values.get("plan")
                    st.session_state.completed_tasks = state_snapshot.values.get("completed_tasks", {})
                    st.rerun()
                else:
                    st.session_state.final_state = resumed_state
                    st.session_state.plan = resumed_state.get("plan")
                    st.session_state.completed_tasks = resumed_state.get("completed_tasks", {})
                    st.session_state.human_required = False
                    st.success("Approved and workflow resumed.")
                    st.rerun()
            except GraphInterrupt:
                state_snapshot = app.get_state(config)
                if state_snapshot and state_snapshot.next:
                    interrupt_payload = {}
                    if state_snapshot.tasks and state_snapshot.tasks[0].interrupts:
                        interrupt_payload = state_snapshot.tasks[0].interrupts[0].value
                    st.session_state.paused_state = dict(state_snapshot.values)
                    if isinstance(interrupt_payload, dict):
                        st.session_state.paused_state['escalation_reason'] = interrupt_payload.get("escalation_reason", "N/A")
                    st.session_state.human_required = True
                    st.session_state.final_state = state_snapshot.values
                    st.session_state.plan = state_snapshot.values.get("plan")
                    st.session_state.completed_tasks = state_snapshot.values.get("completed_tasks", {})
                    st.rerun()
            except Exception as e:
                st.error(f"Resume error: {e}")
    with col_b:
        if st.button("❌ Reject"):
            app = st.session_state.app
            config = st.session_state.current_config
            try:
                # Update state using LangGraph API
                app.update_state(config, {"human_decision": "reject"})
                # Resume graph with spinner
                with st.spinner("🔄 Resuming workflow with rejection..."):
                    resumed_state = app.invoke(None, config)
                st.session_state.final_state = resumed_state
                st.session_state.plan = resumed_state.get("plan")
                st.session_state.completed_tasks = resumed_state.get("completed_tasks", {})
                st.session_state.human_required = False
                st.success("Rejected and workflow resumed.")
                st.rerun()
            except GraphInterrupt:
                state_snapshot = app.get_state(config)
                if state_snapshot and state_snapshot.next:
                    interrupt_payload = {}
                    if state_snapshot.tasks and state_snapshot.tasks[0].interrupts:
                        interrupt_payload = state_snapshot.tasks[0].interrupts[0].value
                    st.session_state.paused_state = dict(state_snapshot.values)
                    if isinstance(interrupt_payload, dict):
                        st.session_state.paused_state['escalation_reason'] = interrupt_payload.get("escalation_reason", "N/A")
                    st.session_state.human_required = True
                    st.session_state.final_state = state_snapshot.values
                    st.session_state.plan = state_snapshot.values.get("plan")
                    st.session_state.completed_tasks = state_snapshot.values.get("completed_tasks", {})
                    st.rerun()
            except Exception as e:
                st.error(f"Resume error: {e}")

# ---------- Show results ----------
if st.session_state.plan:
    st.subheader("📋 Execution Plan")
    plan = st.session_state.plan
    st.write(f"**Overall Goal:** {plan.overall_goal}")
    
    # Custom stepper rendering
    st.markdown('<div class="timeline-container">', unsafe_allow_html=True)
    for task in plan.subtasks:
        assigned = task.assigned_to
        badge_class = f"badge badge-{assigned}"
        deps_str = f"🔗 Dependencies: {task.dependencies}" if task.dependencies else "✅ Ready (No dependencies)"
        st.markdown(f"""
        <div class="timeline-card">
            <div class="{badge_class}">{assigned}</div>
            <div style="font-weight: 600; font-size: 1.1em; color: #f8fafc; margin-bottom: 4px;">Task {task.id}: {task.description}</div>
            <div style="font-size: 0.9em; color: #94a3b8; font-weight: 500;">
                {deps_str} &nbsp;|&nbsp; 📋 Expected: <i>{task.expected_output_type}</i>
            </div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.info(f"🛣️ **Critical Path:** {plan.critical_path}")

if st.session_state.completed_tasks:
    st.subheader("✅ Completed Tasks")
    for task_id, task_data in st.session_state.completed_tasks.items():
        assigned = task_data.get('assigned_to', 'unknown')
        score = task_data.get('review_score', 'N/A')
        with st.expander(f"Task {task_id}: {assigned.upper()} (Review Score: {score})"):
            badge_class = f"badge badge-{assigned}"
            st.markdown(f'<div class="{badge_class}">{assigned}</div>', unsafe_allow_html=True)
            st.text_area("Specialist Output", value=task_data.get("output", ""), height=180, disabled=True, key=f"output_task_{task_id}")

    # Check if we have a file output
    import os
    txt_files = [f for f in os.listdir(".") if f.endswith(".txt") and f != "requirements.txt"]
    if txt_files:
        st.subheader("📄 Generated File Contents")
        for txt_file in txt_files:
            try:
                with open(txt_file, "r", encoding="utf-8") as f:
                    content = f.read()
                with st.expander(f"File: {txt_file}", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button(
                            label=f"⬇️ Download TXT",
                            data=content,
                            file_name=txt_file,
                            mime="text/plain",
                            key=f"txt_{txt_file}"
                        )
                    with col2:
                        try:
                            from fpdf import FPDF
                            pdf = FPDF()
                            pdf.add_page()
                            pdf.set_font("Helvetica", size=11)
                            # Handle utf-8 characters encoding gracefully
                            pdf.multi_cell(0, 10, content.encode('latin-1', 'replace').decode('latin-1'))
                            pdf_bytes = bytes(pdf.output())
                            
                            st.download_button(
                                label=f"⬇️ Download PDF",
                                data=pdf_bytes,
                                file_name=txt_file.replace('.txt', '.pdf'),
                                mime="application/pdf",
                                key=f"pdf_{txt_file}"
                            )
                        except Exception as pdf_err:
                            st.error(f"Failed to generate PDF: {pdf_err}")
                    st.code(content, language="text")
            except Exception as e:
                st.error(f"Error reading {txt_file}: {e}")

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
    
    # Custom terminal-like tracing render
    st.markdown(f'<div class="trace-terminal">{trace_str}</div>', unsafe_allow_html=True)

# ---------- Helper: Reset tracer after run? Not needed. ----------