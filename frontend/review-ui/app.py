import streamlit as st
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

st.set_page_config(page_title="Human Review", layout="wide")
st.title("🛑 Human-in-the-Loop Review")

conn = sqlite3.connect("agent_checkpoints.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)

# Get latest state
threads = checkpointer.list(config={})
for thread in threads:
    state = checkpointer.get(thread.config)
    if state and state.get("awaiting_human"):
        st.header(f"Task: {state['current_task_id']}")
        st.write("**Escalation Reason:**", state.get("escalation_reason"))
        st.write("**Task Description:**", state.get("current_task_description"))
        st.text_area("Current Output:", state.get("current_task_output", ""), height=200)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("✅ Approve"):
                # Update state with human decision
                state["human_decision"] = "approve"
                checkpointer.put(thread.config, state)
                st.success("Approved!")
        with col2:
            if st.button("❌ Reject"):
                state["human_decision"] = "reject"
                checkpointer.put(thread.config, state)
                st.error("Rejected!")
        with col3:
            feedback = st.text_area("Feedback for retry:")
            if st.button("🔄 Modify & Retry"):
                state["human_decision"] = "modify"
                state["human_feedback"] = feedback
                checkpointer.put(thread.config, state)
                st.info("Sent for retry!")