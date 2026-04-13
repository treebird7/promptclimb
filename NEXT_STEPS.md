# Next Steps for PromptClimb

## What We've Accomplished

1. **Analyzed the PromptClimb codebase** and understood its hill-climbing optimization capabilities
2. **Examined the research paper** (The Single-Multi Evolution Loop for Self-Improving)
3. **Created a specialized prompt template** for extracting structured information from academic papers
4. **Set up gold standard examples** with the type of structured output we want to extract
5. **Documented a comprehensive use case** showing how PromptClimb can be applied to research prompt mining
6. **Identified the technical requirements** for running the optimization
7. **Completed spidersan playbook optimization** — first real-world PHC deployment (see `research_results/spidersan_playbook/`)
   - Gemma 4 26B as executor, tested Gemma/GPT-4o/Sonnet 4.6 as proposers
   - Best result: Sonnet 4.6 single-shot mutation → **0.972** peak, **0.938** mean (up from 0.895 baseline)
   - 18-scenario playbook deployed to spidersan production
   - Key finding: targeted single-shot mutation by a strong model beats iterative PHC with weaker proposer

## Key Learnings from Spidersan Campaign

1. **Model hierarchy matters more than iteration count** — Sonnet 4.6 > GPT-4o >> Gemma as proposer
2. **Single-shot targeted mutation can beat iterative optimization** when the engineer (human or AI) understands *why* specific cases fail
3. **Stochastic variance is the real enemy** — same prompt swings ±10% between runs; multi-eval averaging is essential
4. **Scorer design is the leverage point** — the 5-dimension scorer (must_mention, penalty, commands, structure, tier) revealed UX gaps in spidersan itself
5. **Dogfooding via PHC** — optimization loop surfaced CLI design issues (queen vs torrent confusion, advise vs inline advice)

## What's Needed to Complete the Task

To actually run the research prompt mining optimization on the user's paper, you would need:

### 1. API Credentials
PromptClimb requires access to LLMs for:
- **Proposer model**: Generates prompt variations (we used openai:gpt-4o in our setup)
- **Model for evaluation**: Tests the prompts (we used openai:gpt-4o-mini)
- **Optional local endpoints**: For extraction and embedding (as shown in scorer_extraction.py)

You would need to:
- Create a `.env` file in the project root with:
  ```
  OPENAI_API_KEY="your-openai-api-key-here"
  ```
- OR set the environment variable directly when running commands

### 2. Local LLM Endpoints (Optional)
The scorer_extraction.py is configured to work with local models:
- EXECUTOR_URL=http://localhost:8082/v1 (for extraction/generation)
- EMBEDDING_URL=http://192.168.1.157:8083/v1/embeddings (for embeddings)
- Models: gemma-4-26b-a4b-it (extraction) and nomic-embed-text (embeddings)

### 3. Properly Formatted Prompt
Our research_prompt_mining.txt already includes the necessary ## USER TEMPLATE section that the scorer expects.

### 4. Gold Standard Examples
We created section_1.json in the research_mining/gold/ directory with example extractions.

## The Command to Run

Once you have API credentials set up, you would run:

```bash
# Activate the virtual environment
source .venv/bin/activate

# Run the hill-climbing optimization
.venv/bin/phc run \
  --prompt research_prompt_mining.txt \
  --eval scorer_extraction.py \
  --gold /Users/freedbird/Dev/promptclimb/research_mining/gold \
  --iterations 20 \
  --model openai:gpt-4o-mini \
  --proposer openai:gpt-4o \
  --output research_prompt_results
```

## Expected Output

After successful completion, you would find in the research_prompt_results/ directory:
- `prompt.initial.txt`: Your original prompt
- `prompt.best.txt`: The optimized prompt after hill-climbing
- `results.tsv`: Iteration history showing score improvements
- `phc_run.log`: Detailed log of the optimization process

## Alternative Approach: Using Local Models Only

If you don't want to use OpenAI APIs, you could:
1. Modify scorer_extraction.py to use only local endpoints
2. Set EXECUTOR_URL and EMBEDDING_URL to your local LLM servers
3. Use empty or local model identifiers in the phc run command
4. Ensure your local models are capable of following the extraction instructions

## Benefits of Completing This Process

By running this optimization, you would obtain:
1. An automatically engineered prompt that maximally extracts the six types of information we specified from academic papers
2. A prompt that likely generalizes well to similar papers in the language model collaboration/systems domain
3. A demonstration of PromptClimb's capability for complex, structured information extraction tasks
4. A reusable tool for accelerating literature review and research synthesis workflows

## Troubleshooting Notes from Our Attempt

- The scorer requires the ## USER TEMPLATE section in the prompt to properly extract the user-guidance portion
- Empty scores (0.0000) typically indicate either:
  - API connection issues (missing/invalid credentials)
  - Prompt formatting problems preventing proper extraction
  - Scoring function not finding expected patterns in the output
- The torrent shredding mechanism handles long documents by chunking them at paragraph/sentence boundaries

This use case demonstrates PromptClimb's versatility beyond simple classification to complex, structured information extraction challenges in technical domains.