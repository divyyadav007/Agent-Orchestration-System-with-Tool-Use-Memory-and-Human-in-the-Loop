import logging
import time
from typing import List, Dict, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from src.utils.llm import get_llm, invoke_with_retry
from src.tools import registry

# Initialize module logger
logger = logging.getLogger(__name__)

class SpecialistBase:
    """Base class for specialist agents within the orchestration graph.
    
    Binds registered workspace tools, handles LLM invocation with fallbacks,
    and supports multi-turn tool usage execution flows.
    """
    
    def __init__(self, name: str, system_prompt: str, tools: Optional[List[str]] = None) -> None:
        """Initializes the specialist agent.

        Args:
            name (str): The identifier name of the specialist.
            system_prompt (str): Prompt context that details agent instructions/persona.
            tools (Optional[List[str]]): Specific tools this specialist can execute.
                If not specified, defaults to all registered system tools.
        """
        self.name: str = name
        self.system_prompt: str = system_prompt
        
        # Default to all tools in registry if not restricted
        self.tool_names: List[str] = tools if tools is not None else list(registry.tools.keys())
        
        logger.debug(f"[{self.name}] Binding specialist tools: {self.tool_names}")
        self.tool_schemas: List[Dict[str, Any]] = [
            schema for schema in registry.get_tool_schemas()
            if schema["function"]["name"] in self.tool_names
        ]
        logger.debug(f"[{self.name}] Configured schemas: {self.tool_schemas}")

    def execute_task(self, task_description: str, previous_outputs: Optional[Dict[str, Any]] = None) -> str:
        """Executes a given subtask using LLM prompts and tools.

        Args:
            task_description (str): Detailed text prompt of what needs to be performed.
            previous_outputs (Optional[Dict[str, Any]]): Dictionary of outputs from parent task runs.

        Returns:
            str: Final completed task text or code output returned by the agent.
        """
        logger.info(f"[{self.name}] Initiating task execution: '{task_description[:100]}...'")
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
            logger.debug(f"[{self.name}] Injected {len(previous_outputs)} parent task dependencies into prompt.")

        # If no tools are configured for this specialist, perform simple single prompt invocation
        if not self.tool_schemas:
            logger.debug(f"[{self.name}] Running in direct text mode (no tools).")
            return invoke_with_retry(llm, messages).content

        # Bind tools with auto choice selection
        llm_with_tools = llm.bind_tools(self.tool_schemas, tool_choice="auto")

        # Support a maximum of 2 multi-turn tool executions per specialist invocation
        for iteration in range(2):
            logger.debug(f"[{self.name}] LLM invocation iteration {iteration + 1}/2.")
            try:
                response = invoke_with_retry(llm_with_tools, messages)
            except Exception as e:
                err = str(e)
                logger.warning(f"[{self.name}] LLM invocation exception: {err}. Attempting direct direct text fallback.")
                if "tool_use_failed" in err or "Tool choice is none" in err:
                    fallback_llm = get_llm(temperature=0).bind_tools([], tool_choice="none")
                    messages.append(HumanMessage(
                        content="You tried to call a tool that is unavailable. Answer directly without tools."
                    ))
                    return invoke_with_retry(fallback_llm, messages).content
                raise

            # Process tool calls if requested by the LLM response
            if hasattr(response, "tool_calls") and response.tool_calls:
                messages.append(response)
                logger.info(f"[{self.name}] LLM requested {len(response.tool_calls)} tool calls.")
                
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    if tool_name not in registry.tools:
                        logger.warning(f"[{self.name}] Requested tool '{tool_name}' is not in registry.")
                        messages.append(ToolMessage(
                            content=f"Tool '{tool_name}' not available.",
                            tool_call_id=tool_call["id"]
                        ))
                        continue
                        
                    try:
                        logger.info(f"[{self.name}] Executing tool '{tool_name}' with args {tool_args}")
                        result = registry.execute(tool_name, tool_args)
                    except Exception as exec_err:
                        logger.error(f"[{self.name}] Error executing tool '{tool_name}': {exec_err}")
                        result = f"Error: {exec_err}"
                        
                    messages.append(ToolMessage(
                        content=str(result),
                        tool_call_id=tool_call["id"]
                    ))
                    time.sleep(1)  # Spread requests to prevent groq rate limits
            else:
                logger.debug(f"[{self.name}] Completed execution directly on iteration {iteration + 1}.")
                return response.content

        # Fallback if the model does not provide a final answer within 2 tool iterations
        logger.warning(f"[{self.name}] Max tool iterations reached. Requesting final direct response.")
        fallback_llm = get_llm(temperature=0).bind_tools([], tool_choice="none")
        messages.append(HumanMessage(content="Please provide your final answer now without tools."))
        return invoke_with_retry(fallback_llm, messages).content
