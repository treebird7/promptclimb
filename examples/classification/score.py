import sys
from pathlib import Path
import os

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from promptclimb.backends.openai import call_model

LABELS = ["positive", "negative", "neutral"]


def score(prompt: str, cases: list[dict]) -> float:
    correct = 0
    for case in cases:
        # It is important to set the model to be the same as the one used in the climber
        # We can get it from the environment variables
        model = os.environ.get("PHC_MODEL", "openai:gpt-4o-mini")
        result = call_model(prompt + "\n\nText: " + case["input"], model)
        predicted = result.strip().lower()
        if predicted == case["expected"].lower():
            correct += 1
    return correct / len(cases) if cases else 0.0
