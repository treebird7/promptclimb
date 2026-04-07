import os
import csv
import datetime


class ResultsWriter:
    def __init__(self, output_dir: str, initial_prompt: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.results_path = os.path.join(output_dir, "results.tsv")
        self.history_path = os.path.join(output_dir, "history.jsonl")

        with open(os.path.join(output_dir, "prompt.initial.txt"), "w") as f:
            f.write(initial_prompt)

        self.write_header()

    def write_header(self):
        with open(self.results_path, "w", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(["iteration", "score", "best_score", "status", "timestamp"])

    def append_row(self, iteration: int, score: float, best_score: float, status: str):
        with open(self.results_path, "a", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(
                [
                    iteration,
                    f"{score:.4f}",
                    f"{best_score:.4f}",
                    status,
                    datetime.datetime.now().isoformat(),
                ]
            )

    def save_best_prompt(self, prompt: str):
        with open(os.path.join(self.output_dir, "prompt.best.txt"), "w") as f:
            f.write(prompt)
