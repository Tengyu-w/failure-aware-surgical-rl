from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from train_surrol_ppo_failure_aware import flatten_obs, make_env  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--surrol-root", type=Path, default=Path("/mnt/e/RL_projects/SurRoL_clean_SR-VPPV"))
    parser.add_argument("--task", default="NeedleReachRL-v0")
    parser.add_argument("--seed", type=int, default=45300)
    parser.add_argument("--episodes", type=int, default=3)
    parser.add_argument("--steps-per-episode", type=int, default=20)
    parser.add_argument("--observation-mode", default="render_pseudo_vision", choices=["render_pseudo_vision", "render_proprio_vision"])
    parser.add_argument("--proprio-dim", type=int, default=7)
    parser.add_argument("--image-grid-size", type=int, default=4)
    parser.add_argument("--image-feature-mode", default="stats_gray", choices=["stats_gray", "stats_rgb"])
    parser.add_argument("--vision-corruption", default="mixed", choices=["gaussian_noise", "brightness_shift", "occlusion", "blackout", "mixed"])
    parser.add_argument("--vision-corruption-severity", type=float, default=0.5)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def wrapper_args(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        surrol_root=args.surrol_root,
        task=args.task,
        seed=args.seed,
        max_episode_steps=max(50, args.steps_per_episode),
        failure_mode="none",
        failure_prob=0.0,
        observation_mode=args.observation_mode,
        pseudo_vision_noise=0.0,
        vision_corruption="none",
        vision_corruption_prob=0.0,
        vision_corruption_severity=args.vision_corruption_severity,
        vision_stride=1,
        proprio_dim=args.proprio_dim,
        image_grid_size=args.image_grid_size,
        image_feature_mode=args.image_feature_mode,
        danger_zone="none",
        danger_radius=0.052,
        danger_penalty=2.0,
        success_bonus=5.0,
        progress_reward_scale=0.0,
        progress_clip=0.03,
    )


def main() -> None:
    args = parse_args()
    from stable_baselines3 import PPO

    env_args = wrapper_args(args)
    env = make_env(env_args)
    model = PPO.load(
        args.model,
        env=env,
        custom_objects={
            "observation_space": env.observation_space,
            "action_space": env.action_space,
        },
    )

    rows = []
    for episode in range(args.episodes):
        env_args.seed = args.seed + episode
        env.seed(env_args.seed)
        env.reset()
        for step in range(args.steps_per_episode):
            raw_obs = env.last_raw_obs
            image = env._render_for_obs()
            clean_obs = flatten_obs(
                raw_obs,
                args.observation_mode,
                np.random.default_rng(args.seed + episode * 1000 + step),
                0.0,
                image,
                proprio_dim=args.proprio_dim,
                image_grid_size=args.image_grid_size,
                image_feature_mode=args.image_feature_mode,
            )
            diagnostics = {}
            corrupt_obs = flatten_obs(
                raw_obs,
                args.observation_mode,
                np.random.default_rng(args.seed + episode * 1000 + step),
                0.0,
                image,
                args.vision_corruption,
                1.0,
                args.vision_corruption_severity,
                diagnostics,
                args.proprio_dim,
                args.image_grid_size,
                args.image_feature_mode,
            )
            clean_action, _ = model.predict(clean_obs, deterministic=True)
            corrupt_action, _ = model.predict(corrupt_obs, deterministic=True)
            rows.append(
                {
                    "episode": episode,
                    "step": step,
                    "seed": env_args.seed,
                    "corruption_requested": args.vision_corruption,
                    "corruption_applied": diagnostics.get("visual_corruption_applied", "none"),
                    "corruption_magnitude": diagnostics.get("visual_corruption_magnitude", 0.0),
                    "observation_l2_delta": float(np.linalg.norm(corrupt_obs - clean_obs)),
                    "action_l2_delta": float(np.linalg.norm(corrupt_action - clean_action)),
                    "clean_action_norm": float(np.linalg.norm(clean_action)),
                    "corrupt_action_norm": float(np.linalg.norm(corrupt_action)),
                }
            )
            _, _, done, _ = env.step(clean_action)
            if done:
                break
    env.close()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"sensitivity_csv={args.out}")
    print(f"mean_action_l2_delta={np.mean([row['action_l2_delta'] for row in rows]):.8f}")


if __name__ == "__main__":
    main()
