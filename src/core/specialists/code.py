import logging

from src.core.specialists.base import SpecialistBase

# Initialize module logger
logger = logging.getLogger(__name__)

CODE_SYSTEM_PROMPT = """You are a code specialist. You handle file operations and can save text content to files.

You must:
- Use the save_file tool to write text content to the requested file.
- Confirm successful write to the user with a confirmation message.
"""


class CodeSpecialist(SpecialistBase):
    """Specialist agent responsible for code execution or environment file IO operations."""

    def __init__(self) -> None:
        logger.debug("Initializing CodeSpecialist.")
        super().__init__(name="code", system_prompt=CODE_SYSTEM_PROMPT, tools=["save_file"])
