import logging
import os
import time
from typing import Any, List, Optional

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from openai import RateLimitError

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


def invoke_with_retry(llm: BaseChatModel, messages: List[BaseMessage], max_retries: int = 3) -> Any:
    """Invokes an LLM with linear/exponential backoff to handle rate limits gracefully.

    Why this exists: Free-tier or fast API gateways (like Groq) can hit rate limits
    when multiple agents make rapid requests. Retrying after a short sleep prevents
    workflow crashes during multi-agent execution.
    """
    for attempt in range(max_retries):
        try:
            return llm.invoke(messages)
        except RateLimitError as e:
            if attempt == max_retries - 1:
                logger.error(f"Rate limit reached. Max retries ({max_retries}) exhausted.")
                raise
            wait_seconds = 5 * (attempt + 1)
            logger.warning(f"Rate limited. Retrying in {wait_seconds}s (Attempt {attempt + 1}/{max_retries})... Error: {e}")
            time.sleep(wait_seconds)


def get_llm(model_name: Optional[str] = None, temperature: float = 0.0) -> ChatOpenAI:
    """Initializes and returns a ChatOpenAI client configured for the Groq API gateway.

    Why ChatOpenAI for Groq: Groq provides an OpenAI-compatible API endpoint,
    allowing us to use standard LangChain ChatOpenAI objects seamlessly.
    """
    model = model_name or os.getenv("LLM_MODEL", "llama3-8b-8192")
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.error("GROQ_API_KEY environment variable is missing.")
        raise ValueError("GROQ_API_KEY not found in .env file.")

    logger.debug(f"Initializing LLM model={model}, temperature={temperature}")
    return ChatOpenAI(model=model, temperature=temperature, base_url="https://api.groq.com/openai/v1", api_key=api_key)
