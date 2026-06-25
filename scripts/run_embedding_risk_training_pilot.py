from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a PPO pilot with embedding-risk reward shaping.")
    parser.add_argument("--timesteps", type=int, default=8_192)
    parser.add_argument("--episodes", type=int, default=40)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--eval-seed", type=int, default=100)
    parser.add_argument("--penalty-scale", type=float, default=0.75)
    parser.add_argument("--risk-threshold", type=float, default=0.55)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "outputs" / "embedding_risk_training_pilot")
    parser.add_argument("--dataset", type=Path, default=ROOT / "outputs" / "risk_dataset" / "risk_dataset.csv")
    parser.add_argument("--presets", default="prototype,strict")
    return parser.parse_args()


def run(cmd: list[str]) -> None:
    print("RUN " + " ".join(str(part) for part in cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def mean_metric(path: Path, key: str) -> float:
    df = pd.read_csv(path)
    return float(np.nanmean(df[key].to_numpy(dtype=float)))


def train_model(label: str, variant: str, args: argparse.Namespace) -> Path:
    out_dir = args.out_dir / label
    cmd = [
        sys.executable,
        "scripts/train_ppo.py",
        "--task",
        "navigation",
        "--variant",
        variant,
        "--config-preset",
        "prototype",
        "--total-timesteps",
        str(args.timesteps),
        "--seed",
        str(args.seed),
        "--out-dir",
        str(out_dir),
        "--verbose",
        "0",
    ]
    if variant == "conditioned_embedding_risk_penalty":
        cmd += [
            "--embedding-risk-dataset",
            str(args.dataset),
            "--embedding-risk-penalty-scale",
            str(args.penalty_scale),
            "--embedding-risk-threshold",
            str(args.risk_threshold),
        ]
    run(cmd)
    return out_dir / "model.zip"


def evaluate(label: str, model: Path, preset: str, args: argparse.Namespace) -> Path:
    out_csv = args.out_dir / f"{label}_{preset}_eval.csv"
    cmd = [
        sys.executable,
        "scripts/evaluate_policy.py",
        "--task",
        "navigation",
        "--variant",
        "conditioned_embedding_risk_penalty",
        "--config-preset",
        preset,
        "--model",
        str(model),
        "--episodes",
        str(args.episodes),
        "--seed",
        str(args.eval_seed),
        "--out",
        str(out_csv),
        "--deterministic",
        "--embedding-risk-dataset",
        str(args.dataset),
        "--embedding-risk-penalty-scale",
        str(args.penalty_scale),
        "--embedding-risk-threshold",
        str(args.risk_threshold),
    ]
    run(cmd)
    return out_csv


def main() -> None:
    args = parse_args()
    if not args.out_dir.is_absolute():
        args.out_dir = ROOT / args.out_dir
    if not args.dataset.is_absolute():
        args.dataset = ROOT / args.dataset
    args.out_dir.mkdir(parents=True, exist_ok=True)

    models = {
        "baseline_ppo": train_model("baseline_ppo", "conditioned", args),
        "embedding_risk_ppo": train_model("embedding_risk_ppo", "conditioned_embedding_risk_penalty", args),
    }

    presets = [item.strip() for item in args.presets.split(",") if item.strip()]
    rows = []
    for label, model in models.items():
        for preset in presets:
            eval_csv = evaluate(label, model, preset, args)
            rows.append(
                {
                    "method": label,
                    "preset": preset,
                    "timesteps": args.timesteps,
                    "episodes": args.episodes,
                    "success_rate": mean_metric(eval_csv, "success"),
                    "budget_exhaustion_rate": mean_metric(eval_csv, "budget_exhausted"),
                    "mean_return": mean_metric(eval_csv, "return"),
                    "mean_cumulative_cost": mean_metric(eval_csv, "cumulative_cost"),
                    "mean_final_distance": mean_metric(eval_csv, "final_distance"),
                    "mean_embedding_risk": mean_metric(eval_csv, "mean_embedding_risk"),
                    "max_embedding_risk": mean_metric(eval_csv, "max_embedding_risk"),
                    "mean_active_embedding_risk": mean_metric(eval_csv, "embedding_risk_active_score"),
                    "eval_csv": str(eval_csv.relative_to(ROOT)),
                }
            )

    summary = args.out_dir / "summary.csv"
    with summary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"summary={summary}")
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
