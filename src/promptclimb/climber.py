from typing import Callable, List, Dict, Optional
import os
import json
from .proposer import propose
from .results import ResultsWriter


class RunResult:
    """Result of a hill-climbing run."""

    def __init__(
        self,
        start_score: float,
        best_score: float,
        n_iterations: int,
        n_keeps: int,
        n_reverts: int,
        n_rejects: int,
        best_prompt: str,
    ):
        self.start_score = start_score
        self.best_score = best_score
        self.n_iterations = n_iterations
        self.n_keeps = n_keeps
        self.n_reverts = n_reverts
        self.n_rejects = n_rejects
        self.best_prompt = best_prompt

    def __repr__(self):
        return (
            f"RunResult(start={self.start_score:.4f}, best={self.best_score:.4f}, "
            f"keeps={self.n_keeps}/{self.n_iterations})"
        )


class HillClimber:
    def __init__(
        self,
        prompt_path: str,
        scorer: Callable[[str, List[Dict]], float],
        gold_dir: str,
        model: str = "openai:gpt-4o-mini",
        proposer_model: str = None,
        output_dir: str = "results/",
        early_stop_after: int = 20,
    ):
        self.prompt_path = prompt_path
        with open(prompt_path, "r") as f:
            self.initial_prompt = f.read()
        self.scorer = scorer
        self.gold_cases = self._load_gold_cases(gold_dir)
        self.model = model
        self.proposer_model = proposer_model or model
        self.output_dir = output_dir
        self.early_stop_after = early_stop_after
        self.results_writer = ResultsWriter(output_dir, self.initial_prompt)
        os.environ["PHC_MODEL"] = self.model

    def _load_gold_cases(self, gold_dir: str) -> List[Dict]:
        cases = []
        for filename in sorted(os.listdir(gold_dir)):
            if filename.endswith(".json") or filename.endswith(".jsonl"):
                filepath = os.path.join(gold_dir, filename)
                with open(filepath, "r") as f:
                    if filename.endswith(".jsonl"):
                        for line in f:
                            line = line.strip()
                            if line:
                                cases.append(json.loads(line))
                    else:
                        cases.append(json.load(f))
        return cases

    def _score_per_case(
        self, prompt: str, cases: List[Dict]
    ) -> tuple[float, List[Dict]]:
        """Score prompt and annotate each case with its individual score.

        If the scorer returns a single float (the contract), we call it once
        for the aggregate. Per-case scoring is best-effort: we call the scorer
        once per case individually. If that fails or is too slow, we fall back
        to aggregate-only.
        """
        aggregate = self.scorer(prompt, cases)

        # Try per-case scoring for weak-case detection
        annotated = []
        try:
            for case in cases:
                case_score = self.scorer(prompt, [case])
                if isinstance(case, dict):
                    annotated.append({**case, "_score": round(case_score, 4)})
                else:
                    annotated.append({"_data": case, "_score": round(case_score, 4)})
        except Exception:
            # Per-case scoring failed — return unannotated cases
            for case in cases:
                if isinstance(case, dict):
                    annotated.append({**case, "_score": "?"})
                else:
                    annotated.append({"_data": case, "_score": "?"})

        return aggregate, annotated

    def _find_weak_cases(self, annotated_cases: List[Dict], n: int = 5) -> List[Dict]:
        """Return the N lowest-scoring cases for the proposer to focus on."""
        scored = [c for c in annotated_cases if isinstance(c.get("_score"), (int, float))]
        scored.sort(key=lambda c: c["_score"])
        return scored[:n]

    def _validate_proposal(self, new_prompt: str, current_prompt: str) -> Optional[str]:
        """Validate a proposed prompt. Returns rejection reason or None if valid."""
        if not new_prompt:
            return "empty output"
        if len(new_prompt) < 10:
            return "too short"
        # Reject if proposal is identical
        if new_prompt.strip() == current_prompt.strip():
            return "identical to current"
        # Reject if suspiciously small (less than 20% of current)
        if len(new_prompt) < len(current_prompt) * 0.2:
            return f"too small ({len(new_prompt)} chars vs {len(current_prompt)})"
        # Structural check: if original has key markers, proposal must too
        for marker in ["## USER TEMPLATE", "{content}", "{title}"]:
            if marker in current_prompt and marker not in new_prompt:
                return f"missing structural marker: {marker}"
        return None

    def run(self, max_iterations: int = 50) -> RunResult:
        print(f"phc: starting hill-climb for {self.prompt_path}")
        print(f"phc: executor={self.model}  proposer={self.proposer_model}")
        print(f"phc: {len(self.gold_cases)} test cases, max {max_iterations} iterations")

        prompt = self.initial_prompt
        score_0, annotated = self._score_per_case(prompt, self.gold_cases)
        best_score = score_0
        best_prompt = prompt
        # Keep only recent history to bound memory (last 10 entries)
        history = []
        consecutive_reverts = 0
        n_keeps = 0
        n_reverts = 0
        n_rejects = 0

        weak_cases = self._find_weak_cases(annotated)
        print(f"phc: baseline {best_score:.4f} ({len(self.gold_cases)} cases)")
        self.results_writer.append_row(0, score_0, best_score, "baseline")

        for i in range(1, max_iterations + 1):
            # Plateau detection: stop after N consecutive non-improvements
            if consecutive_reverts >= self.early_stop_after:
                print(
                    f"phc: early stop — {consecutive_reverts} consecutive "
                    f"reverts (threshold: {self.early_stop_after})"
                )
                break

            new_prompt = propose(
                prompt, best_score, weak_cases, history, self.proposer_model
            )

            # Validate proposal
            rejection = self._validate_proposal(new_prompt, prompt)
            if rejection:
                n_rejects += 1
                consecutive_reverts += 1
                print(f"phc: iter {i:3d}  REJECT ({rejection})")
                self.results_writer.append_row(i, 0, best_score, f"reject:{rejection}")
                continue

            score_i, annotated = self._score_per_case(new_prompt, self.gold_cases)

            delta = score_i - best_score
            if score_i > best_score:
                prompt = new_prompt
                best_score = score_i
                best_prompt = new_prompt
                n_keeps += 1
                consecutive_reverts = 0
                weak_cases = self._find_weak_cases(annotated)
                print(f"phc: iter {i:3d}  {score_i:.4f}  KEEP   +{delta:.4f}")
                self.results_writer.save_best_prompt(prompt)
                self.results_writer.append_row(i, score_i, best_score, "keep")
            else:
                n_reverts += 1
                consecutive_reverts += 1
                print(f"phc: iter {i:3d}  {score_i:.4f}  REVERT  {delta:.4f}")
                self.results_writer.append_row(i, score_i, best_score, "revert")

            # Bound history to last 10 entries
            history.append({"score": score_i})
            if len(history) > 10:
                history = history[-10:]

        total = n_keeps + n_reverts + n_rejects
        print(f"phc: done — {score_0:.4f} → {best_score:.4f} (+{best_score - score_0:.4f})")
        print(f"phc: {n_keeps} keeps, {n_reverts} reverts, {n_rejects} rejects in {total} iterations")
        print(f"phc: best prompt → {self.output_dir}/prompt.best.txt")

        return RunResult(
            start_score=score_0,
            best_score=best_score,
            n_iterations=total,
            n_keeps=n_keeps,
            n_reverts=n_reverts,
            n_rejects=n_rejects,
            best_prompt=best_prompt,
        )

    def eval(self) -> float:
        print(f"phc: evaluating {self.prompt_path}...")
        score = self.scorer(self.initial_prompt, self.gold_cases)
        print(f"phc: score {score:.4f} ({len(self.gold_cases)} cases)")
        return score
