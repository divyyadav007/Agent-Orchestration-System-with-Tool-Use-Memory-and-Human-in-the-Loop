import time
from typing import List, Dict, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from src.utils.llm import get_llm, invoke_with_retry
from src.tools import registry

class SpecialistBase:
    def __init__(self, name: str, system_prompt: str, tools: List[str] = None):
        self.name = name
        self.system_prompt = system_prompt
        self.tool_names = tools if tools is not None else list(registry.tools.keys())
        print("Registered tools:", list(registry.tools.keys()))
        self.tool_schemas = [
            schema for schema in registry.get_tool_schemas()
            if schema["function"]["name"] in self.tool_names
        ]
        print(f"[{self.name}] Tool schemas:", self.tool_schemas)

    def execute_task(self, task_description: str, previous_outputs: dict = None) -> str:
        llm = get_llm(temperature=0)
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=task_description)
        ]
        if previous_outputs:
            context = "Previous subtask outputs:\n"
            for dep_id, output in previous_outputs.items():
                context += f"Subtask {dep_id}:\n{output}\n\n"
            messages.append(HumanMessage(content=context))

        # If no tools, just call LLM once with retry
        if not self.tool_schemas:
            return invoke_with_retry(llm, messages).content

        # Bind tools
        llm_with_tools = llm.bind_tools(self.tool_schemas, tool_choice="auto")

        for iteration in range(2):                    # max 2 tool-using turns
            try:
                response = invoke_with_retry(llm_with_tools, messages)
            except Exception as e:
                err = str(e)
                if "tool_use_failed" in err or "Tool choice is none" in err:
                    # If model still calls a tool despite error, fallback to no tools
                    fallback_llm = get_llm(temperature=0).bind_tools([], tool_choice="none")
                    messages.append(HumanMessage(
                        content="You tried to call a tool that is unavailable. Answer directly without tools."
                    ))
                    return invoke_with_retry(fallback_llm, messages).content
                raise

            if hasattr(response, "tool_calls") and response.tool_calls:
                messages.append(response)
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    if tool_name not in registry.tools:
                        messages.append(ToolMessage(
                            content=f"Tool '{tool_name}' not available.",
                            tool_call_id=tool_call["id"]
                        ))
                        continue
                    try:
                        result = registry.execute(tool_name, tool_args)
                    except Exception as exec_err:
                        result = f"Error: {exec_err}"
                    messages.append(ToolMessage(
                        content=str(result),
                        tool_call_id=tool_call["id"]
                    ))
                    time.sleep(1)      # spread token usage
            else:
                return response.content

        # fallback after max iterations
        fallback_llm = get_llm(temperature=0).bind_tools([], tool_choice="none")
        messages.append(HumanMessage(content="Please provide your final answer now without tools."))
        return invoke_with_retry(fallback_llm, messages).content
