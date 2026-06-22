from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from constraint_surgical_rl import make_tool_manipulation_env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", default="conditioned_tangent_shielded")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--seed", type=int, default=9000)
    parser.add_argument("--out", type=Path, default=Path("runs") / "manipulation_heuristic_eval.csv")
    return parser.parse_args()


def heuristic_action(env) -> np.ndarray:
    unwrapped = env.unwrapped
    if unwrapped.object_delivered:
        target = unwrapped.retract_xy
    else:
        push_dir = unwrapped.goal_xy - unwrapped.object_xy
        push_norm = np.linalg.norm(push_dir)
        if push_norm < 1e-8:
            push_dir = np.ones_like(push_dir, dtype=np.float32)
            push_norm = np.linalg.norm(push_dir)
        push_dir = push_dir / push_norm
        pre_push = unwrapped.object_xy - push_dir * (unwrapped.config.contact_radius * 0.6)
        if np.linalg.norm(unwrapped.tool_xy - pre_push) > unwrapped.config.contact_radius * 0.5:
            target = pre_push
        else:
            target = unwrapped.tool_xy + push_dir

    action = target - unwrapped.tool_xy
    norm = np.linalg.norm(action)
    if norm < 1e-8:
        return np.zeros_like(unwrapped.tool_xy, dtype=np.float32)

    action = action / norm
    to_forbidden = unwrapped.tool_xy - unwrapped.forbidden_xy
    forbidden_dist = np.linalg.norm(to_forbidden)
    caution_radius = unwrapped.config.forbidden_radius + 0.18
    if forbidden_dist < caution_radius:
        avoid = to_forbidden / max(forbidden_dist, 1e-8)
        action = action + 1.2 * avoid
        action = action / max(np.linalg.norm(action), 1e-8)
    return action.astype(np.float32)


def run_episode(variant: str, seed: int) -> dict:
    env = make_tool_manipulation_env(variant=variant)
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
        "object_delivered": float(info.get("object_delivered", False)),
        "budget_exhausted": float(info.get("budget_exhausted", False)),
        "cumulative_cost": float(info.get("cumulative_cost", 0.0)),
        "final_distance": float(info.get("distance_to_goal", np.nan)),
        "tool_object_distance": float(info.get("tool_object_distance", np.nan)),
        "object_goal_distance": float(info.get("object_goal_distance", np.nan)),
        "final_force_proxy": float(info.get("force_proxy", np.nan)),
        "shield_interventions": float(info.get("shield_interventions", 0.0)),
        "mean_action_deviation": float(info.get("mean_action_deviation", 0.0)),
        "task_phase": float(info.get("task_phase", np.nan)),
    }


def main() -> None:
    args = parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows = [run_episode(args.variant, args.seed + idx) for idx in range(args.episodes)]

    with args.out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["episode", *rows[0].keys()])
        writer.writeheader()
        for idx, row in enumerate(rows):
            writer.writerow({"episode": idx, **row})

    print(f"variant={args.variant}")
    print(f"episodes={args.episodes}")
    print(f"eval_csv={args.out}")
    for key in rows[0]:
        values = np.array([row[key] for row in rows], dtype=np.float64)
        print(f"{key}_mean={values.mean():.4f}")


if __name__ == "__main__":
    main()
