import logging

from src.core.specialists.base import SpecialistBase

# Initialize module logger
logger = logging.getLogger(__name__)

WRITING_SYSTEM_PROMPT = """You are a writing specialist. You craft clear, concise, and professional text based on given information. 
Focus on the required tone, audience, and length.

CRITICAL TOPIC FOCUS:
- You must carefully filter the provided information and previous outputs.
- Focus ONLY on the requested topic/theme of the task.
- Strictly ignore any unrelated, off-topic, or irrelevant news items, headlines, or data that may be present in the previous outputs (e.g., ignore general world news, sports, unrelated incidents, or generic pricing updates if the task is about a specific scandal).

IMPORTANT: You do NOT have access to any tools. You must return only the written content as plain text. Do NOT attempt to call any functions or tools."""


class WritingSpecialist(SpecialistBase):
    """Specialist agent responsible for drafting documents, emails, reports, and summaries."""

    def __init__(self) -> None:
        logger.debug("Initializing WritingSpecialist.")
        super().__init__(
            name="writing", system_prompt=WRITING_SYSTEM_PROMPT, tools=[]  # No tools needed for pure text generation
        )
