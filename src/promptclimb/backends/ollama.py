import requests


def call_model(
    prompt: str, model: str, temperature: float = 0.0, max_tokens: int = 1024
) -> str:
    """Call an Ollama model via its REST API.

    Model string format: "ollama:model-name" or "ollama:model-name@host:port"
    Default endpoint: http://localhost:11434
    """
    model_name, base_url = _parse_model_string(model)

    try:
        response = requests.post(
            f"{base_url}/api/chat",
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
                "stream": False,
            },
            timeout=(15, 300),
        )
        response.raise_for_status()
        return response.json()["message"]["content"]
    except Exception as e:
        print(f"Error calling Ollama model {model_name}: {e}")
        return ""


def get_embedding(text: str, model: str = "nomic-embed-text") -> list[float]:
    """Get an embedding from an Ollama model."""
    model_name, base_url = _parse_model_string(model)

    try:
        response = requests.post(
            f"{base_url}/api/embed",
            json={"model": model_name, "input": text},
            timeout=300,
        )
        response.raise_for_status()
        return response.json()["embeddings"][0]
    except Exception as e:
        print(f"Error getting Ollama embedding for {model_name}: {e}")
        return []


def _parse_model_string(model: str) -> tuple[str, str]:
    """Parse 'ollama:model@host:port' into (model_name, base_url)."""
    name = model.split(":", 1)[-1] if ":" in model else model
    base_url = "http://localhost:11434"

    if "@" in name:
        name, host = name.rsplit("@", 1)
        if not host.startswith("http"):
            host = f"http://{host}"
        base_url = host

    return name, base_url
