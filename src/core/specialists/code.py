from src.core.specialists.base import SpecialistBase

CODE_SYSTEM_PROMPT = """You are a code specialist. You handle file operations and can save text content to files.

You must:
- Use the save_file tool to write text content to the requested file.
- Confirm successful write to the user with a confirmation message.
"""

class CodeSpecialist(SpecialistBase):
    def __init__(self):
        super().__init__(
            name="code",
            system_prompt=CODE_SYSTEM_PROMPT,
            tools=["save_file"]
        )