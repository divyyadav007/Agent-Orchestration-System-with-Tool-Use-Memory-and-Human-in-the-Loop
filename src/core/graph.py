import logging
from typing import Any, Dict

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.core.human_loop import escalation_node
from src.core.reviewer import reviewer_node
from src.core.selector import SPECIALIST_NODE_MAP, selector_node
from src.core.specialists.nodes import code_node, data_node, research_node, writing_node
from src.core.state import WorkflowState
from src.core.supervisor import supervisor_node, validation_node

logger = logging.getLogger(__name__)


def build_graph(checkpointer: Any = None) -> CompiledStateGraph:
    """Constructs and compiles the stateful LangGraph multi-agent orchestration workflow.

    Why StateGraph: LangGraph manages complex cyclic agent execution as a state machine.
    Checkpointers (like SqliteSaver) persist graph state across steps and allow
    pausing for human approval (interrupts).
    """
    logger.info("Initializing multi-agent StateGraph structure.")
    builder = StateGraph(WorkflowState)

    # 1. Register Graph Nodes
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("validate", validation_node)
    builder.add_node("selector", selector_node)
    builder.add_node("research_specialist", research_node)
    builder.add_node("writing_specialist", writing_node)
    builder.add_node("code_specialist", code_node)
    builder.add_node("data_specialist", data_node)
    builder.add_node("reviewer", reviewer_node)
    builder.add_node("escalation", escalation_node)

    # 2. Define Entry Point & Planning Edges
    builder.set_entry_point("supervisor")
    builder.add_edge("supervisor", "validate")

    def after_validate(state: WorkflowState) -> str:
        """Route to selector if plan is valid or max retries reached; retry supervisor if invalid."""
        errors = state.get("validation_errors")
        retry_count = state.get("retry_count", 0)

        if errors and retry_count < 3:
            logger.info(f"Routing back to supervisor (validation retry {retry_count}).")
            return "supervisor"
        return "selector"

    builder.add_conditional_edges("validate", after_validate, {"supervisor": "supervisor", "selector": "selector"})

    def after_selector(state: WorkflowState) -> str:
        """Route to the specialist assigned to the active subtask, or END if all subtasks complete."""
        task_id = state.get("current_task_id")
        if task_id is None:
            logger.info("No remaining tasks. Routing to END.")
            return END

        assigned = state.get("current_task_assigned_to", "")
        target_node = SPECIALIST_NODE_MAP.get(assigned, END)
        logger.info(f"Routing subtask '{task_id}' to '{target_node}'.")
        return target_node

    builder.add_conditional_edges(
        "selector",
        after_selector,
        {
            "research_specialist": "research_specialist",
            "writing_specialist": "writing_specialist",
            "code_specialist": "code_specialist",
            "data_specialist": "data_specialist",
            END: END,
        },
    )

    # Connect Specialists to Quality Reviewer
    builder.add_edge("research_specialist", "reviewer")
    builder.add_edge("writing_specialist", "reviewer")
    builder.add_edge("code_specialist", "reviewer")
    builder.add_edge("data_specialist", "reviewer")

    def after_reviewer(state: WorkflowState) -> str:
        """Route back to selector if task passed review, retry specialist if failed, or escalate if retried >= 2 times."""
        task_id = state.get("current_task_id")
        if task_id is None:
            logger.info("Task passed review. Routing back to selector.")
            return "selector"

        retry_count = state.get("current_task_retry_count", 0)
        if retry_count >= 2:
            logger.warning(f"Task '{task_id}' failed {retry_count} times. Escalating to human loop.")
            return "escalation"

        assigned = state.get("current_task_assigned_to", "")
        target_node = SPECIALIST_NODE_MAP.get(assigned, END)
        logger.info(f"Task '{task_id}' failed review. Retrying on specialist '{target_node}'.")
        return target_node

    builder.add_conditional_edges(
        "reviewer",
        after_reviewer,
        {
            "research_specialist": "research_specialist",
            "writing_specialist": "writing_specialist",
            "code_specialist": "code_specialist",
            "data_specialist": "data_specialist",
            "selector": "selector",
            "escalation": "escalation",
            END: END,
        },
    )

    # Loop escalation back to selector after human decision is applied
    builder.add_edge("escalation", "selector")

    logger.info("Compiling StateGraph with checkpointer.")
    return builder.compile(checkpointer=checkpointer)
