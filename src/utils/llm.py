import os
import time
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from openai import RateLimitError

load_dotenv()

def invoke_with_retry(llm, messages, max_retries=3):
    for attempt in range(max_retries):
        try:
            return llm.invoke(messages)
        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise
            wait = 5 * (attempt + 1)
            print(f"⏳ Rate limited, retrying in {wait}s...")
            time.sleep(wait)

def get_llm(model_name: str = None, temperature: float = 0.0):
    model = model_name or os.getenv("LLM_MODEL", "llama3-8b-8192")
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in .env")
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key
    )