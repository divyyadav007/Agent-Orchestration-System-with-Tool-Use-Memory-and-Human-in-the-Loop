# src/core/specialists/base.py
from typing import List, Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from src.utils.llm import get_llm
from src.tools import registry

class SpecialistBase:
    """Base class for all specialist agents."""
    
    def __init__(self, name: str, system_prompt: str, tools: List[str] = None):
        self.name = name
        self.system_prompt = system_prompt
        # Tools to use: if not specified, use all registered tools
        self.tool_names = tools or list(registry.tools.keys())
        # Get the actual tool schemas for binding
        self.tool_schemas = [
            schema for schema in registry.get_tool_schemas()
            if schema["function"]["name"] in self.tool_names
        ]
    
    def execute_task(self, task_description: str, previous_outputs: dict = None) -> str:
        llm = get_llm(temperature=0)
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=task_description)
        ]
        if previous_outputs:
            context = "Previous subtask outputs:\n"
            for dep_id, output in previous_outputs.items():
                context += f"Subtask {dep_id}: {output}\n"
            messages.append(HumanMessage(content=context))

        # If no tools registered, straight call
        if not self.tool_schemas:
            return llm.invoke(messages).content

        # Bind tools with tool_choice="auto" to avoid "none" error
        llm_with_tools = llm.bind_tools(self.tool_schemas, tool_choice="auto")

        for iteration in range(5):
            try:
                response = llm_with_tools.invoke(messages)
            except Exception as e:
                # Catch any tool‑related API errors (hallucinated tool call, etc.)
                error_msg = str(e)
                if "tool_use_failed" in error_msg or "Tool choice is none" in error_msg:
                    # Fallback: remove tools and force a plain answer
                    fallback_llm = get_llm(temperature=0)
                    messages.append(HumanMessage(content="You tried to call a tool that is unavailable. Please answer the question directly without using any tools."))
                    return fallback_llm.invoke(messages).content
                else:
                    raise  # re‑raise unexpected errors

            if hasattr(response, "tool_calls") and response.tool_calls:
                messages.append(response)
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]

                    # Safety: only execute if tool is registered
                    if tool_name not in registry.tools:
                        messages.append(ToolMessage(
                            content=f"Tool '{tool_name}' not available. Use only available tools.",
                            tool_call_id=tool_call["id"]
                        ))
                        continue

                    try:
                        result = registry.execute(tool_name, tool_args)
                    except Exception as exec_err:
                        result = f"Tool execution error: {exec_err}"

                    messages.append(ToolMessage(
                        content=str(result),
                        tool_call_id=tool_call["id"]
                    ))
            else:
                return response.content

        # Max iterations reached, force final answer without tools
        fallback_llm = get_llm(temperature=0)
        messages.append(HumanMessage(content="Please provide your final answer now without using tools."))
        return fallback_llm.invoke(messages).content