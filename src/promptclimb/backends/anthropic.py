import os

try:
    import anthropic
except ImportError:
    anthropic = None


def call_model(
    prompt: str, model: str, temperature: float = 0.0, max_tokens: int = 1024
) -> str:
    """Call an Anthropic model via the Anthropic SDK.

    Model string format: "anthropic:model-name"
    Examples: "anthropic:claude-haiku-4-5", "anthropic:claude-sonnet-4-6"
    """
    if anthropic is None:
        raise ImportError(
            "anthropic package not installed. Run: pip install anthropic"
        )

    model_name = model.split(":", 1)[-1] if ":" in model else model
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model=model_name,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return response.content[0].text
    except Exception as e:
        print(f"Error calling Anthropic model {model_name}: {e}")
        return ""
