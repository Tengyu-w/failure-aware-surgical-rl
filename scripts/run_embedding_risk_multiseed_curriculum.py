from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a multi-seed PPO comparison for embedding-risk curriculum fine-tuning."
    )
    parser.add_argument("--seeds", default="0,1,2")
    parser.add_argument("--timesteps", type=int, default=8_192)
    parser.add_argument("--episodes", type=int, default=50)
    parser.add_argument("--eval-seed", type=int, default=100)
    parser.add_argument("--penalty-scale", type=float, default=0.25)
    parser.add_argument("--risk-threshold", type=float, default=0.55)
    parser.add_argument("--curriculum-probability", type=float, default=0.35)
    parser.add_argument("--curriculum-candidates", type=int, default=8)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "outputs" / "embedding_risk_multiseed_curriculum")
    parser.add_argument("--dataset", type=Path, default=ROOT / "outputs" / "risk_dataset" / "risk_dataset.csv")
    parser.add_argument("--presets", default="prototype,strict")
    return parser.parse_args()


def run(cmd: list[str]) -> None:
    print("RUN " + " ".join(str(part) for part in cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def parse_seeds(raw: str) -> list[int]:
    return [int(item.strip()) for item in raw.split(",") if item.strip()]


def mean_metric(path: Path, key: str) -> float:
    df = pd.read_csv(path)
    return float(np.nanmean(df[key].to_numpy(dtype=float)))


def train_model(
    label: str,
    variant: str,
    seed: int,
    args: argparse.Namespace,
    init_model: Path | None = None,
) -> Path:
    out_dir = args.out_dir / f"seed_{seed}" / label
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
        str(seed),
        "--out-dir",
        str(out_dir),
        "--verbose",
        "0",
    ]
    if init_model is not None:
        cmd += ["--init-model", str(init_model)]
    if variant in {"conditioned_embedding_risk_penalty", "conditioned_embedding_risk_curriculum"}:
        cmd += [
            "--embedding-risk-dataset",
            str(args.dataset),
            "--embedding-risk-penalty-scale",
            str(args.penalty_scale),
            "--embedding-risk-threshold",
            str(args.risk_threshold),
        ]
    if variant == "conditioned_embedding_risk_curriculum":
        cmd += [
            "--embedding-risk-curriculum-probability",
            str(args.curriculum_probability),
            "--embedding-risk-curriculum-candidates",
            str(args.curriculum_candidates),
        ]
    run(cmd)
    return out_dir / "model.zip"


def evaluate(label: str, model: Path, seed: int, preset: str, args: argparse.Namespace) -> Path:
    out_csv = args.out_dir / f"seed_{seed}" / f"{label}_{preset}_eval.csv"
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
        str(args.eval_seed + 1000 * seed),
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


def summarize_seed_rows(rows: list[dict], args: argparse.Namespace) -> Path:
    seed_summary = args.out_dir / "seed_summary.csv"
    with seed_summary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return seed_summary


def aggregate(seed_summary: Path, args: argparse.Namespace) -> Path:
    df = pd.read_csv(seed_summary)
    metrics = [
        "success_rate",
        "budget_exhaustion_rate",
        "mean_return",
        "mean_cumulative_cost",
        "mean_final_distance",
        "mean_embedding_risk",
        "max_embedding_risk",
        "mean_active_embedding_risk",
    ]
    aggregate_rows = []
    for (method, preset), group in df.groupby(["method", "preset"], sort=False):
        row = {
            "method": method,
            "preset": preset,
            "seeds": int(group["seed"].nunique()),
            "timesteps_per_stage": args.timesteps,
            "episodes_per_seed": args.episodes,
        }
        for metric in metrics:
            values = group[metric].to_numpy(dtype=float)
            row[f"{metric}_mean"] = float(np.nanmean(values))
            row[f"{metric}_std"] = float(np.nanstd(values, ddof=1)) if values.size > 1 else 0.0
        aggregate_rows.append(row)

    aggregate_summary = args.out_dir / "aggregate_summary.csv"
    with aggregate_summary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(aggregate_rows[0].keys()))
        writer.writeheader()
        writer.writerows(aggregate_rows)
    return aggregate_summary


def plot_aggregate(aggregate_summary: Path) -> Path:
    df = pd.read_csv(aggregate_summary)
    methods = ["baseline_ppo", "embedding_risk_reward_ppo", "embedding_curriculum_finetune_ppo"]
    labels = ["Baseline", "Risk reward", "Curriculum FT"]
    colors = ["#4C78A8", "#F58518", "#B279A2"]
    metrics = [
        ("success_rate", "Success rate", (0.0, max(0.08, float(df["success_rate_mean"].max()) + 0.04))),
        ("budget_exhaustion_rate", "Budget exhaustion", (0.0, 1.05)),
        ("mean_final_distance", "Final distance", (0.0, max(1.0, float(df["mean_final_distance_mean"].max()) + 0.25))),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.8), constrained_layout=True)
    for ax, (metric, title, ylim) in zip(axes, metrics):
        for preset_idx, preset in enumerate(["prototype", "strict"]):
            subset = df[df["preset"] == preset].set_index("method").loc[methods]
            x = np.arange(len(methods)) + (preset_idx - 0.5) * 0.22
            ax.bar(
                x,
                subset[f"{metric}_mean"].to_numpy(),
                yerr=subset[f"{metric}_std"].to_numpy(),
                width=0.38,
                label=preset if metric == "success_rate" else None,
                color=colors,
                alpha=0.95 if preset == "prototype" else 0.55,
                edgecolor="black",
                linewidth=0.4,
                capsize=3,
            )
        ax.set_title(title)
        ax.set_xticks(np.arange(len(methods)), labels, rotation=18, ha="right")
        ax.set_ylim(*ylim)
        ax.grid(axis="y", alpha=0.25)
    axes[0].legend(frameon=False, loc="upper right")
    fig.suptitle("Embedding-risk PPO multi-seed pilot", fontsize=12)
    out_dir = ROOT / "reports" / "figures" / "embedding_risk_training_pilot"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "multiseed_curriculum_metrics.png"
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    return out_path


def publish_tracked_summaries(seed_summary: Path, aggregate_summary: Path) -> tuple[Path, Path]:
    tracked_seed = ROOT / "outputs" / "embedding_risk_multiseed_curriculum_seed_summary.csv"
    tracked_aggregate = ROOT / "outputs" / "embedding_risk_multiseed_curriculum_aggregate_summary.csv"
    shutil.copyfile(seed_summary, tracked_seed)
    shutil.copyfile(aggregate_summary, tracked_aggregate)
    return tracked_seed, tracked_aggregate


def main() -> None:
    args = parse_args()
    if not args.out_dir.is_absolute():
        args.out_dir = ROOT / args.out_dir
    if not args.dataset.is_absolute():
        args.dataset = ROOT / args.dataset
    args.out_dir.mkdir(parents=True, exist_ok=True)

    seeds = parse_seeds(args.seeds)
    presets = [item.strip() for item in args.presets.split(",") if item.strip()]
    rows = []
    for seed in seeds:
        baseline_model = train_model("baseline_ppo", "conditioned", seed, args)
        models = {
            "baseline_ppo": baseline_model,
            "embedding_risk_reward_ppo": train_model(
                "embedding_risk_reward_ppo",
                "conditioned_embedding_risk_penalty",
                seed,
                args,
            ),
            "embedding_curriculum_finetune_ppo": train_model(
                "embedding_curriculum_finetune_ppo",
                "conditioned_embedding_risk_curriculum",
                seed,
                args,
                init_model=baseline_model,
            ),
        }
        for label, model in models.items():
            for preset in presets:
                eval_csv = evaluate(label, model, seed, preset, args)
                rows.append(
                    {
                        "seed": seed,
                        "method": label,
                        "preset": preset,
                        "timesteps_per_stage": args.timesteps,
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

    seed_summary = summarize_seed_rows(rows, args)
    aggregate_summary = aggregate(seed_summary, args)
    tracked_seed, tracked_aggregate = publish_tracked_summaries(seed_summary, aggregate_summary)
    figure_path = plot_aggregate(aggregate_summary)
    print(f"seed_summary={seed_summary}")
    print(f"aggregate_summary={aggregate_summary}")
    print(f"tracked_seed_summary={tracked_seed}")
    print(f"tracked_aggregate_summary={tracked_aggregate}")
    print(f"figure={figure_path}")
    print(pd.read_csv(aggregate_summary).to_string(index=False))


if __name__ == "__main__":
    main()
