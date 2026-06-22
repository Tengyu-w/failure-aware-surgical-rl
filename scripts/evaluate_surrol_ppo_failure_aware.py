from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from train_surrol_ppo_failure_aware import make_env  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--surrol-root", type=Path, default=Path("/mnt/e/RL_projects/SurRoL_clean_SR-VPPV"))
    parser.add_argument("--task", default="NeedlePickRL-v0")
    parser.add_argument("--seed", type=int, default=44000)
    parser.add_argument("--episodes", type=int, default=3)
    parser.add_argument("--max-episode-steps", type=int, default=100)
    parser.add_argument("--failure-mode", default="none", choices=["none", "action_noise", "action_dropout", "near_target_drift"])
    parser.add_argument("--failure-prob", type=float, default=0.25)
    parser.add_argument("--observation-mode", default="pseudo_vision", choices=["state", "pseudo_vision", "render_pseudo_vision", "render_proprio_vision"])
    parser.add_argument("--pseudo-vision-noise", type=float, default=0.003)
    parser.add_argument("--vision-corruption", default="none", choices=["none", "gaussian_noise", "brightness_shift", "occlusion", "blackout", "mixed"])
    parser.add_argument("--vision-corruption-prob", type=float, default=0.0)
    parser.add_argument("--vision-corruption-severity", type=float, default=0.25)
    parser.add_argument("--vision-stride", type=int, default=1)
    parser.add_argument("--proprio-dim", type=int, default=7)
    parser.add_argument("--image-grid-size", type=int, default=4)
    parser.add_argument("--image-feature-mode", default="stats_gray", choices=["stats_gray", "stats_rgb"])
    parser.add_argument("--danger-zone", default="none")
    parser.add_argument("--danger-radius", type=float, default=0.052)
    parser.add_argument("--danger-penalty", type=float, default=2.0)
    parser.add_argument("--success-bonus", type=float, default=5.0)
    parser.add_argument("--progress-reward-scale", type=float, default=0.0)
    parser.add_argument("--progress-clip", type=float, default=0.03)
    parser.add_argument("--distance-reward-scale", type=float, default=0.0)
    parser.add_argument("--near-target-action-penalty", type=float, default=0.0)
    parser.add_argument("--near-target-threshold", type=float, default=0.12)
    parser.add_argument("--out", type=Path, default=ROOT / "runs" / "surrol_ppo_eval.csv")
    return parser.parse_args()


def goal_distance(raw_obs) -> float:
    if not isinstance(raw_obs, dict):
        return float("nan")
    achieved = np.asarray(raw_obs["achieved_goal"], dtype=np.float32).ravel()
    desired = np.asarray(raw_obs["desired_goal"], dtype=np.float32).ravel()
    n = min(achieved.size, desired.size)
    if n == 0:
        return float("nan")
    return float(np.linalg.norm(achieved[:n] - desired[:n]))


def risk_level(success: float, unsafe_events: int, final_distance: float) -> str:
    if unsafe_events > 0:
        return "abort_candidate"
    if success >= 1.0:
        return "auto_execute"
    if np.isfinite(final_distance) and final_distance < 0.12:
        return "auto_recovery"
    return "human_review"


def run_evaluation(args: argparse.Namespace) -> None:
    from stable_baselines3 import PPO

    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    base_seed = args.seed
    env = make_env(args)
    model = PPO.load(
        args.model,
        env=env,
        custom_objects={
            "observation_space": env.observation_space,
            "action_space": env.action_space,
        },
    )
    for episode in range(args.episodes):
        args.seed = base_seed + episode
        env.seed(args.seed)
        obs = env.reset()
        initial_distance = goal_distance(env.last_raw_obs)
        min_distance = initial_distance
        total_reward = 0.0
        unsafe_events = 0
        success = 0.0
        final_distance = float("nan")
        steps = 0
        total_progress_reward = 0.0
        visual_corruption_magnitudes = []
        visual_frame_ages = []
        visual_frame_updates = 0
        for step_idx in range(args.max_episode_steps):
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, done, info = env.step(action)
            total_reward += float(reward)
            unsafe_events += int(float(info.get("unsafe_violation", 0.0)) > 0)
            success = float(info.get("is_success", 0.0))
            final_distance = goal_distance(env.last_raw_obs)
            min_distance = min(min_distance, final_distance)
            total_progress_reward += float(info.get("progress_reward", 0.0))
            visual_corruption_magnitudes.append(float(info.get("visual_corruption_magnitude", 0.0)))
            visual_frame_ages.append(float(info.get("visual_frame_age", 0.0)))
            visual_frame_updates += int(bool(info.get("visual_frame_updated", False)))
            steps = step_idx + 1
            if done:
                break
        rows.append(
            {
                "task": args.task,
                "model": str(args.model),
                "episode": episode,
                "seed": args.seed,
                "failure_mode": args.failure_mode,
                "observation_mode": args.observation_mode,
                "vision_corruption": args.vision_corruption,
                "vision_stride": args.vision_stride,
                "success": success,
                "steps": steps,
                "return": total_reward,
                "final_distance": final_distance,
                "initial_distance": initial_distance,
                "min_distance": min_distance,
                "net_distance_progress": initial_distance - final_distance,
                "total_progress_reward": total_progress_reward,
                "mean_visual_corruption_magnitude": float(np.mean(visual_corruption_magnitudes)) if visual_corruption_magnitudes else 0.0,
                "mean_visual_frame_age": float(np.mean(visual_frame_ages)) if visual_frame_ages else 0.0,
                "visual_frame_updates": visual_frame_updates,
                "unsafe_events": unsafe_events,
                "risk_level": risk_level(success, unsafe_events, final_distance),
            }
        )
    env.close()

    with args.out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"eval_csv={args.out}")


def main() -> None:
    run_evaluation(parse_args())


if __name__ == "__main__":
    main()
