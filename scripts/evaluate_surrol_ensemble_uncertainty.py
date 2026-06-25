from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from train_surrol_ppo_failure_aware import goal_distance, make_env  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", type=Path, nargs="+", required=True)
    parser.add_argument("--primary-index", type=int, default=0)
    parser.add_argument("--surrol-root", type=Path, default=Path("external/SurRoL_clean_SR-VPPV"))
    parser.add_argument("--task", default="NeedleReachRL-v0")
    parser.add_argument("--seed", type=int, default=50500)
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--max-episode-steps", type=int, default=75)
    parser.add_argument("--vision-stride", type=int, default=4)
    parser.add_argument("--proprio-dim", type=int, default=7)
    parser.add_argument("--image-grid-size", type=int, default=8)
    parser.add_argument("--image-feature-mode", default="stats_rgb", choices=["stats_gray", "stats_rgb"])
    parser.add_argument("--near-target-threshold", type=float, default=0.12)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args()


def env_args(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        surrol_root=args.surrol_root,
        task=args.task,
        seed=args.seed,
        max_episode_steps=args.max_episode_steps,
        failure_mode="none",
        failure_prob=0.0,
        observation_mode="render_proprio_vision",
        pseudo_vision_noise=0.003,
        vision_corruption="none",
        vision_corruption_prob=0.0,
        vision_corruption_severity=0.25,
        vision_stride=args.vision_stride,
        proprio_dim=args.proprio_dim,
        image_grid_size=args.image_grid_size,
        image_feature_mode=args.image_feature_mode,
        danger_zone="none",
        danger_radius=0.052,
        danger_penalty=2.0,
        success_bonus=5.0,
        progress_reward_scale=10.0,
        progress_clip=0.03,
    )


def binary_auc(scores: list[float], positives: list[bool]) -> float:
    positive_scores = [score for score, positive in zip(scores, positives) if positive]
    negative_scores = [score for score, positive in zip(scores, positives) if not positive]
    if not positive_scores or not negative_scores:
        return float("nan")
    wins = 0.0
    for positive in positive_scores:
        for negative in negative_scores:
            wins += float(positive > negative) + 0.5 * float(positive == negative)
    return wins / (len(positive_scores) * len(negative_scores))


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    if not 0 <= args.primary_index < len(args.models):
        raise ValueError("primary-index must identify one of the supplied models")
    from stable_baselines3 import PPO

    config = env_args(args)
    env = make_env(config)
    models = [
        PPO.load(
            path,
            env=env,
            custom_objects={"observation_space": env.observation_space, "action_space": env.action_space},
        )
        for path in args.models
    ]
    step_rows = []
    episode_rows = []
    for episode in range(args.episodes):
        eval_seed = args.seed + episode
        env.seed(eval_seed)
        obs = env.reset()
        initial_distance = goal_distance(env.last_raw_obs)
        min_distance = initial_distance
        disagreements = []
        near_disagreements = []
        success = 0.0
        final_distance = initial_distance
        for step in range(args.max_episode_steps):
            actions = np.stack([model.predict(obs, deterministic=True)[0] for model in models]).astype(np.float32)
            mean_action = actions.mean(axis=0)
            disagreement = float(np.sqrt(np.mean((actions - mean_action) ** 2)))
            max_pairwise = max(
                float(np.linalg.norm(actions[i] - actions[j]))
                for i in range(len(actions))
                for j in range(i + 1, len(actions))
            )
            current_distance = goal_distance(env.last_raw_obs)
            disagreements.append(disagreement)
            if current_distance < args.near_target_threshold:
                near_disagreements.append(disagreement)
            obs, _, done, info = env.step(actions[args.primary_index])
            success = float(info.get("is_success", 0.0))
            final_distance = goal_distance(env.last_raw_obs)
            min_distance = min(min_distance, final_distance)
            step_rows.append(
                {
                    "episode": episode,
                    "seed": eval_seed,
                    "step": step,
                    "goal_distance_before": current_distance,
                    "goal_distance_after": final_distance,
                    "action_disagreement_rms": disagreement,
                    "max_pairwise_action_l2": max_pairwise,
                    "primary_action_norm": float(np.linalg.norm(actions[args.primary_index])),
                    "success": success,
                }
            )
            if done:
                break
        episode_rows.append(
            {
                "episode": episode,
                "seed": eval_seed,
                "success": success,
                "failure": float(success < 1.0),
                "steps": step + 1,
                "initial_distance": initial_distance,
                "min_distance": min_distance,
                "final_distance": final_distance,
                "mean_action_disagreement": float(np.mean(disagreements)),
                "max_action_disagreement": float(np.max(disagreements)),
                "mean_near_target_disagreement": float(np.mean(near_disagreements)) if near_disagreements else float("nan"),
                "near_target_steps": len(near_disagreements),
            }
        )
    env.close()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.out_dir / "ensemble_uncertainty_steps.csv", step_rows)
    write_csv(args.out_dir / "ensemble_uncertainty_episodes.csv", episode_rows)
    failures = [bool(row["failure"]) for row in episode_rows]
    mean_auc = binary_auc([float(row["mean_action_disagreement"]) for row in episode_rows], failures)
    max_auc = binary_auc([float(row["max_action_disagreement"]) for row in episode_rows], failures)
    summary = {
        "models": [str(path) for path in args.models],
        "primary_index": args.primary_index,
        "episodes": len(episode_rows),
        "success_rate": float(np.mean([row["success"] for row in episode_rows])),
        "failure_detection_auc_mean_disagreement": mean_auc,
        "failure_detection_auc_max_disagreement": max_auc,
        "note": "Exploratory AUC on the same 10 episodes; no routing threshold was fitted.",
    }
    (args.out_dir / "ensemble_uncertainty_summary.json").write_text(
        __import__("json").dumps(summary, indent=2), encoding="utf-8"
    )
    print(f"episodes_csv={args.out_dir / 'ensemble_uncertainty_episodes.csv'}")
    print(f"mean_disagreement_auc={mean_auc:.4f}")
    print(f"max_disagreement_auc={max_auc:.4f}")


if __name__ == "__main__":
    main()
