import os
from promptclimb import call_model

LABELS = ["positive", "negative", "neutral"]


def score(prompt: str, cases: list[dict]) -> float:
    correct = 0
    model = os.environ.get("PHC_MODEL", "openai:gpt-4o-mini")
    for case in cases:
        result = call_model(prompt + "\n\nText: " + case["input"], model)
        predicted = result.strip().lower()
        if predicted == case["expected"].lower():
            correct += 1
    return correct / len(cases) if cases else 0.0
