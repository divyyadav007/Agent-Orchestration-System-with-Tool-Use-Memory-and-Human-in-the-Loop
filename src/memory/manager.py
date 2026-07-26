import logging
from typing import Any, Dict, List, Optional

from src.memory.long_term import long_term_memory
from src.memory.short_term import short_term_memory

# Initialize module logger
logger = logging.getLogger(__name__)


class MemoryManager:
    """Orchestrator coordinating short-term caching and semantic long-term agent memory operations."""

    def __init__(self) -> None:
        self.short = short_term_memory
        self.long = long_term_memory

    def get_context_for_planning(self, user_request: str) -> List[Dict[str, Any]]:
        """Retrieves semantic memory context for task planning.

        Args:
            user_request (str): User prompt/task request.

        Returns:
            List[Dict[str, Any]]: A list of similar historical records matching the prompt.
        """
        logger.debug(f"Retrieving planning context for user request: '{user_request[:80]}...'")
        return self.long.search_similar(user_request, n_results=3)

    def save_task_state(self, task_id: str, state_snapshot: Dict[str, Any]) -> None:
        """Caches the current state of a task configuration in progress.

        Args:
            task_id (str): Unique identifier for the active task.
            state_snapshot (Dict[str, Any]): Current state workflow map.
        """
        logger.debug(f"Saving task state snapshot for task_id: '{task_id}'")
        self.short.save(task_id, state_snapshot)

    def load_task_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Loads a cached state of a task in progress.

        Args:
            task_id (str): Task identifier.

        Returns:
            Optional[Dict[str, Any]]: Cached workflow state dict if found, else None.
        """
        logger.debug(f"Loading task state snapshot for task_id: '{task_id}'")
        return self.short.load(task_id)

    def complete_task(
        self,
        task_id: str,
        user_request: str,
        plan_summary: str,
        tools_used: List[str],
        outcome: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Completes execution on a task: indexes details in vector memory and cleans up temporary state.

        Args:
            task_id (str): Task configuration ID.
            user_request (str): Original user request.
            plan_summary (str): Summarized planning text.
            tools_used (List[str]): List of tools used during workflow.
            outcome (str): Task execution output.
            metadata (Optional[Dict[str, Any]]): Metadata variables.
        """
        logger.info(f"Finalizing task '{task_id}': indexing outcome and purging transient state caches.")
        self.long.add_task(task_id, user_request, plan_summary, tools_used, outcome, metadata)
        self.short.delete(task_id)


# Global singleton memory manager instance
memory_manager = MemoryManager()
