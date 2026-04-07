# promptclimb

Automatically improve LLM prompts through hill-climbing.

Give it a prompt, a scoring function, and test data. It does the rest.

## What you should know first

**The loop is the test rig; the value is that, with the right rig, it finds principles that generalize.**

After 354 iterations of automated prompt optimization across 3 machines, we learned that the loop is most valuable as measurement infrastructure, not as the primary optimizer. The biggest gains come from choosing the right model, writing one good example, and fixing your scoring metric — not from running more iterations. But when evaluation, preprocessing, and search-space design are strong enough, the prompt principles the loop discovers transfer across model families (phi4-optimized prompts transferred +10% to Claude Sonnet, +8% to Haiku). [Read the full findings.](SPEC_prompt_hill_climber.md#design-principles)

Use `phc` to *measure and systematically improve* your prompts. Use your brain for the structural changes.

## Quickstart

```bash
git clone https://github.com/treebird7/promptclimb.git
cd promptclimb
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

Set your API key (or use a local model — no key needed):

```bash
# Option A: OpenAI
echo 'OPENAI_API_KEY="sk-..."' > .env

# Option B: Local Ollama (no key needed)
# Just have Ollama running with your model pulled
```

Run the classification example:

```bash
phc run --prompt examples/classification/prompt.txt \
        --eval examples/classification/score.py \
        --gold examples/classification/tests/
```

## Usage

### `phc run` — optimize a prompt

```bash
phc run \
  --prompt prompt.txt \
  --eval score.py \
  --gold tests/ \
  --iterations 50 \
  --model openai:gpt-4o-mini \
  --proposer openai:gpt-4o \
  --early-stop 20 \
  --output results/
```

**Key insight: use a smart model for proposals, a cheap model for execution.** The proposer runs once per iteration; the executor runs N times (once per test case). A $0.001 Claude Haiku proposal beats 20 iterations of a 4B local model proposing word swaps.

### `phc eval` — score without mutating

```bash
phc eval --prompt prompt.txt --eval score.py --gold tests/
```

### Python API

```python
from promptclimb import HillClimber

def my_scorer(prompt: str, cases: list[dict]) -> float:
    correct = sum(1 for c in cases if run_llm(prompt, c["input"]) == c["expected"])
    return correct / len(cases)

climber = HillClimber(
    prompt_path="prompt.txt",
    scorer=my_scorer,
    gold_dir="tests/",
    model="ollama:llama3.2",
    proposer_model="openai:gpt-4o",
)
result = climber.run(max_iterations=50)
print(f"{result.start_score:.4f} → {result.best_score:.4f} ({result.n_keeps} keeps)")
```

## Supported backends

```
openai:gpt-4o-mini          # OpenAI API
openai:gpt-4o               # OpenAI API
anthropic:claude-haiku-4-5   # Anthropic API (pip install promptclimb[anthropic])
ollama:llama3.2              # Local Ollama
ollama:gemma3:4b             # Local Ollama
lmstudio:gemma-4-26b         # LMStudio (OpenAI-compatible)
http://localhost:8082         # Any OpenAI-compatible endpoint
```

## Writing a scorer

The scorer is the only code you must write. Everything else has defaults.

```python
# score.py
def score(prompt: str, cases: list[dict]) -> float:
    """
    Args:
        prompt: The current prompt text.
        cases: List of dicts with "input" and "expected" keys.
    Returns:
        Float between 0.0 and 1.0. Higher is better.
    """
    ...
```

Built-in scorers for common tasks:

```python
from promptclimb.scorers.cosine import cosine_similarity

scorer = cosine_similarity(model="text-embedding-3-small")
```

## Test case format

```json
{"input": "I love this product!", "expected": "positive"}
```

Put cases in a directory as `.json` or `.jsonl` files.

## Output

```
results/
  prompt.best.txt       # Best prompt found
  prompt.initial.txt    # Original (for diffing)
  results.tsv           # Per-iteration scores and status
```

## Features baked in from production experience

- **Contamination guard** — strips proposer meta-commentary ("Here's the improved prompt:") that would corrupt the prompt
- **Proposal validation** — rejects empty, too-short, identical, or suspiciously truncated proposals
- **Per-case weak spot detection** — identifies lowest-scoring test cases and feeds them to the proposer
- **OPRO-style history** — shows the proposer recent scores sorted worst→best so it sees the improvement trajectory
- **Early stop** — halts after N consecutive non-improvements (default 20) instead of grinding through reverts
- **Bounded history** — keeps only last 10 iterations in memory

## License

MIT
