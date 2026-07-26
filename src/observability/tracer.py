import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.callbacks.base import BaseCallbackHandler
from rich.tree import Tree

# Initialize module logger
logger = logging.getLogger(__name__)


class ExecutionNode:
    """Represents a single span execution node in the trace dependency tree."""

    def __init__(self, name: str, node_type: str = "node") -> None:
        self.name: str = name
        self.type: str = node_type
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.duration_ms: float = 0.0
        self.input_data: Any = None
        self.output_data: Any = None
        self.metadata: Dict[str, Any] = {}
        self.children: List[ExecutionNode] = []
        self.token_usage: Dict[str, int] = {}


class GraphTracer(BaseCallbackHandler):
    """Tracer callback engine logging agent, LLM, and tool invocations into a hierarchical tree format."""

    def __init__(self) -> None:
        super().__init__()
        self.root: ExecutionNode = ExecutionNode("workflow", "graph")
        self.stack: List[ExecutionNode] = [self.root]
        logger.debug("GraphTracer callback handler initialized.")

    def on_chain_start(self, serialized: Optional[Dict[str, Any]], inputs: Dict[str, Any], **kwargs: Any) -> None:
        """Fires when a LangChain/LangGraph chain execution step begins."""
        if serialized is None:
            serialized = {}
        name = serialized.get("name", "chain") or "chain"
        node = ExecutionNode(name, "node")
        node.start_time = datetime.utcnow()
        node.input_data = inputs

        self.stack[-1].children.append(node)
        self.stack.append(node)
        logger.debug(f"Tracer Chain Start: '{name}'")

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Fires when a chain execution step completes."""
        if len(self.stack) <= 1:  # Root should remain on stack
            return
        node = self.stack.pop()
        node.end_time = datetime.utcnow()
        if node.start_time:
            node.duration_ms = (node.end_time - node.start_time).total_seconds() * 1000
        node.output_data = outputs
        logger.debug(f"Tracer Chain End: '{node.name}' ({node.duration_ms:.1f}ms)")

    def on_llm_start(self, serialized: Optional[Dict[str, Any]], prompts: List[str], **kwargs: Any) -> None:
        """Fires when LLM processing begins."""
        if len(self.stack) == 0:
            self.stack = [self.root]
        name = "llm_call"
        if serialized and isinstance(serialized, dict):
            name = serialized.get("name", name)

        llm_node = ExecutionNode(name, "llm")
        llm_node.start_time = datetime.utcnow()
        llm_node.input_data = {"prompts": prompts}

        self.stack[-1].children.append(llm_node)
        self.stack.append(llm_node)
        logger.debug(f"Tracer LLM Start: '{name}'")

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Fires when LLM processing finishes successfully."""
        if len(self.stack) <= 1:
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

        logger.debug(f"Tracer LLM End: '{node.name}' ({node.duration_ms:.1f}ms)")

    def add_tool_call(self, tool_name: str, params: Dict[str, Any], result: Any, duration_ms: float) -> None:
        """Explicitly appends a tool execution call to the current active span node.

        Args:
            tool_name (str): Identifier name of the invoked tool.
            params (Dict[str, Any]): Parameters supplied.
            result (Any): Evaluation result text/data.
            duration_ms (float): Elapsed execution duration in milliseconds.
        """
        tool_node = ExecutionNode(tool_name, "tool")
        tool_node.start_time = datetime.utcnow()
        tool_node.end_time = datetime.utcnow()
        tool_node.duration_ms = duration_ms
        tool_node.input_data = params
        tool_node.output_data = result

        if len(self.stack) > 0:
            self.stack[-1].children.append(tool_node)
        logger.debug(f"Tracer Tool Call Appended: '{tool_name}' ({duration_ms:.1f}ms)")

    def get_tree(self) -> Tree:
        """Constructs and returns a Rich Console Tree representation of the execution logs.

        Returns:
            Tree: Interactive console tree layout representing nested execution spans.
        """
        tree = Tree(f"[bold blue]{self.root.name}[/]")
        self._add_node_to_tree(tree, self.root)
        return tree

    def _add_node_to_tree(self, tree: Tree, node: ExecutionNode) -> None:
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

    def reset(self) -> None:
        """Purges execution span histories to prepare for a fresh workflow run."""
        self.root = ExecutionNode("workflow", "graph")
        self.stack = [self.root]
        logger.info("GraphTracer execution spans reset.")
