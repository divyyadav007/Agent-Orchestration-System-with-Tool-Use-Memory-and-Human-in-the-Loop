from src.memory.short_term import short_term_memory
from src.memory.long_term import long_term_memory
from typing import Dict, Any, List

class MemoryManager:
    def __init__(self):
        self.short = short_term_memory
        self.long = long_term_memory
    
    def get_context_for_planning(self, user_request: str) -> List[Dict]:
        """Retrieve similar past tasks to help the supervisor plan better."""
        return self.long.search_similar(user_request, n_results=3)
    
    def save_task_state(self, task_id: str, state_snapshot: Dict[str, Any]):
        self.short.save(task_id, state_snapshot)
    
    def load_task_state(self, task_id: str) -> Dict[str, Any]:
        return self.short.load(task_id)
    
    def complete_task(self, task_id: str, user_request: str, plan_summary: str,
                     tools_used: List[str], outcome: str, metadata: Dict = None):
        # Save to long-term memory for future
        self.long.add_task(task_id, user_request, plan_summary, tools_used, outcome, metadata)
        # Optionally remove from short-term (or let TTL handle)
        self.short.delete(task_id)

# Singleton
memory_manager = MemoryManager()