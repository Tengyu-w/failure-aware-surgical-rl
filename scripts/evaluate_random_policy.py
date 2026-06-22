from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from constraint_surgical_rl import make_tool_navigation_env
from constraint_surgical_rl.envs.presets import CONFIG_PRESET_NAMES


VARIANTS = (
    "conditioned",
    "conditioned_shielded",
    "conditioned_tangent_shielded",
    "no_phase_budget",
    "no_phase_budget_shielded",
    "no_phase_budget_tangent_shielded",
    "no_budget",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=VARIANTS, default="conditioned_tangent_shielded")
    parser.add_argument("--config-preset", choices=CONFIG_PRESET_NAMES, default="prototype")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--seed", type=int, default=5000)
    parser.add_argument("--out", type=Path, default=Path("runs") / "random_eval.csv")
    return parser.parse_args()


def run_episode(variant: str, config_preset: str, seed: int) -> dict:
    env = make_tool_navigation_env(variant=variant, config_preset=config_preset)
    obs, _ = env.reset(seed=seed)
    total_reward = 0.0
    terminated = False
    truncated = False
    info = {}

    while not (terminated or truncated):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward

    return {
        "return": total_reward,
        "success": float(info.get("success", False)),
        "budget_exhausted": float(info.get("budget_exhausted", False)),
        "cumulative_cost": float(info.get("cumulative_cost", 0.0)),
        "remaining_budget": float(info.get("remaining_budget", 0.0)),
        "final_distance": float(info.get("distance_to_goal", np.nan)),
        "final_force_proxy": float(info.get("force_proxy", np.nan)),
        "shield_interventions": float(info.get("shield_interventions", 0.0)),
        "mean_action_deviation": float(info.get("mean_action_deviation", 0.0)),
        "cumulative_action_deviation": float(info.get("cumulative_action_deviation", 0.0)),
    }


def main() -> None:
    args = parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows = [run_episode(args.variant, args.config_preset, args.seed + idx) for idx in range(args.episodes)]

    with args.out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["episode", *rows[0].keys()])
        writer.writeheader()
        for idx, row in enumerate(rows):
            writer.writerow({"episode": idx, **row})

    print(f"variant={args.variant}")
    print(f"config_preset={args.config_preset}")
    print(f"episodes={args.episodes}")
    print(f"eval_csv={args.out}")
    for key in rows[0]:
        values = np.array([row[key] for row in rows], dtype=np.float64)
        print(f"{key}_mean={values.mean():.4f}")


if __name__ == "__main__":
    main()
