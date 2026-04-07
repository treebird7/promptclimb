def _route_call(prompt: str, model: str, **kwargs) -> str:
    if model.startswith("anthropic:"):
        from .backends.anthropic import call_model
    else:
        from .backends.openai import call_model
    return call_model(prompt, model, **kwargs)


def get_proposer_prompt(
    prompt: str, score: float, weak_cases: list, history: list
) -> str:
    """
    Generates the prompt for the proposer model.
    """
    history_str = "\n".join(
        [f"- {item['score']:.4f}: {item['prompt'][:50]}..." for item in history[-5:]]
    )
    weak_cases_str = "\n".join(
        [f"- {case['input'][:50]}... -> {case['expected']}" for case in weak_cases[:5]]
    )

    return f"""You are a prompt engineer. Your job is to improve this prompt.

Current score: {score:.4f}/1.0
Weakest cases:
{weak_cases_str}

Recent history:
{history_str}

Current prompt:
---
{prompt}
---

Output an improved version of the entire prompt. Focus on the weakest cases.
Do not explain your changes — just output the new prompt.
"""


def propose(
    prompt: str, score: float, weak_cases: list, history: list, model: str
) -> str:
    """
    Generates a new prompt using the proposer model.
    """
    proposer_prompt = get_proposer_prompt(prompt, score, weak_cases, history)
    new_prompt = _route_call(proposer_prompt, model, temperature=0.7)
    return new_prompt
