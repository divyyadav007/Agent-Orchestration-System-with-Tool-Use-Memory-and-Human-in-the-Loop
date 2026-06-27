from src.core.specialists.base import SpecialistBase

CODE_SYSTEM_PROMPT = """You are a code specialist. You can write and execute Python code, and handle file operations. 
For now, you only need to confirm file operations with a string confirmation.

IMPORTANT: You do NOT have access to any tools at this time. You must return only a confirmation string as plain text. Do NOT attempt to call any functions or tools."""

class CodeSpecialist(SpecialistBase):
    def __init__(self):
        super().__init__(
            name="code",
            system_prompt=CODE_SYSTEM_PROMPT,
            tools=[]  # will add file_io later
        )