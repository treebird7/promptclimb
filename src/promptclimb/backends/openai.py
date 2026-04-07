import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


def get_openai_client(model_string: str):
    """
    Initializes an OpenAI client based on the model string.
    Supports openai:, lmstudio:, http://, https:// prefixes.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = None

    if model_string.startswith("openai:"):
        pass  # Default OpenAI client
    elif model_string.startswith("lmstudio:"):
        base_url = "http://localhost:1234/v1"
        api_key = "lm-studio"
    elif model_string.startswith("http://") or model_string.startswith("https://"):
        base_url = model_string
        api_key = "no-key-required"

    return OpenAI(api_key=api_key, base_url=base_url)


def call_model(
    prompt: str, model: str, temperature: float = 0.0, max_tokens: int = 1024
) -> str:
    """
    Calls an OpenAI-compatible model.
    """
    model_name = model.split(":")[-1] if ":" in model else model
    client = get_openai_client(model)

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling model {model}: {e}")
        return ""


def get_embedding(text: str, model: str = "text-embedding-3-small") -> list[float]:
    """
    Gets an embedding for a text string.
    """
    model_name = model.split(":")[-1] if ":" in model else model
    client = get_openai_client(model)

    try:
        response = client.embeddings.create(input=text, model=model_name)
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding for model {model}: {e}")
        return []
