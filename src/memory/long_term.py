import chromadb
import os
from chromadb.utils import embedding_functions
from typing import List, Dict

class LongTermMemory:
    def __init__(self):
        self.db_path = os.getenv("CHROMA_DB_PATH", "./chroma_data")
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self.collection = self.client.get_or_create_collection(
            name="task_history",
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_task(self, task_id: str, user_request: str, plan_summary: str,
                 tools_used: List[str], outcome: str, metadata: Dict = None):
        documents = [f"Request: {user_request}\nPlan: {plan_summary}\nTools: {', '.join(tools_used)}\nOutcome: {outcome}"]
        meta = metadata or {}
        meta.update({"tools_used": ",".join(tools_used)})
        self.collection.add(
            documents=documents,
            ids=[task_id],
            metadatas=[meta]
        )
    
    def search_similar(self, query: str, n_results: int = 3) -> List[Dict]:
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        tasks = []
        for i, doc in enumerate(results["documents"][0]):
            tasks.append({
                "document": doc,
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i]
            })
        return tasks

long_term_memory = LongTermMemory()