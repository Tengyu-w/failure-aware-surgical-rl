from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


METRICS = [
    ("success_mean", "Success Rate"),
    ("budget_exhausted_mean", "Budget Exhaustion Rate"),
    ("cumulative_cost_mean", "Cumulative Cost"),
    ("final_distance_mean", "Final Distance"),
    ("shield_interventions_mean", "Shield Interventions"),
    ("mean_action_deviation_mean", "Mean Action Deviation"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=Path("runs") / "plots")
    return parser.parse_args()


def load_summary(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def variant_from_row(row: dict) -> str:
    variant = row["variant"]
    if "_seed" in variant:
        return variant.split("_seed")[0]
    return variant


def aggregate(rows: list[dict], metric: str) -> tuple[list[str], np.ndarray, np.ndarray]:
    grouped = defaultdict(list)
    for row in rows:
        if row.get(metric, "") == "":
            continue
        grouped[variant_from_row(row)].append(float(row[metric]))

    variants = sorted(grouped)
    means = np.array([np.mean(grouped[variant]) for variant in variants], dtype=np.float64)
    stds = np.array([np.std(grouped[variant]) for variant in variants], dtype=np.float64)
    return variants, means, stds


def plot_metric(rows: list[dict], metric: str, label: str, out_dir: Path) -> None:
    variants, means, stds = aggregate(rows, metric)
    if not variants:
        return

    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(len(variants))
    ax.bar(x, means, yerr=stds, color=["#4f79a8", "#d38b5d", "#6ca66f"][: len(variants)], capsize=4)
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
    rows = load_summary(args.summary)

    for metric, label in METRICS:
        plot_metric(rows, metric, label, args.out_dir)

    print(f"plots_dir={args.out_dir}")


if __name__ == "__main__":
    main()
