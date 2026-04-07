"""Tests for the HillClimber core loop — uses mock scorer/proposer."""

import json
import os
import tempfile
from unittest.mock import patch

from promptclimb.climber import HillClimber


def _make_test_env(prompt_text="Classify sentiment.", cases=None):
    """Create temp dirs with prompt file and gold cases."""
    tmpdir = tempfile.mkdtemp()
    prompt_path = os.path.join(tmpdir, "prompt.txt")
    gold_dir = os.path.join(tmpdir, "gold")
    output_dir = os.path.join(tmpdir, "results")
    os.makedirs(gold_dir)

    with open(prompt_path, "w") as f:
        f.write(prompt_text)

    if cases is None:
        cases = [
            {"input": "I love this", "expected": "positive"},
            {"input": "I hate this", "expected": "negative"},
        ]
    for i, case in enumerate(cases):
        with open(os.path.join(gold_dir, f"case_{i:02d}.json"), "w") as f:
            json.dump(case, f)

    return prompt_path, gold_dir, output_dir


def test_eval_calls_scorer():
    prompt_path, gold_dir, output_dir = _make_test_env()

    def mock_scorer(prompt, cases):
        return 0.75

    climber = HillClimber(
        prompt_path=prompt_path,
        scorer=mock_scorer,
        gold_dir=gold_dir,
        output_dir=output_dir,
    )
    score = climber.eval()
    assert score == 0.75


def test_run_keeps_improvements():
    prompt_path, gold_dir, output_dir = _make_test_env()

    call_count = {"n": 0}

    def improving_scorer(prompt, cases):
        call_count["n"] += 1
        # Baseline returns 0.5, then each mutation scores higher
        if "improved" in prompt:
            return 0.8
        return 0.5

    with patch("promptclimb.climber.propose") as mock_propose:
        mock_propose.return_value = "improved prompt"
        climber = HillClimber(
            prompt_path=prompt_path,
            scorer=improving_scorer,
            gold_dir=gold_dir,
            output_dir=output_dir,
        )
        result = climber.run(max_iterations=3)

    assert result.best_score == 0.8
    assert result.n_keeps >= 1
    assert os.path.exists(os.path.join(output_dir, "prompt.best.txt"))


def test_run_reverts_bad_proposals():
    prompt_path, gold_dir, output_dir = _make_test_env()

    def constant_scorer(prompt, cases):
        return 0.5

    with patch("promptclimb.climber.propose") as mock_propose:
        mock_propose.return_value = "worse prompt"
        climber = HillClimber(
            prompt_path=prompt_path,
            scorer=constant_scorer,
            gold_dir=gold_dir,
            output_dir=output_dir,
        )
        result = climber.run(max_iterations=3)

    assert result.best_score == 0.5
    assert result.n_keeps == 0
    assert result.n_reverts == 3


def test_rejects_empty_proposals():
    prompt_path, gold_dir, output_dir = _make_test_env()

    def scorer(prompt, cases):
        return 0.5

    with patch("promptclimb.climber.propose") as mock_propose:
        mock_propose.return_value = ""
        climber = HillClimber(
            prompt_path=prompt_path,
            scorer=scorer,
            gold_dir=gold_dir,
            output_dir=output_dir,
        )
        result = climber.run(max_iterations=3)

    assert result.n_rejects == 3
    assert result.n_keeps == 0


def test_early_stop():
    prompt_path, gold_dir, output_dir = _make_test_env()

    def scorer(prompt, cases):
        return 0.5

    with patch("promptclimb.climber.propose") as mock_propose:
        mock_propose.return_value = "some different prompt text here"
        climber = HillClimber(
            prompt_path=prompt_path,
            scorer=scorer,
            gold_dir=gold_dir,
            output_dir=output_dir,
            early_stop_after=5,
        )
        result = climber.run(max_iterations=100)

    # Should stop well before 100 iterations
    total = result.n_keeps + result.n_reverts + result.n_rejects
    assert total <= 6  # 5 reverts + maybe 1 extra before check


def test_validate_rejects_identical():
    prompt_path, gold_dir, output_dir = _make_test_env()

    def scorer(prompt, cases):
        return 0.5

    with patch("promptclimb.climber.propose") as mock_propose:
        # Return the exact same prompt
        mock_propose.return_value = "Classify sentiment."
        climber = HillClimber(
            prompt_path=prompt_path,
            scorer=scorer,
            gold_dir=gold_dir,
            output_dir=output_dir,
        )
        result = climber.run(max_iterations=3)

    assert result.n_rejects == 3


def test_results_tsv_written():
    prompt_path, gold_dir, output_dir = _make_test_env()

    def scorer(prompt, cases):
        return 0.5

    with patch("promptclimb.climber.propose") as mock_propose:
        mock_propose.return_value = "different prompt text"
        climber = HillClimber(
            prompt_path=prompt_path,
            scorer=scorer,
            gold_dir=gold_dir,
            output_dir=output_dir,
        )
        climber.run(max_iterations=2)

    tsv_path = os.path.join(output_dir, "results.tsv")
    assert os.path.exists(tsv_path)
    with open(tsv_path) as f:
        lines = f.readlines()
    # Header + baseline + 2 iterations
    assert len(lines) == 4


def test_load_jsonl_cases():
    tmpdir = tempfile.mkdtemp()
    prompt_path = os.path.join(tmpdir, "prompt.txt")
    gold_dir = os.path.join(tmpdir, "gold")
    os.makedirs(gold_dir)

    with open(prompt_path, "w") as f:
        f.write("test prompt")

    with open(os.path.join(gold_dir, "cases.jsonl"), "w") as f:
        f.write('{"input": "a", "expected": "1"}\n')
        f.write('{"input": "b", "expected": "2"}\n')

    climber = HillClimber(
        prompt_path=prompt_path,
        scorer=lambda p, c: 0.5,
        gold_dir=gold_dir,
    )
    assert len(climber.gold_cases) == 2
