from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from constraint_surgical_rl import make_tool_navigation_env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", default="conditioned")
    parser.add_argument("--config-preset", default="prototype")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--seed", type=int, default=200)
    parser.add_argument("--out", type=Path, default=Path("runs") / "heuristic_eval.csv")
    return parser.parse_args()


def heuristic_action(env) -> np.ndarray:
    unwrapped = env.unwrapped
    to_target = unwrapped.target_xy - unwrapped.tool_xy
    norm = np.linalg.norm(to_target)
    if norm < 1e-8:
        return np.zeros_like(unwrapped.tool_xy, dtype=np.float32)

    action = to_target / norm
    to_forbidden = unwrapped.tool_xy - unwrapped.forbidden_xy
    forbidden_dist = np.linalg.norm(to_forbidden)
    caution_radius = unwrapped.config.forbidden_radius + 0.18
    if forbidden_dist < caution_radius:
        avoid = to_forbidden / max(forbidden_dist, 1e-8)
        action = action + 1.2 * avoid
        action = action / max(np.linalg.norm(action), 1e-8)
    return action.astype(np.float32)


def run_episode(variant: str, config_preset: str, seed: int) -> dict:
    env = make_tool_navigation_env(variant=variant, config_preset=config_preset)
    obs, _ = env.reset(seed=seed)
    total_reward = 0.0
    terminated = False
    truncated = False
    info = {}
    while not (terminated or truncated):
        obs, reward, terminated, truncated, info = env.step(heuristic_action(env))
        total_reward += reward
    return {
        "return": total_reward,
        "success": float(info.get("success", False)),
        "budget_exhausted": float(info.get("budget_exhausted", False)),
        "cumulative_cost": float(info.get("cumulative_cost", 0.0)),
        "final_distance": float(info.get("distance_to_goal", np.nan)),
        "final_force_proxy": float(info.get("force_proxy", np.nan)),
        "shield_interventions": float(info.get("shield_interventions", 0.0)),
        "mean_action_deviation": float(info.get("mean_action_deviation", 0.0)),
        "cumulative_action_deviation": float(info.get("cumulative_action_deviation", 0.0)),
    }


def main() -> None:
    args = parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows = [run_episode(args.variant, args.config_preset, args.seed + i) for i in range(args.episodes)]

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
