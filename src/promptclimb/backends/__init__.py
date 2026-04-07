"""Model backend routing.

Supports:
  openai:gpt-4o-mini          OpenAI API
  anthropic:claude-haiku-4-5   Anthropic API
  ollama:llama3.2              Local Ollama
  lmstudio:gemma-4-26b         Local LMStudio (OpenAI-compatible)
  http://localhost:8082         Raw OpenAI-compatible endpoint
"""


def call_model(
    prompt: str, model: str, temperature: float = 0.0, max_tokens: int = 1024
) -> str:
    """Route a model call to the appropriate backend."""
    if model.startswith("ollama:"):
        from .ollama import call_model as _call
    elif model.startswith("anthropic:"):
        from .anthropic import call_model as _call
    else:
        # openai:, lmstudio:, http://, https:// all use OpenAI-compatible API
        from .openai import call_model as _call
    return _call(prompt, model, temperature=temperature, max_tokens=max_tokens)


def get_embedding(text: str, model: str = "text-embedding-3-small") -> list[float]:
    """Route an embedding call to the appropriate backend."""
    if model.startswith("ollama:"):
        from .ollama import get_embedding as _embed
    else:
        from .openai import get_embedding as _embed
    return _embed(text, model)
