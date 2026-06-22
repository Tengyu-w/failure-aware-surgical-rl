from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--steps", type=Path, required=True)
    parser.add_argument("--episodes", type=Path, required=True)
    parser.add_argument("--action-gap-threshold", type=float, default=0.25)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args()


def split_name(seed: int) -> str:
    residue = int(seed) % 4
    if residue in {0, 1}:
        return "train"
    if residue == 2:
        return "validation"
    return "test"


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    values = np.load(args.dataset)
    steps = pd.read_csv(args.steps)
    episodes = pd.read_csv(args.episodes)
    observations = np.asarray(values["observations"], dtype=np.float32)
    actions = np.asarray(values["actions"], dtype=np.float32)
    if len(observations) != len(actions) or len(observations) != len(steps):
        raise ValueError("Dataset arrays and step rows are not aligned")

    steps = steps.copy()
    steps["split"] = steps["seed"].map(split_name)
    steps["high_action_gap"] = steps["policy_oracle_action_l2"] >= args.action_gap_threshold
    split_rows = []
    for name, group in steps.groupby("split", sort=False):
        split_rows.append(
            {
                "split": name,
                "seeds": int(group["seed"].nunique()),
                "steps": int(len(group)),
                "high_action_gap_steps": int(group["high_action_gap"].sum()),
                "high_action_gap_rate": float(group["high_action_gap"].mean()),
                "mean_action_gap": float(group["policy_oracle_action_l2"].mean()),
                "max_action_gap": float(group["policy_oracle_action_l2"].max()),
                "mean_predicted_risk": float(group["predicted_risk"].mean()),
                "mean_memory_distance": float(group["memory_distance"].mean()),
            }
        )
    split_table = pd.DataFrame(split_rows).sort_values("split")
    split_table.to_csv(args.out_dir / "seed_split_summary.csv", index=False)
    steps.to_csv(args.out_dir / "adapter_online_scored_steps.csv", index=False)

    episode_rows = episodes.copy()
    episode_rows["split"] = episode_rows["seed"].map(split_name)
    episode_rows.to_csv(args.out_dir / "adapter_online_episodes_with_split.csv", index=False)
    summary = {
        "dataset": str(args.dataset),
        "steps": int(len(steps)),
        "episodes": int(len(episodes)),
        "observation_shape": list(observations.shape),
        "action_shape": list(actions.shape),
        "action_gap_threshold": args.action_gap_threshold,
        "high_action_gap_steps": int(steps["high_action_gap"].sum()),
        "high_action_gap_rate": float(steps["high_action_gap"].mean()),
        "mean_action_gap": float(steps["policy_oracle_action_l2"].mean()),
        "max_action_gap": float(steps["policy_oracle_action_l2"].max()),
        "splits": split_rows,
        "passes_shape_check": observations.ndim == 2 and observations.shape[1] == 208,
        "passes_split_positive_check": bool((split_table["high_action_gap_steps"] > 0).all()),
        "note": "Split is seed_mod_4: train={0,1}, validation={2}, test={3}.",
    }
    (args.out_dir / "adapter_online_dataset_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(f"summary={args.out_dir / 'adapter_online_dataset_summary.json'}")
    print(f"steps={summary['steps']}")
    print(f"high_action_gap_steps={summary['high_action_gap_steps']}")
    print(f"passes_shape_check={summary['passes_shape_check']}")
    print(f"passes_split_positive_check={summary['passes_split_positive_check']}")


if __name__ == "__main__":
    main()
