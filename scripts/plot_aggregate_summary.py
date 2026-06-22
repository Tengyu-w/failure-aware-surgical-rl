from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


METRICS = [
    ("success_mean", "Success Rate"),
    ("budget_exhausted_mean", "Budget Exhaustion Rate"),
    ("cumulative_cost_mean", "Cumulative Cost"),
    ("final_distance_mean", "Final Distance"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aggregate", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=Path("runs") / "aggregate_plots")
    return parser.parse_args()


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def plot_metric(rows: list[dict], metric: str, label: str, out_dir: Path) -> None:
    variants = [row["variant"] for row in rows]
    means = np.array([float(row[f"{metric}_mean_over_seeds"]) for row in rows], dtype=np.float64)
    stds = np.array([float(row[f"{metric}_std_over_seeds"]) for row in rows], dtype=np.float64)

    fig, ax = plt.subplots(figsize=(6, 4))
    x = np.arange(len(variants))
    ax.bar(x, means, yerr=stds, color=["#4f79a8", "#6ca66f", "#d38b5d"][: len(variants)], capsize=4)
    ax.set_xticks(x)
    ax.set_xticklabels(variants, rotation=18, ha="right")
    ax.set_ylabel(label)
    ax.set_title(label)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_dir / f"{metric}.png", dpi=160)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    rows = read_rows(args.aggregate)
    for metric, label in METRICS:
        plot_metric(rows, metric, label, args.out_dir)
    print(f"plots_dir={args.out_dir}")


if __name__ == "__main__":
    main()
