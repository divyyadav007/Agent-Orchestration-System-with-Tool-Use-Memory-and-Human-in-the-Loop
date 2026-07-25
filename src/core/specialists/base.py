import logging
import time
from typing import List, Dict, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from src.utils.llm import get_llm, invoke_with_retry
from src.tools import registry

logger = logging.getLogger(__name__)


class SpecialistBase:
    """Base class for all specialized agents (Research, Writing, Data, Code).
    
    Why this pattern exists: Inheriting from SpecialistBase ensures every specialist 
    agent has a consistent tool-binding interface, dependency context ingestion, 
    and multi-turn tool execution loop.
    """

    def __init__(self, name: str, system_prompt: str, tools: Optional[List[str]] = None) -> None:
        self.name: str = name
        self.system_prompt: str = system_prompt
        self.tool_names: List[str] = tools if tools is not None else list(registry.tools.keys())

        # Select matching tool schemas registered in ToolRegistry
        self.tool_schemas: List[Dict[str, Any]] = [
            schema for schema in registry.get_tool_schemas()
            if schema["function"]["name"] in self.tool_names
        ]

    def execute_task(self, task_description: str, previous_outputs: Optional[Dict[str, Any]] = None) -> str:
        """Executes a subtask, injecting dependency context and handling tool calls."""
        logger.info(f"[{self.name}] Executing task: '{task_description[:80]}...'")
        llm = get_llm(temperature=0)

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=task_description)
        ]

        # Inject context from completed prerequisite subtasks
        if previous_outputs:
            context = "Previous subtask outputs:\n" + "\n\n".join(
                f"Subtask {dep_id}:\n{out}" for dep_id, out in previous_outputs.items()
            )
            messages.append(HumanMessage(content=context))

        # Direct text mode if no tools configured
        if not self.tool_schemas:
            return invoke_with_retry(llm, messages).content

        # Tool-enabled mode with up to 2 tool loop iterations
        llm_with_tools = llm.bind_tools(self.tool_schemas, tool_choice="auto")

        for iteration in range(2):
            try:
                response = invoke_with_retry(llm_with_tools, messages)
            except Exception as e:
                logger.warning(f"[{self.name}] Tool invocation error ({e}). Falling back to text response.")
                fallback_llm = get_llm(temperature=0).bind_tools([], tool_choice="none")
                messages.append(HumanMessage(content="Answer directly without tools."))
                return invoke_with_retry(fallback_llm, messages).content

            # Handle requested tool calls
            if getattr(response, "tool_calls", None):
                messages.append(response)
                for call in response.tool_calls:
                    tool_name, tool_args = call["name"], call["args"]
                    if tool_name not in registry.tools:
                        messages.append(ToolMessage(content=f"Tool '{tool_name}' missing.", tool_call_id=call["id"]))
                        continue

                    try:
                        result = registry.execute(tool_name, tool_args)
                    except Exception as err:
                        result = f"Error: {err}"

                    messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
                    time.sleep(1)
            else:
                return response.content

        # Fallback if tools repeat without final text answer
        fallback_llm = get_llm(temperature=0).bind_tools([], tool_choice="none")
        messages.append(HumanMessage(content="Please provide your final answer now."))
        return invoke_with_retry(fallback_llm, messages).content

