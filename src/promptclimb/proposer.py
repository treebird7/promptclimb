import re


def _route_call(prompt: str, model: str, **kwargs) -> str:
    """Route to correct backend based on model prefix."""
    if model.startswith("anthropic:"):
        from .backends.anthropic import call_model
    elif model.startswith("ollama:"):
        from .backends.ollama import call_model
    else:
        from .backends.openai import call_model
    return call_model(prompt, model, **kwargs)


# Patterns that indicate proposer meta-commentary leaked into the output
_CONTAMINATION_PATTERNS = [
    # "Here's the improved prompt:", "Here is the revised prompt:", "Below is the new prompt:"
    re.compile(r"^(here'?s?|below is|here is|i'?ve|the following is|this is)\b.*(revised|improved|updated|new|modified)\b", re.IGNORECASE),
    # "Key changes:", "Changes made:", "Changes I made:"
    re.compile(r"^(key )?changes( made| I made)?:", re.IGNORECASE),
    # "Note:", "Explanation:", "Reasoning:", "Summary of changes:"
    re.compile(r"^(note|explanation|reasoning|summary of changes):", re.IGNORECASE),
]

_FENCE_MARKERS = {"```", "```text", "```markdown"}


def _is_meta(line: str) -> bool:
    """Check if a line is meta-commentary (contamination header or fence)."""
    stripped = line.strip()
    if stripped in _FENCE_MARKERS:
        return True
    return any(p.search(stripped) for p in _CONTAMINATION_PATTERNS)


def strip_contamination(text: str) -> str:
    """Remove proposer meta-commentary wrapping the actual prompt.

    LLMs often wrap their output in preamble ("Here's the improved prompt:")
    and postamble ("Key changes: ..."). This strips both.
    """
    lines = text.strip().splitlines()
    if not lines:
        return text

    # Forward pass: skip leading meta lines, fences, and blanks between them
    start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or _is_meta(stripped):
            start = i + 1
            continue
        break

    # Backward pass: skip trailing meta, fences, bullets after meta, and blanks
    end = len(lines)
    i = len(lines) - 1
    while i >= start:
        stripped = lines[i].strip()
        if (
            not stripped
            or stripped.startswith("- ")
            or _is_meta(stripped)
        ):
            end = i
            i -= 1
            continue
        break

    return "\n".join(lines[start:end]).strip()


def get_proposer_prompt(
    prompt: str, score: float, weak_cases: list, history: list
) -> str:
    """Build the meta-prompt that asks the proposer to mutate the current prompt.

    Uses OPRO-style worst→best ordering so the proposer sees the improvement
    trajectory and targets weak spots.
    """
    # Show history sorted worst→best (OPRO pattern: model sees trajectory)
    sorted_history = sorted(history[-8:], key=lambda h: h["score"])
    history_str = "\n".join(
        [f"  score={item['score']:.4f}" for item in sorted_history]
    ) if sorted_history else "  (no history yet)"

    weak_cases_str = ""
    if weak_cases:
        weak_cases_str = "These test cases score the lowest — focus your changes here:\n"
        for case in weak_cases[:5]:
            inp = case.get("input", "")[:80]
            exp = str(case.get("expected", ""))[:80]
            case_score = case.get("_score", "?")
            weak_cases_str += f"  - [{case_score}] input: {inp}...  expected: {exp}\n"
    else:
        weak_cases_str = "(No per-case breakdown available)"

    return f"""You are a prompt engineer. Your job is to improve the prompt below.

Current score: {score:.4f} / 1.0

Weak cases:
{weak_cases_str}

Recent scores (worst → best):
{history_str}

Current prompt:
---
{prompt}
---

Rules:
- Output ONLY the improved prompt. No explanation, no preamble, no commentary.
- Do not wrap your output in markdown fences.
- Make targeted, structural changes. Word swaps ("extract"→"retrieve") rarely help.
- If many cases score zero, the prompt may be missing permission to handle that format. Add explicit instructions.
- If scores are 0.4–0.7, add or improve examples.
- If scores are >0.7, make precise refinements to definitions or edge-case handling.

Output the complete improved prompt now:"""


def propose(
    prompt: str, score: float, weak_cases: list, history: list, model: str
) -> str:
    """Generate a mutated prompt using the proposer model."""
    proposer_prompt = get_proposer_prompt(prompt, score, weak_cases, history)
    raw = _route_call(proposer_prompt, model, temperature=0.7, max_tokens=4096)
    return strip_contamination(raw)
