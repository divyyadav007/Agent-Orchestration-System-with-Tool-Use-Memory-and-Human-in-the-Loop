import time
from typing import Any, Dict, List, Optional
from datetime import datetime
from langchain_core.callbacks.base import BaseCallbackHandler
from rich.tree import Tree

class ExecutionNode:
    def __init__(self, name: str, node_type: str = "node"):
        self.name = name
        self.type = node_type
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.duration_ms: float = 0.0
        self.input_data: Any = None
        self.output_data: Any = None
        self.metadata: Dict[str, Any] = {}
        self.children: List[ExecutionNode] = []
        self.token_usage: Dict[str, int] = {}

class GraphTracer(BaseCallbackHandler):
    def __init__(self):
        self.root = ExecutionNode("workflow", "graph")
        self.stack = [self.root]

    # ---------- chain events ----------
    def on_chain_start(self, serialized: Optional[Dict[str, Any]], inputs: Dict[str, Any], **kwargs):
        # serialized may be None for some internal chains
        if serialized is None:
            serialized = {}
        name = serialized.get("name", "chain") or "chain"
        node = ExecutionNode(name, "node")
        node.start_time = datetime.utcnow()
        node.input_data = inputs
        self.stack[-1].children.append(node)
        self.stack.append(node)

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs):
        if len(self.stack) <= 1:   # only root left, ignore mismatched end
            return
        node = self.stack.pop()
        node.end_time = datetime.utcnow()
        if node.start_time:
            node.duration_ms = (node.end_time - node.start_time).total_seconds() * 1000
        node.output_data = outputs

    # ---------- LLM events ----------
    def on_llm_start(self, serialized: Optional[Dict[str, Any]], prompts: List[str], **kwargs):
        if len(self.stack) == 0:
            self.stack = [self.root]      # safety reset
        name = "llm_call"
        if serialized and isinstance(serialized, dict):
            name = serialized.get("name", name)
        llm_node = ExecutionNode(name, "llm")
        llm_node.start_time = datetime.utcnow()
        llm_node.input_data = {"prompts": prompts}
        self.stack[-1].children.append(llm_node)
        self.stack.append(llm_node)

    def on_llm_end(self, response, **kwargs):
        if len(self.stack) <= 1:          # ignore mismatched end
            return
        node = self.stack.pop()
        node.end_time = datetime.utcnow()
        if node.start_time:
            node.duration_ms = (node.end_time - node.start_time).total_seconds() * 1000
        try:
            usage = response.llm_output.get("token_usage", {})
            node.token_usage = {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            }
        except Exception:
            pass
        try:
            node.output_data = {"content": response.generations[0][0].text}
        except Exception:
            pass

    # ---------- tool calls (manually added) ----------
    def add_tool_call(self, tool_name: str, params: Dict, result: Any, duration_ms: float):
        tool_node = ExecutionNode(tool_name, "tool")
        tool_node.start_time = datetime.utcnow()
        tool_node.end_time = datetime.utcnow()
        tool_node.duration_ms = duration_ms
        tool_node.input_data = params
        tool_node.output_data = result
        # add under current active node
        if len(self.stack) > 0:
            self.stack[-1].children.append(tool_node)

    # ---------- tree rendering ----------
    def get_tree(self) -> Tree:
        tree = Tree(f"[bold blue]{self.root.name}[/]")
        self._add_node_to_tree(tree, self.root)
        return tree

    def _add_node_to_tree(self, tree: Tree, node: ExecutionNode):
        for child in node.children:
            label = child.name
            if child.type == "llm":
                tokens = child.token_usage.get("total_tokens", 0)
                label += f" [dim]({tokens} tokens, {child.duration_ms:.0f}ms)[/]"
            elif child.type == "tool":
                label += f" [dim]({child.duration_ms:.0f}ms)[/]"
            elif child.type == "node":
                label += f" [dim]({child.duration_ms:.0f}ms)[/]"
            branch = tree.add(label)
            self._add_node_to_tree(branch, child)

    def reset(self):
        self.root = ExecutionNode("workflow", "graph")
        self.stack = [self.root]