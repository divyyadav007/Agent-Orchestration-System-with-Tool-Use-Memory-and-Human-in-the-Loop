import logging
from typing import Dict, Any, Callable
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from src.core.state import WorkflowState
from src.core.supervisor import supervisor_node, validation_node
from src.core.selector import selector_node
from src.core.reviewer import reviewer_node
from src.core.specialists.nodes import research_node, writing_node, code_node, data_node
from src.core.human_loop import escalation_node

# Initialize module logger
logger = logging.getLogger(__name__)

# Mapping from supervisor specialists list to their respective node names in the graph
SPECIALIST_NODE_MAP: Dict[str, str] = {
    "research": "research_specialist",
    "data": "data_specialist",
    "writing": "writing_specialist",
    "code": "code_specialist"
}

def build_graph(checkpointer: Any = None) -> CompiledStateGraph:
    """Builds and compiles the multi-agent LangGraph workflow.

    Defines nodes, edges, conditional routing functions, and attaches 
    an optional persistence checkpointer.

    Args:
        checkpointer (Any): LangGraph checkpointer instance (e.g. SqliteSaver)
            for state persistence across pauses/interrupts.

    Returns:
        CompiledStateGraph: The compiled state graph workflow runnable.
    """
    logger.info("Initializing multi-agent StateGraph structure.")
    builder = StateGraph(WorkflowState)
    
    # Register graph nodes
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("validate", validation_node)
    builder.add_node("selector", selector_node)
    builder.add_node("research_specialist", research_node)
    builder.add_node("writing_specialist", writing_node)
    builder.add_node("code_specialist", code_node)
    builder.add_node("data_specialist", data_node)
    builder.add_node("reviewer", reviewer_node)
    builder.add_node("escalation", escalation_node)

    # Set entrypoint edge
    builder.set_entry_point("supervisor")
    builder.add_edge("supervisor", "validate")

    def after_validate(state: WorkflowState) -> str:
        """Determines routing following plan validation.

        If the plan has validation errors and has been attempted less than 3 times,
        routes back to the supervisor node; otherwise routes to the selector.
        """
        errors = state.get("validation_errors")
        retry_count = state.get("retry_count", 0)
        
        if errors is not None:
            if retry_count < 3:
                logger.info(f"Graph Routing: Plan has validation errors (retry {retry_count}). Routing back to supervisor.")
                return "supervisor"
            else:
                logger.warning("Graph Routing: Max plan validation retries reached. Routing to selector despite errors.")
                
        return "selector"

    builder.add_conditional_edges("validate", after_validate, {
        "supervisor": "supervisor",
        "selector": "selector"
    })

    def after_selector(state: WorkflowState) -> str:
        """Determines routing following subtask selection.

        Routes to the assigned specialist node or END if all tasks are complete.
        """
        task_id = state.get("current_task_id")
        if task_id is None:
            logger.info("Graph Routing: No further tasks to execute. Routing to END.")
            return END
            
        assigned = state.get("current_task_assigned_to", "")
        target_node = SPECIALIST_NODE_MAP.get(assigned, END)
        logger.info(f"Graph Routing: Routing task '{task_id}' to specialist node '{target_node}'.")
        return target_node

    builder.add_conditional_edges("selector", after_selector, {
        "research_specialist": "research_specialist",
        "writing_specialist": "writing_specialist",
        "code_specialist": "code_specialist",
        "data_specialist": "data_specialist",
        END: END
    })

    # Connect specialists to the reviewer node
    builder.add_edge("research_specialist", "reviewer")
    builder.add_edge("writing_specialist", "reviewer")
    builder.add_edge("code_specialist", "reviewer")
    builder.add_edge("data_specialist", "reviewer")

    def after_reviewer(state: WorkflowState) -> str:
        """Determines routing after verification review.

        If task passed, routes back to selector. If failed, routes back to the 
        assigned specialist for retry. Escalates if max retries are exceeded.
        """
        task_id = state.get("current_task_id")
        # If current_task_id was reset to None, it means the task was successful/passed
        if task_id is None:
            logger.info("Graph Routing: Task review passed. Routing back to selector.")
            return "selector"
            
        retry_count = state.get("current_task_retry_count", 0)
        if retry_count >= 2:
            logger.warning(f"Graph Routing: Task '{task_id}' failed review {retry_count} times. Escalating to human loop.")
            return "escalation"
            
        assigned = state.get("current_task_assigned_to", "")
        target_node = SPECIALIST_NODE_MAP.get(assigned, END)
        logger.info(f"Graph Routing: Task '{task_id}' failed review. Routing to specialist '{target_node}' for retry {retry_count+1}/2.")
        return target_node

    builder.add_conditional_edges("reviewer", after_reviewer, {
        "research_specialist": "research_specialist",
        "writing_specialist": "writing_specialist",
        "code_specialist": "code_specialist",
        "data_specialist": "data_specialist",
        "selector": "selector",
        "escalation": "escalation",
        END: END
    })

    # Loop escalation back to the selector for re-evaluation once human intervention is resolved
    builder.add_edge("escalation", "selector")
    
    logger.info("Compiling StateGraph with checkpointing capability.")
    return builder.compile(checkpointer=checkpointer)