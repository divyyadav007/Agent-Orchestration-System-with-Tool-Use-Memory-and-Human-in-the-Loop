import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.core.supervisor import supervisor_node
from src.utils.llm import get_llm

node = supervisor_node
if __name__ == "__main__":
    state = {"user_request": "I need a summary of recent news about AI regulations, then write a 200-word brief for my CEO, and save it to a file."}
    result = node(state)
    plan = result["plan"]
    print("Overall goal:", plan.overall_goal)
    for subtask in plan.subtasks:
        print(f"\nSubtask {subtask.id}: {subtask.description}")
        print(f"  Assigned to: {subtask.assigned_to}")
        print(f"  Dependencies: {subtask.dependencies}")
        print(f"  Expected output: {subtask.expected_output_type}")
    print("\nCritical path:", plan.critical_path)