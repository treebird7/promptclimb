from typing import Callable, List, Dict
import numpy as np
from ..backends.openai import get_embedding, call_model


def cosine_similarity(
    model: str = "text-embedding-3-small",
) -> Callable[[str, List[Dict]], float]:
    """
    Returns a scorer function that calculates the cosine similarity between
    the model's output and the expected output.
    """

    def scorer(prompt: str, cases: List[Dict]) -> float:
        total_score = 0
        for case in cases:
            output = call_model(prompt + "\n\nInput: " + case["input"], model)

            output_embedding = get_embedding(output, model)
            expected_embedding = get_embedding(case["expected"], model)

            if output_embedding and expected_embedding:
                similarity = np.dot(output_embedding, expected_embedding) / (
                    np.linalg.norm(output_embedding)
                    * np.linalg.norm(expected_embedding)
                )
                total_score += (similarity + 1) / 2  # Normalize to 0-1 range

        return total_score / len(cases) if cases else 0.0

    return scorer
