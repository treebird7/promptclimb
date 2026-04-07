# SPEC: prompt-hill-climber

**An open-source tool that automatically improves LLM prompts through hill-climbing.**

Give it a prompt, a scoring function, and test data. It does the rest.

---

## One-liner

```bash
phc run --prompt prompt.txt --eval eval.py --gold tests/ --iterations 50
```

---

## Problem

Developers hand-tune prompts by vibes. There's no systematic way to iterate. When they do iterate, they optimize against noisy eval data and hit false ceilings. They think the model can't do better — the measurement is the bottleneck.

## Solution

A CLI tool that runs a propose → evaluate → keep/revert loop on any LLM prompt. The user defines what "better" means (a scoring function). The tool handles mutation, comparison, and rollback.

---

## Core Concepts

| Concept | What the user provides |
|---------|----------------------|
| **Prompt** | A text file. Can be any format — system prompt, chat template, structured template with `{variables}`. |
| **Scorer** | A Python function: `score(prompt: str, test_cases: list[dict]) -> float`. Returns 0.0–1.0. The user defines what "good" means. |
| **Test cases** | A directory of JSON/JSONL files. Each case has an `input` and an `expected` (gold). |
| **Proposer** | An LLM that reads the current prompt + scores and suggests a mutation. Built-in default uses the same model. Can be overridden to use a smarter model. |

---

## Interface

### CLI

```bash
# Basic run
phc run --prompt prompt.txt --eval score.py --gold tests/

# With options
phc run \
  --prompt prompt.txt \
  --eval score.py \
  --gold tests/ \
  --iterations 50 \
  --model openai:gpt-4o-mini \
  --proposer openai:gpt-4o \
  --output results/

# Just evaluate current prompt (no mutation)
phc eval --prompt prompt.txt --eval score.py --gold tests/

# Analyze a completed run
phc analyze --results results/
```

### Python API

```python
from prompt_hill_climber import HillClimber

def my_scorer(prompt: str, cases: list[dict]) -> float:
    """User-defined scoring function."""
    correct = 0
    for case in cases:
        output = call_my_llm(prompt, case["input"])
        if matches(output, case["expected"]):
            correct += 1
    return correct / len(cases)

climber = HillClimber(
    prompt_path="prompt.txt",
    scorer=my_scorer,
    gold_dir="tests/",
    model="openai:gpt-4o-mini",      # executor
    proposer="openai:gpt-4o",         # proposer (optional, defaults to model)
)

result = climber.run(max_iterations=50)
print(f"Start: {result.start_score:.4f} → Final: {result.best_score:.4f}")
print(f"Improvements: {result.n_keeps}/{result.n_iterations}")
```

---

## Scorer Contract

The scorer is the only thing the user MUST write. Everything else has defaults.

```python
# score.py — minimal example
def score(prompt: str, cases: list[dict]) -> float:
    """
    Args:
        prompt: The current prompt string.
        cases: List of dicts, each with at least "input" and "expected".

    Returns:
        Float between 0.0 and 1.0. Higher is better.
    """
    ...
```

### Built-in scorers (optional convenience)

```python
from prompt_hill_climber.scorers import cosine_similarity, exact_match, contains_all

# Embedding similarity between output and expected
scorer = cosine_similarity(model="text-embedding-3-small")

# Exact string match
scorer = exact_match()

# All expected strings appear in output
scorer = contains_all()
```

---

## Test Case Format

```jsonl
{"input": "Extract entities from: 'Alice works at Acme Corp in NYC'", "expected": ["Alice", "Acme Corp", "NYC"]}
{"input": "Summarize: ...", "expected": "A one-paragraph summary of..."}
```

Or as a directory of JSON files:
```
tests/
  case_01.json    # {"input": "...", "expected": "..."}
  case_02.json
  ...
```

The tool passes the full list to the scorer. The scorer decides how to use `expected` — exact match, semantic similarity, checklist, whatever.

---

## Proposer

The proposer reads:
1. The current prompt
2. The current score
3. Per-case scores (which cases are weak)
4. History of recent mutations and their outcomes

And outputs: a mutated prompt.

### Built-in proposer prompt (simplified)

```
You are a prompt engineer. Your job is to improve this prompt.

Current score: {score}/1.0
Weakest cases: {weak_cases}
Recent history: {history}

Current prompt:
---
{prompt}
---

Output an improved version of the entire prompt. Focus on the weakest cases.
Do not explain your changes — just output the new prompt.
```

### Proposer model selection

```yaml
# phc.yaml
proposer:
  model: openai:gpt-4o        # smart model for proposals
  temperature: 0.7             # some creativity
executor:
  model: ollama:llama3.2       # cheap model for execution
  temperature: 0               # deterministic scoring
```

The key insight: **the proposer runs once per iteration, the executor runs N times (once per test case)**. Use a smart expensive model for proposals, a cheap fast model for execution.

---

## Loop Algorithm

```
1. BASELINE
   score_0 = scorer(prompt, cases)
   best = score_0

2. FOR i in 1..max_iterations:
   a. PROPOSE
      new_prompt = proposer(prompt, best, weak_cases, history)

   b. VALIDATE
      if new_prompt is malformed or too short: SKIP

   c. EVALUATE
      score_i = scorer(new_prompt, cases)

   d. DECIDE
      if score_i > best:
          prompt = new_prompt
          best = score_i
          LOG "KEEP +{delta}"
      else:
          LOG "REVERT {delta}"

   e. RECORD
      append to results.tsv

3. OUTPUT
   Write best prompt to prompt.best.txt
   Write results to results.tsv
   Write score curve to scores.png (if matplotlib available)
```

---

## Output

```
results/
  prompt.best.txt          # Best prompt found
  prompt.initial.txt       # Original prompt (for diff)
  results.tsv              # Per-iteration: iter, score, best, status, timestamp
  history.jsonl            # Full mutation history with proposer reasoning
  scores.png               # Score curve plot (optional)
  case_scores.json         # Per-case breakdown at best prompt
```

---

## Configuration

```yaml
# phc.yaml (optional — all fields have CLI/env defaults)
prompt: prompt.txt
eval: score.py
gold: tests/

iterations: 50

executor:
  model: ollama:llama3.2         # or openai:gpt-4o-mini, anthropic:haiku, etc.
  temperature: 0
  timeout: 60

proposer:
  model: openai:gpt-4o           # defaults to executor model if not set
  temperature: 0.7

output: results/

# Advanced
backup_every: 5                   # git commit every N keeps
section_targeting: true           # proposer focuses on weakest cases
early_stop_after: 20              # stop after N consecutive reverts
```

---

## Model Backends

Unified interface, pluggable backends:

```
openai:gpt-4o-mini          # OpenAI API
anthropic:haiku              # Anthropic API
ollama:llama3.2              # Local Ollama
lmstudio:gemma-4-26b         # Local LMStudio (OpenAI-compatible)
http://localhost:8082         # Raw OpenAI-compatible endpoint
```

The tool ships with `openai` and `ollama` backends. Others via plugins or raw URL.

---

## Example: Improving a Classification Prompt

```python
# score.py
import json
from prompt_hill_climber import call_model

LABELS = ["positive", "negative", "neutral"]

def score(prompt: str, cases: list[dict]) -> float:
    correct = 0
    for case in cases:
        result = call_model(prompt + "\n\nText: " + case["input"])
        predicted = result.strip().lower()
        if predicted == case["expected"].lower():
            correct += 1
    return correct / len(cases)
```

```bash
phc run --prompt classify.txt --eval score.py --gold sentiment_tests/ \
  --model ollama:llama3.2 --proposer openai:gpt-4o --iterations 30
```

Output:
```
phc: baseline 0.6400 (25 cases)
phc: iter  1  0.6800  KEEP  +0.0400  (improved few-shot examples)
phc: iter  2  0.6400  REVERT
phc: iter  3  0.7200  KEEP  +0.0400  (added edge case instruction)
...
phc: iter 30  0.8400  best
phc: improved 0.6400 → 0.8400 (+0.2000) in 30 iterations, 8 keeps
phc: wrote results/prompt.best.txt
```

---

## What It Is NOT

- **Not a fine-tuning tool.** It optimizes prompts, not model weights.
- **Not an eval framework.** The user writes the scorer. The tool just loops.
- **Not an agent.** No planning, no tool use, no multi-step reasoning. Just hill-climbing.
- **Not magic.** Garbage gold data = garbage ceiling (the fidelity ceiling — see THESIS).

---

## Package Structure

```
prompt-hill-climber/
  pyproject.toml
  src/
    prompt_hill_climber/
      __init__.py
      cli.py              # Click/Typer CLI
      climber.py           # HillClimber class
      proposer.py          # Built-in proposer prompt + logic
      backends/
        __init__.py
        openai.py          # OpenAI-compatible (also LMStudio)
        ollama.py          # Ollama
        anthropic.py       # Anthropic
      scorers/
        __init__.py
        cosine.py          # Embedding similarity
        exact.py           # Exact match
        contains.py        # Substring checklist
      results.py           # TSV + JSONL writer
      plot.py              # Optional matplotlib score curve
  tests/
  examples/
    classification/
    extraction/
    summarization/
  README.md
  LICENSE                  # MIT
```

---

## Design Principles

1. **Scorer is the only required code.** Everything else has sensible defaults.
2. **Works offline.** Ollama + local scorer = fully local, no API keys.
3. **Proposer ≠ executor.** Use a smart model to think, a cheap model to do.
4. **No framework lock-in.** The scorer is a plain Python function. No decorators, no base classes, no registration.
5. **Transparent.** Every iteration logged. Every mutation saved. Full history in JSONL.
6. **The tool is dumb on purpose.** Hill-climbing is the simplest optimization that works. No genetic algorithms, no Bayesian optimization, no neural architecture search. Just: try something, is it better, keep or revert.

---

## Prior Art / Differentiation

| Tool | What it does | How PHC differs |
|------|-------------|-----------------|
| DSPy | Optimizes LLM pipelines via compilation | PHC is simpler — just prompts, no pipeline abstraction |
| PromptFoo | Eval framework for prompts | PHC adds the optimization loop — eval + improve, not just eval |
| TextGrad | Gradient-based prompt optimization | PHC is gradient-free — no backprop, just hill-climbing |
| OPRO (Google) | LLM-based prompt optimization | Same idea, but PHC is a practical CLI tool, not a paper |

**PHC's niche:** the simplest possible tool that actually works. Zero ML knowledge required. If you can write a Python function that returns a float, you can optimize your prompt.

---

## MVP Scope (v0.1)

Ship the smallest useful thing:

- [ ] `HillClimber` class with `run()` and `eval()`
- [ ] CLI: `phc run`, `phc eval`
- [ ] OpenAI-compatible backend (covers OpenAI, LMStudio, vLLM, llama.cpp)
- [ ] Built-in proposer prompt
- [ ] TSV results output
- [ ] `cosine_similarity` built-in scorer
- [ ] One example (classification)
- [ ] README with 5-minute quickstart

**Not in v0.1:** Ollama backend, plotting, phc.yaml config file, section targeting, git backup, plugins.

---

## Name Candidates

- `prompt-hill-climber` / `phc` — descriptive
- `promptclimb` — shorter
- `climbr` — catchy
- `hillprompt` — meh
- `promptforge` — too grandiose

Recommendation: **`promptclimb`** — short, memorable, pip-installable.

---

*Spec by Yosef, 2026-04-07. Born from the selfimprove fidelity ceiling thesis.*
