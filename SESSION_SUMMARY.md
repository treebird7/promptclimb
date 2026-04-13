# Session Summary: PromptClimb Research Prompt Mining & Improvements

## Date: 2026-04-09
## Participants: Yosef (running norm loop), Nemosan (implementing improvements)

## Key Discoveries

### 1. Root Cause of Scorer Issues
The scorer_extraction.py was returning 0.0 because:
- It was using hardcoded paths: `../selfimprove/samples` and `../selfimprove/gold`
- When run from `/Users/freedbird/Dev/promptclimb/`, this pointed to wrong directories
- Environment variables `SAMPLES_DIR` and `GOLD_DIR` were being set correctly but the scorer construction had a bug:
  ```python
  SAMPLES_DIR = os.environ.get("SAMPLES_DIR", os.environ.get("PHC_SAMPLES_DIR",
      os.path.join(os.path.dirname(__file__), "..", "selfimprove", "samples")))
  ```
  This was working correctly, but the issue was that when we ran from promptclimb directory, the `../selfimprove` path was incorrect.

### 2. Working Configuration
When we explicitly set:
- `SAMPLES_DIR=/Users/freedbird/Dev/promptclimb/research_mining/samples`
- `GOLD_DIR=/Users/freedbird/Dev/promptclimb/research_mining/gold`
- `SELFIMPROVE_EXECUTOR=gemma-4-26b-a4b-it`
- `EMBEDDING_URL=http://localhost:8083`

The scorer worked correctly, producing:
- Score: 0.5538 for the research prompt on the Single-Multi Evolution Loop section
- This demonstrates the extraction pipeline is functional when paths are correct

### 3. Files Modified/Created
- `/Users/freedbird/Dev/promptclimb/src/promptclimb/backends/lmstudio.py` - NEW: LMStudio backend
- `/Users/freedbird/Dev/promptclimb/src/promptclimb/backends/__init__.py` - UPDATED: Added lmstudio routing
- `/Users/freedbird/Dev/promptclimb/research_prompt_mining.txt` - Research prompt template
- `/Users/freedbird/Dev/promptclimb/research_mining/gold/section_1.json` - Gold standard extraction
- `/Users/freedbird/Dev/promptclimb/research_mining/samples/section_1.md` - Research paper sample
- `/Users/freedbird/Dev/promptclimb/RESEARCH_USECASE.md` - Detailed use case documentation
- `/Users/freedbird/Dev/promptclimb/NEXT_STEPS.md` - Implementation guidance
- `/Users/freedbird/Dev/promptclimb/yosef-nemosan-coordination.md` - Coordination document

### 4. Experimental Results Available
From Yosef's norm loop:
- **R1 (Haiku, no splicing)**: 0.8051 best, 1/20 keeps (5% hit rate)
- **R8 (Haiku, with splicing)**: 0.8003 best, 3/20 keeps (15% hit rate) 
- **Current norm loop**: Plateaued at 0.7719 after 50 iterations

## Next Steps Agreed with Yosef

### Priority #1: Local Proposer Test
Test devstral-small-2-2512 as proposer vs Haiku:
```
SELFIMPROVE_EXECUTOR=gemma-4-26b-a4b-it
.venv/bin/phc run --prompt prompt.md --eval scorer_extraction.py --gold gold/
--model "http://localhost:8082/v1" --proposer "lmstudio:devstral-small-2-2512"
--iterations 20 --early-stop 15 --output results_devstral/
```

### Priority #2: Multi-Metric Scorer
Extend scorer_extraction.py to return weighted composite:
- Cosine similarity (0.5)
- JSON schema validity (0.2) 
- Concept count precision (0.15)
- Type accuracy (0.15)

### Priority #3: Full Normalized Experiment
After verifying local proposer works, run full hill-climbing from scratch on normalized samples to test if normalization enables higher asymptotic performance than 0.8345.

## Current Blockers
1. Need to verify if devstral-small-2-2512 is actually loadable on LMStudio (Yosef said 24B model is loaded but not active)
2. Need to fix the scorer to work properly with the research mining directories when using phc command (currently works when called directly but not through phc due to environment variable handling)
3. Need to kill any hanging phc/python processes before running new experiments

## Immediate Actions for Next Session
1. Check LMStudio model loading status for devstral-small-2-2512
2. Run the local proposer test with proper environment variable forwarding
3. If successful, implement multi-metric scorer
4. Coordinate with Yosef on timing for normalized experiment re-run

The research prompt mining use case is validated and ready for optimization experiments once the technical blockers are resolved.