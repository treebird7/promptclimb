# promptclimb

An open-source tool that automatically improves LLM prompts through hill-climbing.

Give it a prompt, a scoring function, and test data. It does the rest.

## Quickstart (5 minutes)

1.  **Install the package:**

    ```bash
    git clone https://github.com/example/promptclimb.git
    cd promptclimb
    python3 -m venv venv
    source venv/bin/activate
    pip install -e .
    ```

2.  **Set your OpenAI API key:**

    Create a `.env` file in the project root and add your API key:

    ```
    OPENAI_API_KEY="sk-..."
    ```

3.  **Run the classification example:**

    ```bash
    phc run --prompt examples/classification/prompt.txt \
            --eval examples/classification/score.py \
            --gold examples/classification/tests/
    ```

    This will run the hill-climbing process and generate a `results/` directory with the improved prompt and detailed logs.

4.  **Check the results:**

    After the run, you'll find the best prompt in `results/prompt.best.txt` and the iteration history in `results/results.tsv`.

## Usage

### `phc run`

Run the prompt hill-climbing optimization.

```bash
phc run \
  --prompt prompt.txt \
  --eval score.py \
  --gold tests/ \
  --iterations 50 \
  --model openai:gpt-4o-mini \
  --proposer openai:gpt-4o \
  --output results/
```

### `phc eval`

Evaluate the current prompt without mutation.

```bash
phc eval --prompt prompt.txt --eval score.py --gold tests/
```
