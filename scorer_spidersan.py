"""scorer_spidersan.py — Promptclimb scorer for spidersan playbook optimization.

Evaluates whether the LLM response to a gitops scenario:
1. References the correct spidersan commands (must_mention match)
2. Avoids irrelevant commands (must_not_mention penalty)
3. Uses proper tier terminology (TIER 1/2/3 when context has conflicts)
4. Gives structured, actionable advice (not vague prose)

Gold cases are in gold/spidersan_maze/cases.json.

Usage:
    phc run --prompt prompt.md --eval scorer_spidersan.py --gold gold/spidersan_maze \
        --iterations 50 --model http://127.0.0.1:1234/v1 \
        --proposer http://127.0.0.1:1234/v1
"""

import json
import os
import re
import time
import requests

EXECUTOR_URL = os.environ.get("SPIDERSAN_LLM_URL", "http://127.0.0.1:1234")
EXECUTOR_MODEL = os.environ.get("SPIDERSAN_LLM_MODEL", "gemma-4-27b-it")


def _generate(system: str, user: str) -> str:
    """Call LLM with system + user messages, return response text."""
    for attempt in range(3):
        try:
            resp = requests.post(
                f"{EXECUTOR_URL}/v1/chat/completions",
                json={
                    "model": EXECUTOR_MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 800,
                },
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                return f"[ERROR: {e}]"
    return "[ERROR: unreachable]"


def _build_user_message(case: dict) -> str:
    """Build user message from scenario + context."""
    parts = [case["scenario"]]
    ctx = case.get("context", {})
    if ctx:
        parts.append(f"\nRepository context: {json.dumps(ctx, indent=2)}")
    return "\n".join(parts)


def _score_response(response: str, case: dict) -> dict:
    """Score a single LLM response against a gold case.

    Returns dict with component scores and details.
    """
    response_lower = response.lower()
    details = {}

    # 1. must_mention hits (0-1, weighted 0.50)
    must_mention = case.get("must_mention", [])
    if must_mention:
        hits = sum(1 for term in must_mention if term.lower() in response_lower)
        mention_score = hits / len(must_mention)
        details["must_mention"] = {
            "hits": hits,
            "total": len(must_mention),
            "missed": [t for t in must_mention if t.lower() not in response_lower],
        }
    else:
        mention_score = 1.0

    # 2. must_not_mention penalties (0-1, weighted 0.15)
    must_not = case.get("must_not_mention", [])
    if must_not:
        violations = sum(1 for term in must_not if term.lower() in response_lower)
        penalty_score = 1.0 - (violations / len(must_not))
        details["must_not_mention"] = {
            "violations": violations,
            "total": len(must_not),
            "violated": [t for t in must_not if t.lower() in response_lower],
        }
    else:
        penalty_score = 1.0

    # 3. command coverage — expected_commands actually present (0-1, weighted 0.20)
    expected = case.get("expected_commands", [])
    if expected:
        cmd_hits = 0
        for cmd in expected:
            # Match exact command or key substrings
            cmd_parts = cmd.replace("spidersan ", "").split()
            key = cmd_parts[0] if cmd_parts else cmd
            if key in response_lower or cmd.lower() in response_lower:
                cmd_hits += 1
        cmd_score = cmd_hits / len(expected)
        details["commands"] = {"hits": cmd_hits, "total": len(expected)}
    else:
        cmd_score = 1.0

    # 4. structure bonus (0-1, weighted 0.10)
    # Reward structured output: numbered steps, bullet points, code blocks
    struct_signals = 0
    if re.search(r"^\d+\.", response, re.MULTILINE):
        struct_signals += 1
    if re.search(r"^[-*•]", response, re.MULTILINE):
        struct_signals += 1
    if "```" in response or "`spidersan" in response_lower:
        struct_signals += 1
    struct_score = min(struct_signals / 2, 1.0)

    # 5. tier awareness — when conflicts exist, should mention tiers (0-1, weighted 0.05)
    ctx = case.get("context", {})
    conflicts = ctx.get("conflicts", {})
    has_conflicts = any(conflicts.get(f"tier{i}", 0) > 0 for i in (1, 2, 3))
    if has_conflicts:
        tier_score = 1.0 if re.search(r"tier\s*[123]", response_lower) else 0.0
    else:
        tier_score = 1.0  # no conflicts → no tier needed

    # Weighted composite
    total = (
        mention_score * 0.50
        + penalty_score * 0.15
        + cmd_score * 0.20
        + struct_score * 0.10
        + tier_score * 0.05
    )

    details["scores"] = {
        "must_mention": round(mention_score, 3),
        "penalty": round(penalty_score, 3),
        "commands": round(cmd_score, 3),
        "structure": round(struct_score, 3),
        "tier": round(tier_score, 3),
        "total": round(total, 4),
    }

    return details


def score(prompt_text: str, gold_cases: list) -> float:
    """Evaluate prompt against all gold cases. Returns 0.0-1.0.

    This is the entry point that promptclimb calls.
    """
    if not gold_cases:
        return 0.0

    # Handle gold_cases format — could be list of dicts or a flat list
    cases = gold_cases
    if isinstance(cases, list) and len(cases) == 1 and isinstance(cases[0], list):
        cases = cases[0]

    scores = []
    for case in cases:
        if not isinstance(case, dict):
            continue

        user_msg = _build_user_message(case)
        response = _generate(prompt_text, user_msg)

        if response.startswith("[ERROR"):
            scores.append(0.0)
            continue

        result = _score_response(response, case)
        total = result["scores"]["total"]
        scores.append(total)

        name = case.get("name", "?")
        print(f"  [{name}] score={total:.3f} | mention={result['scores']['must_mention']:.2f} "
              f"cmds={result['scores']['commands']:.2f} "
              f"struct={result['scores']['structure']:.2f}")

    return sum(scores) / len(scores) if scores else 0.0
