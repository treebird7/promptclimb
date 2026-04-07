import os
from anthropic import Anthropic


def call_model(prompt: str, model: str, temperature: float = 0.0, max_tokens: int = 4096) -> str:
    model_name = model.split(":")[-1] if ":" in model else model
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    try:
        resp = client.messages.create(
            model=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text
    except Exception as e:
        print(f"Error calling anthropic model {model}: {e}")
        return ""
