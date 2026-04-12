import requests


def call_model(
    prompt: str, model: str, temperature: float = 0.0, max_tokens: int = 1024
) -> str:
    """Call an LM Studio model via its OpenAI-compatible REST API.

    Model string format: "lmstudio:model-name" or "lmstudio:model-name@host:port"
    Default endpoint: http://localhost:1234/v1
    """
    model_name, base_url = _parse_model_string(model)

    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=(15, 300),
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Error calling LM Studio model {model_name}: {e}")
        return ""


def get_embedding(text: str, model: str = "nomic-embed-text") -> list[float]:
    """Get an embedding from an LM Studio model."""
    model_name, base_url = _parse_model_string(model)

    try:
        response = requests.post(
            f"{base_url}/embeddings",
            json={"model": model_name, "input": text},
            timeout=300,
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]
    except Exception as e:
        print(f"Error getting LM Studio embedding for {model_name}: {e}")
        return []


def _parse_model_string(model: str) -> tuple[str, str]:
    """Parse 'lmstudio:model@host:port' into (model_name, base_url)."""
    name = model.split(":", 1)[-1] if ":" in model else model
    base_url = "http://localhost:1234/v1"

    if "@" in name:
        name, host = name.rsplit("@", 1)
        if not host.startswith("http"):
            host = f"http://{host}"
        base_url = host

    return name, base_url
