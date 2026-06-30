import logging
from typing import Dict, Any
from src.core.state import WorkflowState
from src.core.specialists.research import ResearchSpecialist
from src.core.specialists.writing import WritingSpecialist
from src.core.specialists.code import CodeSpecialist
from src.core.specialists.data import DataSpecialist
from src.core.specialists.base import SpecialistBase

# Initialize module logger
logger = logging.getLogger(__name__)

# Global instances of specialist agents
research_specialist: ResearchSpecialist = ResearchSpecialist()
writing_specialist: WritingSpecialist = WritingSpecialist()
code_specialist: CodeSpecialist = CodeSpecialist()
data_specialist: DataSpecialist = DataSpecialist()

def specialist_node(state: WorkflowState, specialist: SpecialistBase) -> Dict[str, Any]:
    """Generic orchestrator wrapper node that routes workflow state details to a specialist.

    Args:
        state (WorkflowState): Current global graph state.
        specialist (SpecialistBase): The active specialist agent instance to invoke.

    Returns:
        Dict[str, Any]: State updates with the specialist's raw text response
            and appended assistant messages.
    """
    task_id = state.get("current_task_id")
    task_desc = state.get("current_task_description")
    
    if not task_id or not task_desc:
        logger.warning(f"Specialist wrapper node executed but task_id='{task_id}' or description is empty.")
        return {}
    
    # Ingest verification feedback comments if returning from a previous failed review attempt
    feedback = state.get("review_feedback")
    if feedback:
        enhanced_task_desc = (
            f"{task_desc}\n\n"
            f"[Feedback from previous review attempt: {feedback}]\n"
            f"Please refine and improve your previous results based on this feedback."
        )
        logger.info(f"Specialist '{specialist.name}' executing task '{task_id}' with retry review feedback.")
        feedback_return = {"review_feedback": None}
    else:
        enhanced_task_desc = task_desc
        logger.info(f"Specialist '{specialist.name}' executing task '{task_id}'.")
        feedback_return = {}
    
    plan = state["plan"]
    if not plan:
        logger.error("Specialist wrapper node: Execution plan missing from state.")
        return {}
        
    current_subtask = next(st for st in plan.subtasks if st.id == task_id)
    completed = state.get("completed_tasks", {})
    
    # Gather output data values from prerequisite parent subtasks
    previous_outputs = {
        dep_id: completed[dep_id]["output"]
        for dep_id in current_subtask.dependencies
        if dep_id in completed
    }
    logger.debug(f"Specialist '{specialist.name}' gathered {len(previous_outputs)} dependency output inputs.")
    
    result = specialist.execute_task(task_description=enhanced_task_desc, previous_outputs=previous_outputs)
    
    return {
        "current_task_output": result,
        "messages": [{"role": "assistant", "content": result}],
        **feedback_return
    }

# Specific specialist node bindings used by the StateGraph configuration
def research_node(state: WorkflowState) -> Dict[str, Any]:
    """Graph node executor for the ResearchSpecialist agent."""
    return specialist_node(state, research_specialist)

def writing_node(state: WorkflowState) -> Dict[str, Any]:
    """Graph node executor for the WritingSpecialist agent."""
    return specialist_node(state, writing_specialist)

def code_node(state: WorkflowState) -> Dict[str, Any]:
    """Graph node executor for the CodeSpecialist agent."""
    return specialist_node(state, code_specialist)  

def data_node(state: WorkflowState) -> Dict[str, Any]:
    """Graph node executor for the DataSpecialist agent."""
    return specialist_node(state, data_specialist)