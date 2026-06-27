import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

def get_llm(model_name: str = None, temperature: float = 0.0):
    model = model_name or os.getenv("LLM_MODEL", "llama3-70b-8192")
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key:
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            base_url="https://api.groq.com/openai/v1",
            api_key=groq_api_key
        )
    else:
        return ChatOpenAI(model=model, temperature=temperature)