from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from stable_baselines3 import PPO

from constraint_surgical_rl import make_tool_manipulation_env, make_tool_navigation_env
from constraint_surgical_rl.envs.presets import CONFIG_PRESET_NAMES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--task", choices=("navigation", "manipulation"), default="navigation")
    parser.add_argument(
        "--variant",
        choices=(
            "conditioned",
            "conditioned_embedding_risk_penalty",
            "conditioned_shielded",
            "conditioned_tangent_shielded",
            "conditioned_risk_gated_tangent_shielded",
            "no_phase_budget",
            "no_phase_budget_shielded",
            "no_phase_budget_tangent_shielded",
            "no_phase_budget_risk_gated_tangent_shielded",
            "no_budget",
        ),
        default="conditioned",
    )
    parser.add_argument("--config-preset", choices=CONFIG_PRESET_NAMES, default="prototype")
    parser.add_argument("--episodes", type=int, default=50)
    parser.add_argument("--seed", type=int, default=100)
    parser.add_argument("--out", type=Path, default=Path("runs") / "eval.csv")
    parser.add_argument("--deterministic", action="store_true")
    parser.add_argument("--embedding-risk-dataset", type=Path, default=None)
    parser.add_argument("--embedding-risk-penalty-scale", type=float, default=0.75)
    parser.add_argument("--embedding-risk-threshold", type=float, default=0.55)
    return parser.parse_args()


def make_env(
    task: str,
    variant: str,
    config_preset: str,
    embedding_risk_dataset: Path | None = None,
    embedding_risk_penalty_scale: float = 0.75,
    embedding_risk_threshold: float = 0.55,
):
    if task == "navigation":
        return make_tool_navigation_env(
            variant=variant,
            config_preset=config_preset,
            embedding_risk_dataset=embedding_risk_dataset,
            embedding_risk_penalty_scale=embedding_risk_penalty_scale,
            embedding_risk_threshold=embedding_risk_threshold,
        )
    return make_tool_manipulation_env(variant=variant)


def run_episode(
    model: PPO,
    task: str,
    variant: str,
    config_preset: str,
    seed: int,
    deterministic: bool,
    embedding_risk_dataset: Path | None = None,
    embedding_risk_penalty_scale: float = 0.75,
    embedding_risk_threshold: float = 0.55,
) -> dict:
    env = make_env(
        task=task,
        variant=variant,
        config_preset=config_preset,
        embedding_risk_dataset=embedding_risk_dataset,
        embedding_risk_penalty_scale=embedding_risk_penalty_scale,
        embedding_risk_threshold=embedding_risk_threshold,
    )
    obs, _ = env.reset(seed=seed)

    total_reward = 0.0
    terminated = False
    truncated = False
    info = {}

    while not (terminated or truncated):
        action, _ = model.predict(obs, deterministic=deterministic)
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
        "object_delivered": float(info.get("object_delivered", False)),
        "tool_object_distance": float(info.get("tool_object_distance", np.nan)),
        "object_goal_distance": float(info.get("object_goal_distance", np.nan)),
        "task_phase": float(info.get("task_phase", np.nan)),
        "mean_embedding_risk": float(info.get("mean_embedding_risk", np.nan)),
        "max_embedding_risk": float(info.get("max_embedding_risk", np.nan)),
        "embedding_risk_score": float(info.get("embedding_risk_score", np.nan)),
        "embedding_risk_active_score": float(info.get("embedding_risk_active_score", np.nan)),
    }


def summarize(rows: list[dict]) -> dict:
    keys = rows[0].keys()
    return {key: float(np.mean([row[key] for row in rows])) for key in keys}


def main() -> None:
    args = parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    model = PPO.load(args.model)
    rows = [
        run_episode(
            model,
            task=args.task,
            variant=args.variant,
            config_preset=args.config_preset,
            seed=args.seed + i,
            deterministic=args.deterministic,
            embedding_risk_dataset=args.embedding_risk_dataset,
            embedding_risk_penalty_scale=args.embedding_risk_penalty_scale,
            embedding_risk_threshold=args.embedding_risk_threshold,
        )
        for i in range(args.episodes)
    ]
    summary = summarize(rows)

    with args.out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["episode", *rows[0].keys()])
        writer.writeheader()
        for idx, row in enumerate(rows):
            writer.writerow({"episode": idx, **row})

    print(f"episodes={args.episodes}")
    print(f"variant={args.variant}")
    print(f"task={args.task}")
    print(f"config_preset={args.config_preset}")
    print(f"model={args.model}")
    print(f"eval_csv={args.out}")
    for key, value in summary.items():
        print(f"{key}_mean={value:.4f}")


if __name__ == "__main__":
    main()
