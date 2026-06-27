from src.core.specialists.base import SpecialistBase

WRITING_SYSTEM_PROMPT = """You are a writing specialist. You craft clear, concise, and professional text based on given information. 
Focus on the required tone, audience, and length.

IMPORTANT: You do NOT have access to any tools. You must return only the written content as plain text. Do NOT attempt to call any functions or tools."""

class WritingSpecialist(SpecialistBase):
    def __init__(self):
        super().__init__(
            name="writing",
            system_prompt=WRITING_SYSTEM_PROMPT,
            tools=[]  # no tools needed for pure text generation
        )