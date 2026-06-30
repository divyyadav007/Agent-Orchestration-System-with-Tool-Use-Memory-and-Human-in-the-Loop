import logging
import os
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.utils import embedding_functions

# Initialize module logger
logger = logging.getLogger(__name__)

class LongTermMemory:
    """Manages long-term semantic memory storing historical task logs in ChromaDB."""

    def __init__(self) -> None:
        self.db_path: str = os.getenv("CHROMA_DB_PATH", "./chroma_data")
        logger.info(f"Initializing ChromaDB client at pathway: {self.db_path}")
        try:
            self.client = chromadb.PersistentClient(path=self.db_path)
            self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            self.collection = self.client.get_or_create_collection(
                name="task_history",
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("ChromaDB long-term memory store initialized successfully.")
        except Exception as e:
            logger.error(f"Critical error initializing ChromaDB: {e}", exc_info=True)
            raise

    def add_task(
        self,
        task_id: str,
        user_request: str,
        plan_summary: str,
        tools_used: List[str],
        outcome: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Stores a task execution summary semantic record.

        Args:
            task_id (str): Unique identifier for the completed task.
            user_request (str): The original user prompt request.
            plan_summary (str): The generated execution plan summary text.
            tools_used (List[str]): List of tool names called during execution.
            outcome (str): Result output description.
            metadata (Optional[Dict[str, Any]]): Additional metadata variables.
        """
        doc = f"Request: {user_request}\nPlan: {plan_summary}\nTools: {', '.join(tools_used)}\nOutcome: {outcome}"
        meta = metadata or {}
        meta.update({"tools_used": ",".join(tools_used)})
        
        logger.info(f"Storing completed task semantic record in ChromaDB: id='{task_id}'")
        try:
            self.collection.add(
                documents=[doc],
                ids=[task_id],
                metadatas=[meta]
            )
            logger.debug(f"Task record '{task_id}' successfully saved in vector store.")
        except Exception as e:
            logger.error(f"Failed to save task record '{task_id}' in ChromaDB: {e}", exc_info=True)

    def search_similar(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Queries the vector store for historically similar task executions.

        Args:
            query (str): The user query/prompt text to search against.
            n_results (int): The number of search results to return.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing similar task matches,
                each containing keys 'document', 'metadata', and 'distance'.
        """
        logger.debug(f"Searching vector memory for similar tasks to query: '{query[:100]}...'")
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            tasks: List[Dict[str, Any]] = []
            
            # Verify results exist
            if not results or not results.get("documents") or len(results["documents"]) == 0:
                logger.debug("No matching records found in long-term memory.")
                return tasks
                
            for i, doc in enumerate(results["documents"][0]):
                tasks.append({
                    "document": doc,
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "distance": results["distances"][0][i] if results.get("distances") else 1.0
                })
                
            logger.debug(f"Found {len(tasks)} matches in vector memory.")
            return tasks
        except Exception as e:
            logger.error(f"Failed to query ChromaDB for query '{query}': {e}", exc_info=True)
            return []


# Global singleton long-term memory instance
long_term_memory = LongTermMemory()