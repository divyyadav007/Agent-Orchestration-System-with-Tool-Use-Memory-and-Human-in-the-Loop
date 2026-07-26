from typing import List

from pydantic import BaseModel, Field


class SubTask(BaseModel):
    """Data model representing a single subtask within an execution plan."""

    id: str = Field(..., description="Unique identifier for the subtask (e.g., '1', '2a')")
    description: str = Field(..., description="Detailed description of what needs to be performed")
    assigned_to: str = Field(..., description="Specialist type required: 'research', 'data', 'writing', or 'code'")
    dependencies: List[str] = Field(
        default_factory=list, description="List of subtask IDs that must be successfully completed before this subtask starts"
    )
    expected_output_type: str = Field(
        ..., description="Expected format/type of the output, e.g., 'list of URLs', 'dataframe', 'text summary', 'code output'"
    )


class ExecutionPlan(BaseModel):
    """Data model representing the overall goal and structured plan of execution."""

    overall_goal: str = Field(..., description="A clear restatement of the overall goal of the user request")
    subtasks: List[SubTask] = Field(..., description="List of subtasks that make up the complete plan")
    critical_path: List[str] = Field(..., description="Ordered list of sequential bottleneck subtask IDs")
