from typing import Callable, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class ToolDefinition(BaseModel):
    name: str
    description: str
    parameter_schema: Dict[str, Any]
    function: Optional[Callable] = None

class ToolInvocation(BaseModel):
    tool_name: str
    params: Dict[str, Any]
    result: Any = None
    error: Optional[str] = None
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self.invocation_log: list[ToolInvocation] = []
        self.tracer = None   # will be set externally

    def set_tracer(self, tracer):
        self.tracer = tracer

    def register(self, name: str, description: str, parameter_schema: Dict[str, Any]):
        def decorator(func: Callable):
            self.tools[name] = ToolDefinition(
                name=name,
                description=description,
                parameter_schema=parameter_schema,
                function=func
            )
            return func
        return decorator

    def execute(self, tool_name: str, params: Dict[str, Any]) -> Any:
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not registered.")
        tool = self.tools[tool_name]
        invocation = ToolInvocation(tool_name=tool_name, params=params)
        self.invocation_log.append(invocation)
        start = datetime.utcnow()
        try:
            result = tool.function(**params)
            invocation.result = result
            if self.tracer:
                duration = (datetime.utcnow() - start).total_seconds() * 1000
                self.tracer.add_tool_call(tool_name, params, result, duration)
            return result
        except Exception as e:
            invocation.error = str(e)
            raise
        finally:
            invocation.end_time = datetime.utcnow()

    def get_tool_schemas(self) -> list[Dict[str, Any]]:
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

registry = ToolRegistry()