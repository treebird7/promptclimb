from typing import Callable, List, Dict
import os
import json
from .proposer import propose
from .results import ResultsWriter


class HillClimber:
    def __init__(
        self,
        prompt_path: str,
        scorer: Callable[[str, List[Dict]], float],
        gold_dir: str,
        model: str = "openai:gpt-4o-mini",
        proposer_model: str = None,
        output_dir: str = "results/",
    ):
        self.prompt_path = prompt_path
        with open(prompt_path, "r") as f:
            self.initial_prompt = f.read()
        self.scorer = scorer
        self.gold_cases = self._load_gold_cases(gold_dir)
        self.model = model
        self.proposer_model = proposer_model or model
        self.results_writer = ResultsWriter(output_dir, self.initial_prompt)
        os.environ["PHC_MODEL"] = self.model

    def _load_gold_cases(self, gold_dir: str) -> List[Dict]:
        cases = []
        for filename in os.listdir(gold_dir):
            if filename.endswith(".json") or filename.endswith(".jsonl"):
                filepath = os.path.join(gold_dir, filename)
                with open(filepath, "r") as f:
                    if filename.endswith(".jsonl"):
                        for line in f:
                            cases.append(json.loads(line))
                    else:
                        cases.append(json.load(f))
        return cases

    def run(self, max_iterations: int = 50):
        print(f"Starting hill-climbing for {self.prompt_path}...")

        prompt = self.initial_prompt
        score_0 = self.scorer(prompt, self.gold_cases)
        best_score = score_0
        history = []

        print(f"phc: baseline {best_score:.4f} ({len(self.gold_cases)} cases)")
        self.results_writer.append_row(0, score_0, best_score, "baseline")

        for i in range(1, max_iterations + 1):
            # TODO: Add weak cases detection
            new_prompt = propose(prompt, best_score, [], history, self.proposer_model)

            if not new_prompt or len(new_prompt) < 10:
                print(f"phc: iter {i:2d}  REJECT (bad proposal)")
                self.results_writer.append_row(i, 0, best_score, "reject")
                continue

            score_i = self.scorer(new_prompt, self.gold_cases)

            delta = score_i - best_score
            if score_i > best_score:
                prompt = new_prompt
                best_score = score_i
                status = "KEEP"
                print(f"phc: iter {i:2d}  {score_i:.4f}  {status}  +{delta:.4f}")
                self.results_writer.save_best_prompt(prompt)

            else:
                status = "REVERT"
                print(f"phc: iter {i:2d}  {score_i:.4f}  {status}")

            self.results_writer.append_row(i, score_i, best_score, status)
            history.append({"prompt": new_prompt, "score": score_i})

        print(
            f"phc: improved {score_0:.4f} -> {best_score:.4f} (+{best_score - score_0:.4f}) in {max_iterations} iterations"
        )
        print(f"phc: wrote {self.results_writer.output_dir}/prompt.best.txt")

    def eval(self):
        print(f"Evaluating {self.prompt_path}...")
        score = self.scorer(self.initial_prompt, self.gold_cases)
        print(f"Score: {score:.4f}")
        return score
