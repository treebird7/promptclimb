"""Tests for the proposer module — contamination stripping and prompt generation."""

from promptclimb.proposer import strip_contamination, get_proposer_prompt


def test_strip_preamble():
    raw = "Here's the improved prompt:\n\nClassify the sentiment."
    assert strip_contamination(raw) == "Classify the sentiment."


def test_strip_heres_revised():
    raw = "Here is the revised prompt:\nDo the thing.\nDo it well."
    assert strip_contamination(raw) == "Do the thing.\nDo it well."


def test_strip_markdown_fences():
    raw = "```\nClassify the sentiment.\n```"
    assert strip_contamination(raw) == "Classify the sentiment."


def test_strip_markdown_fences_with_lang():
    raw = "```text\nClassify the sentiment.\n```"
    assert strip_contamination(raw) == "Classify the sentiment."


def test_strip_trailing_explanation():
    raw = "Classify the sentiment.\n\nKey changes:\n- Added examples"
    assert strip_contamination(raw) == "Classify the sentiment."


def test_strip_combined():
    raw = (
        "Here's the improved prompt:\n"
        "```\n"
        "Classify the sentiment of this text.\n"
        "Return positive, negative, or neutral.\n"
        "```\n"
        "Changes made:\n"
        "- Added output format"
    )
    result = strip_contamination(raw)
    assert result == "Classify the sentiment of this text.\nReturn positive, negative, or neutral."


def test_clean_prompt_unchanged():
    raw = "Classify the sentiment.\nReturn one of: positive, negative, neutral."
    assert strip_contamination(raw) == raw


def test_empty_string():
    assert strip_contamination("") == ""


def test_proposer_prompt_includes_score():
    result = get_proposer_prompt("My prompt", 0.65, [], [])
    assert "0.6500" in result
    assert "My prompt" in result


def test_proposer_prompt_includes_weak_cases():
    weak = [{"input": "test input", "expected": "positive", "_score": 0.2}]
    result = get_proposer_prompt("My prompt", 0.5, weak, [])
    assert "test input" in result
    assert "0.2" in result


def test_proposer_prompt_includes_history():
    history = [{"score": 0.4}, {"score": 0.6}, {"score": 0.5}]
    result = get_proposer_prompt("My prompt", 0.6, [], history)
    # History should be sorted worst→best (OPRO pattern)
    lines = result.split("\n")
    score_lines = [l for l in lines if "score=" in l]
    scores = [float(l.strip().split("=")[1]) for l in score_lines]
    assert scores == sorted(scores)
