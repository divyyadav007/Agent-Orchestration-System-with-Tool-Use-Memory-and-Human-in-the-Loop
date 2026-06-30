import logging
from typing import Callable, Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

# Initialize module logger
logger = logging.getLogger(__name__)

class ToolDefinition(BaseModel):
    """Configuration definition representing a single registered tool."""
    name: str = Field(..., description="Unique identification name of the tool")
    description: str = Field(..., description="Detailed description of what the tool accomplishes")
    parameter_schema: Dict[str, Any] = Field(..., description="JSON Schema definition for the expected parameters")
    function: Optional[Callable[..., Any]] = Field(default=None, description="The executable Python function handler")

    class Config:
        arbitrary_types_allowed = True


class ToolInvocation(BaseModel):
    """Audit log representing a single execution instance of a tool."""
    tool_name: str = Field(..., description="Name of the invoked tool")
    params: Dict[str, Any] = Field(..., description="Parameters supplied to the invocation")
    result: Any = Field(default=None, description="Returned result from the execution")
    error: Optional[str] = Field(default=None, description="Error message if the invocation failed")
    start_time: datetime = Field(default_factory=datetime.utcnow, description="UTC Timestamp of execution start")
    end_time: Optional[datetime] = Field(default=None, description="UTC Timestamp of execution completion")


class ToolRegistry:
    """Registry engine that handles registration, schema retrieval, and execution tracking of agent tools."""
    def __init__(self) -> None:
        self.tools: Dict[str, ToolDefinition] = {}
        self.invocation_log: List[ToolInvocation] = []
        self.tracer: Any = None  # Will be set externally to trace execution pathways

    def set_tracer(self, tracer: Any) -> None:
        """Attaches an external tracer callback handler to log tool execution spans.

        Args:
            tracer (Any): An instance of GraphTracer or compatible callback tracer.
        """
        logger.debug(f"Tracer set on ToolRegistry: {type(tracer).__name__}")
        self.tracer = tracer

    def register(self, name: str, description: str, parameter_schema: Dict[str, Any]) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator that registers a Python function as an executable agent tool.

        Args:
            name (str): Unique identifier name for the tool.
            description (str): Detailed instruction string describing when and how to call the tool.
            parameter_schema (Dict[str, Any]): JSON Schema mapping parameter names to types and descriptions.

        Returns:
            Callable: Decorated wrapper registering the tool metadata on function load.
        """
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.tools[name] = ToolDefinition(
                name=name,
                description=description,
                parameter_schema=parameter_schema,
                function=func
            )
            logger.info(f"Successfully registered tool: '{name}'")
            return func
        return decorator

    def execute(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Executes a registered tool by its identifier name and parameters.

        Args:
            tool_name (str): Name of the registered tool to invoke.
            params (Dict[str, Any]): Dictionary of arguments to pass to the tool.

        Raises:
            ValueError: If the tool is not registered.
            Exception: Any exception thrown during the execution of the tool function.

        Returns:
            Any: The returned value of the tool's execution handler.
        """
        if tool_name not in self.tools:
            logger.error(f"Execution failed: Tool '{tool_name}' is not registered.")
            raise ValueError(f"Tool '{tool_name}' not registered.")
            
        tool = self.tools[tool_name]
        invocation = ToolInvocation(tool_name=tool_name, params=params)
        self.invocation_log.append(invocation)
        
        logger.info(f"Executing tool '{tool_name}' with parameters: {params}")
        start = datetime.utcnow()
        try:
            if tool.function is None:
                raise ValueError(f"Tool '{tool_name}' does not have an execution handler function.")
            result = tool.function(**params)
            invocation.result = result
            
            # Record execution span in GraphTracer if configured
            if self.tracer:
                duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
                self.tracer.add_tool_call(tool_name, params, result, duration_ms)
                
            logger.debug(f"Tool '{tool_name}' executed successfully.")
            return result
        except Exception as e:
            logger.error(f"Error during execution of tool '{tool_name}': {e}", exc_info=True)
            invocation.error = str(e)
            raise
        finally:
            invocation.end_time = datetime.utcnow()

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Returns standard Open-AI tool configuration schemas for registered tools.

        Returns:
            List[Dict[str, Any]]: Array of dictionary declarations formatted for tool binding.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameter_schema
                }
            }
            for t in self.tools.values()
        ]


# Global singleton registry instance
registry = ToolRegistry()