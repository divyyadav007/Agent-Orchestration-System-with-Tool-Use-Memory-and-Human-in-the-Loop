from langgraph.graph import StateGraph, END
from src.core.state import WorkflowState
from src.core.supervisor import supervisor_node, validation_node
from src.core.selector import selector_node
from src.core.reviewer import reviewer_node
from src.core.specialists.nodes import research_node, writing_node, code_node
from src.core.human_loop import escalation_node

SPECIALIST_NODE_MAP = {
    "research": "research_specialist",
    "data": "data_specialist",
    "writing": "writing_specialist",
    "code": "code_specialist"
}

def build_graph(checkpointer=None):
    builder = StateGraph(WorkflowState)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("validate", validation_node)
    builder.add_node("selector", selector_node)
    builder.add_node("research_specialist", research_node)
    builder.add_node("writing_specialist", writing_node)
    builder.add_node("code_specialist", code_node)
    builder.add_node("reviewer", reviewer_node)
    builder.add_node("escalation", escalation_node)

    builder.set_entry_point("supervisor")
    builder.add_edge("supervisor", "validate")

    def after_validate(state: WorkflowState) -> str:
        if state["validation_errors"] is not None and state.get("retry_count", 0) < 3:
            return "supervisor"
        return "selector"

    builder.add_conditional_edges("validate", after_validate, {
        "supervisor": "supervisor",
        "selector": "selector"
    })

    def after_selector(state: WorkflowState) -> str:
        task_id = state.get("current_task_id")
        if task_id is None:
            return END
        assigned = state["current_task_assigned_to"]
        return SPECIALIST_NODE_MAP.get(assigned, END)

    builder.add_conditional_edges("selector", after_selector, {
        "research_specialist": "research_specialist",
        "writing_specialist": "writing_specialist",
        "code_specialist": "code_specialist",
        END: END
    })

    builder.add_edge("research_specialist", "reviewer")
    builder.add_edge("writing_specialist", "reviewer")
    builder.add_edge("code_specialist", "reviewer")

    def after_reviewer(state: WorkflowState) -> str:
        task_id = state.get("current_task_id")
        if task_id is None:
            return "selector"
        retry_count = state.get("current_task_retry_count", 0)
        if retry_count >= 2:
            return "escalation"
        assigned = state["current_task_assigned_to"]
        return SPECIALIST_NODE_MAP.get(assigned, END)

    builder.add_conditional_edges("reviewer", after_reviewer, {
        "research_specialist": "research_specialist",
        "writing_specialist": "writing_specialist",
        "code_specialist": "code_specialist",
        "selector": "selector",
        "escalation": "escalation",
        END: END
    })

    builder.add_edge("escalation", "selector")
    return builder.compile(checkpointer=checkpointer)