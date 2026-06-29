from typing import Dict, Any
from src.core.state import WorkflowState
from src.core.specialists.research import ResearchSpecialist
from src.core.specialists.writing import WritingSpecialist
from src.core.specialists.code import CodeSpecialist
from src.core.specialists.data import DataSpecialist
from src.core.specialists.base import SpecialistBase


research_specialist = ResearchSpecialist()
writing_specialist = WritingSpecialist()
code_specialist = CodeSpecialist()
data_specialist = DataSpecialist()

def specialist_node(state: WorkflowState, specialist) -> dict:
    task_id = state["current_task_id"]
    task_desc = state["current_task_description"]
    if not task_id or not task_desc:
        return {}
    
    # If there is feedback from previous attempt, incorporate it
    feedback = state.get("review_feedback")
    if feedback:
        enhanced_task_desc = f"{task_desc}\n\n[Feedback from previous attempt: {feedback}]\nPlease improve based on this feedback."
        # Clear feedback so it's not used again
        feedback_return = {"review_feedback": None}
    else:
        enhanced_task_desc = task_desc
        feedback_return = {}
    
    plan = state["plan"]
    current_subtask = next(st for st in plan.subtasks if st.id == task_id)
    completed = state.get("completed_tasks", {})
    previous_outputs = {
        dep_id: completed[dep_id]["output"]
        for dep_id in current_subtask.dependencies
        if dep_id in completed
    }
    
    result = specialist.execute_task(task_description=enhanced_task_desc, previous_outputs=previous_outputs)
    
    return {
        "current_task_output": result,
        "messages": [{"role": "assistant", "content": result}],
        **feedback_return
    }

# Specific node functions that bind the specialist
def research_node(state: WorkflowState) -> dict:
    return specialist_node(state, research_specialist)

def writing_node(state: WorkflowState) -> dict:
    return specialist_node(state, writing_specialist)

def code_node(state: WorkflowState) -> dict:
    return specialist_node(state, code_specialist)  

def data_node(state: WorkflowState) -> dict:
    return specialist_node(state, data_specialist)