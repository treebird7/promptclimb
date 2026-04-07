import click
import importlib.util
import sys
from pathlib import Path
from .climber import HillClimber


def load_scorer_from_file(filepath: str):
    """Loads a scorer function from a Python file."""
    path = Path(filepath)
    spec = importlib.util.spec_from_file_location(path.stem, path.resolve())
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.score


@click.group()
def main():
    """promptclimb — automatically improve LLM prompts through hill-climbing."""
    pass


@main.command()
@click.option(
    "--prompt",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Path to the prompt file.",
)
@click.option(
    "--eval",
    "eval_script",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Path to the evaluation script (must export a score() function).",
)
@click.option(
    "--gold",
    required=True,
    type=click.Path(exists=True, file_okay=False),
    help="Path to the directory with gold test cases.",
)
@click.option("--iterations", default=50, help="Maximum number of iterations.")
@click.option("--model", default="openai:gpt-4o-mini", help="Model for execution.")
@click.option(
    "--proposer", help="Model for proposing mutations (defaults to executor model)."
)
@click.option("--output", default="results/", help="Directory to save results.")
@click.option(
    "--early-stop",
    default=20,
    help="Stop after N consecutive non-improvements (0 to disable).",
)
def run(prompt, eval_script, gold, iterations, model, proposer, output, early_stop):
    """Run the prompt hill-climbing optimization."""
    scorer_func = load_scorer_from_file(eval_script)

    climber = HillClimber(
        prompt_path=prompt,
        scorer=scorer_func,
        gold_dir=gold,
        model=model,
        proposer_model=proposer,
        output_dir=output,
        early_stop_after=early_stop if early_stop > 0 else float("inf"),
    )
    climber.run(max_iterations=iterations)


@main.command()
@click.option(
    "--prompt",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Path to the prompt file.",
)
@click.option(
    "--eval",
    "eval_script",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Path to the evaluation script.",
)
@click.option(
    "--gold",
    required=True,
    type=click.Path(exists=True, file_okay=False),
    help="Path to the directory with gold test cases.",
)
def eval(prompt, eval_script, gold):
    """Evaluate the current prompt without mutation."""
    scorer_func = load_scorer_from_file(eval_script)

    climber = HillClimber(prompt_path=prompt, scorer=scorer_func, gold_dir=gold)
    climber.eval()


if __name__ == "__main__":
    main()
