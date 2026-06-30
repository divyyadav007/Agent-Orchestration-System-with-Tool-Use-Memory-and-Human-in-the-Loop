import logging
import os
import time
from typing import Any, List, Optional, Union
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from langchain_core.language_models.chat_models import BaseChatModel
from openai import RateLimitError

# Load environment variables
load_dotenv()

# Initialize module logger
logger = logging.getLogger(__name__)

def invoke_with_retry(
    llm: BaseChatModel,
    messages: List[BaseMessage],
    max_retries: int = 3
) -> Any:
    """Invokes the language model with an exponential backoff retry mechanism for rate limits.

    Args:
        llm (BaseChatModel): The LangChain chat model to invoke.
        messages (List[BaseMessage]): The conversation messages/prompt to send.
        max_retries (int): Maximum number of retry attempts on rate limit errors.

    Raises:
        RateLimitError: If rate limit is hit and max_retries is reached.
        Exception: Any other exception raised by the LLM invocation.

    Returns:
        Any: The response from the language model.
    """
    for attempt in range(max_retries):
        try:
            return llm.invoke(messages)
        except RateLimitError as e:
            if attempt == max_retries - 1:
                logger.error(f"Rate limit reached. Max retries ({max_retries}) exhausted.")
                raise
            wait = 5 * (attempt + 1)
            logger.warning(f"Rate limited during LLM invocation. Retrying in {wait} seconds (Attempt {attempt + 1}/{max_retries})... Error: {e}")
            time.sleep(wait)

def get_llm(model_name: Optional[str] = None, temperature: float = 0.0) -> ChatOpenAI:
    """Initializes and returns the configuration for the ChatOpenAI client pointing to the Groq API gateway.

    Args:
        model_name (Optional[str]): Name of the LLM model to request. If not specified,
            will fall back to the LLM_MODEL environment variable or 'llama3-8b-8192'.
        temperature (float): Controls creativity/determinism of the model. Defaults to 0.0.

    Raises:
        ValueError: If GROQ_API_KEY environment variable is not defined.

    Returns:
        ChatOpenAI: A configured ChatOpenAI instance pointing to Groq.
    """
    model = model_name or os.getenv("LLM_MODEL", "llama3-8b-8192")
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.error("GROQ_API_KEY environment variable is missing.")
        raise ValueError("GROQ_API_KEY not found in .env")
        
    logger.debug(f"Initializing ChatOpenAI with model={model}, temperature={temperature}")
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key
    )