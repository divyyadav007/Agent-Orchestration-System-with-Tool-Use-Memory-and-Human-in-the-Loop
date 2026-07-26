import logging
import os
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)


class LongTermMemory:
    """Long-Term Semantic Memory Manager using ChromaDB.

    Why vector memory is used: When users submit new prompts, the Supervisor queries
    ChromaDB for semantically similar past tasks. Injecting relevant past plans
    improves future plan quality (RAG for agent planning).
    """

    def __init__(self) -> None:
        self.db_path: str = os.getenv("CHROMA_DB_PATH", "./chroma_data")
        try:
            self.client = chromadb.PersistentClient(path=self.db_path)
            self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
            self.collection = self.client.get_or_create_collection(
                name="task_history", embedding_function=self.embedding_fn, metadata={"hnsw:space": "cosine"}
            )
            logger.info("ChromaDB long-term memory store initialized.")
        except Exception as e:
            logger.error(f"Error initializing ChromaDB: {e}", exc_info=True)
            raise

    def add_task(
        self,
        task_id: str,
        user_request: str,
        plan_summary: str,
        tools_used: List[str],
        outcome: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Indexes a completed task and its outcome into ChromaDB."""
        doc = f"Request: {user_request}\nPlan: {plan_summary}\nTools: {', '.join(tools_used)}\nOutcome: {outcome}"
        meta = dict(metadata or {})
        meta["tools_used"] = ",".join(tools_used)

        try:
            self.collection.add(documents=[doc], ids=[task_id], metadatas=[meta])
            logger.debug(f"Saved task '{task_id}' in long-term vector store.")
        except Exception as e:
            logger.error(f"Failed to save task '{task_id}' in ChromaDB: {e}", exc_info=True)

    def search_similar(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Queries vector store for semantically similar historical task executions."""
        try:
            results = self.collection.query(
                query_texts=[query], n_results=n_results, include=["documents", "metadatas", "distances"]
            )

            if not results or not results.get("documents") or not results["documents"][0]:
                return []

            docs = results["documents"][0]
            metas = results.get("metadatas", [[]])[0]
            dists = results.get("distances", [[]])[0]

            return [
                {
                    "document": docs[i],
                    "metadata": metas[i] if i < len(metas) else {},
                    "distance": dists[i] if i < len(dists) else 1.0,
                }
                for i in range(len(docs))
            ]
        except Exception as e:
            logger.error(f"Failed to query ChromaDB for '{query}': {e}", exc_info=True)
            return []


long_term_memory = LongTermMemory()
