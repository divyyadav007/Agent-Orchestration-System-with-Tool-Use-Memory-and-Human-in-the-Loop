from pydantic import BaseModel, Field
from typing import List

class SubTask(BaseModel):
    id: str = Field(description="Unique identifier (e.g., '1', '2a')")
    description: str = Field(description="Detailed description of what to do")
    assigned_to: str = Field(description="Specialist type: research, data, writing, code")
    dependencies: List[str] = Field(default_factory=list, description="IDs of subtasks that must be completed before this")
    expected_output_type: str = Field(description="e.g., 'list of URLs', 'dataframe', 'text summary', 'code output'")

class ExecutionPlan(BaseModel):
    overall_goal: str = Field(description="Restated goal in clear terms")
    subtasks: List[SubTask] = Field(description="List of subtasks to execute")
    critical_path: List[str] = Field(description="Ordered list of subtask IDs that must be done sequentially")