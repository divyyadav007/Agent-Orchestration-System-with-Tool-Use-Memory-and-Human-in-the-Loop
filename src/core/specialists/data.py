import logging
from src.core.specialists.base import SpecialistBase

# Initialize module logger
logger = logging.getLogger(__name__)

DATA_SYSTEM_PROMPT = """You are a data specialist. You can query databases, process data, and perform calculations.
For now, return only the data/calculation results as plain text.

IMPORTANT: You do NOT have access to any tools at this time. You must return only the analysis or calculation results as plain text. Do NOT attempt to call any functions or tools."""


class DataSpecialist(SpecialistBase):
    """Specialist agent responsible for processing datasets, data formatting, and calculation tasks."""

    def __init__(self) -> None:
        logger.debug("Initializing DataSpecialist.")
        super().__init__(name="data", system_prompt=DATA_SYSTEM_PROMPT, tools=[])
