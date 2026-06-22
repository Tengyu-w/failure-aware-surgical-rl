from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from evaluate_surrol_visual_risk_routing import (  # noqa: E402
    VisualActionRiskHead,
    VisualRecoveryMemory,
    env_args,
)
from train_surrol_ppo_failure_aware import goal_distance, make_env  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--risk-head", type=Path, required=True)
    parser.add_argument("--recovery-memory", type=Path, required=True)
    parser.add_argument("--risk-threshold", type=float, default=0.4)
    parser.add_argument("--action-gap-threshold", type=float, default=0.25)
    parser.add_argument("--intervention-horizon", type=int, default=5)
    parser.add_argument("--surrol-root", type=Path, default=Path("/mnt/e/RL_projects/SurRoL_clean_SR-VPPV"))
    parser.add_argument("--task", default="NeedleReachRL-v0")
    parser.add_argument("--seed", type=int, default=51000)
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--max-episode-steps", type=int, default=75)
    parser.add_argument("--vision-stride", type=int, default=4)
    parser.add_argument("--proprio-dim", type=int, default=7)
    parser.add_argument("--image-grid-size", type=int, default=8)
    parser.add_argument("--image-feature-mode", default="stats_rgb", choices=["stats_gray", "stats_rgb"])
    parser.add_argument(
        "--vision-corruption",
        default="none",
        choices=["none", "gaussian_noise", "brightness_shift", "occlusion", "blackout", "mixed"],
    )
    parser.add_argument("--vision-corruption-prob", type=float, default=0.0)
    parser.add_argument("--vision-corruption-severity", type=float, default=0.25)
    parser.add_argument("--visual-adapter", type=Path, default=None)
    parser.add_argument(
        "--collection-mode",
        default="targeted_ood",
        choices=["targeted_ood", "all_steps"],
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args()


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    from stable_baselines3 import PPO

    risk_head = VisualActionRiskHead(args.risk_head)
    recovery_memory = VisualRecoveryMemory(args.recovery_memory)
    env = make_env(env_args(args))
    model = PPO.load(
        args.model,
        env=env,
        custom_objects={"observation_space": env.observation_space, "action_space": env.action_space},
    )
    observations: list[np.ndarray] = []
    oracle_actions: list[np.ndarray] = []
    step_rows: list[dict] = []
    episode_rows: list[dict] = []

    for episode in range(args.episodes):
        episode_seed = args.seed + episode
        env.seed(episode_seed)
        obs = env.reset()
        success = 0.0
        interventions = 0
        collected_start = len(observations)
        min_distance = goal_distance(env.last_raw_obs)
        step = 0
        while step < args.max_episode_steps:
            risk = risk_head.score(obs)
            policy_action = np.asarray(model.predict(obs, deterministic=True)[0], dtype=np.float32)
            recovery_action, memory_distance = recovery_memory.predict(obs)
            if args.collection_mode == "all_steps":
                oracle_action = np.asarray(env.env.get_oracle_action(env.last_raw_obs), dtype=np.float32)
                action_gap = float(np.linalg.norm(policy_action - oracle_action))
                observations.append(np.asarray(obs, dtype=np.float32))
                oracle_actions.append(oracle_action)
                step_rows.append(
                    {
                        "episode": episode,
                        "seed": episode_seed,
                        "step": step,
                        "intervention": interventions,
                        "intervention_step": 0,
                        "predicted_risk": risk,
                        "memory_distance": memory_distance,
                        "policy_oracle_action_l2": action_gap,
                        "goal_distance_before": goal_distance(env.last_raw_obs),
                        "eligible_high_gap": action_gap >= args.action_gap_threshold,
                    }
                )
                obs, _, done, info = env.step(policy_action)
                step += 1
                success = float(info.get("is_success", 0.0))
                min_distance = min(min_distance, goal_distance(env.last_raw_obs))
                if done:
                    break
                continue
            high_risk_ood = risk >= args.risk_threshold and memory_distance > recovery_memory.max_neighbor_distance
            if high_risk_ood:
                interventions += 1
                for intervention_step in range(args.intervention_horizon):
                    oracle_action = np.asarray(env.env.get_oracle_action(env.last_raw_obs), dtype=np.float32)
                    current_policy = np.asarray(model.predict(obs, deterministic=True)[0], dtype=np.float32)
                    action_gap = float(np.linalg.norm(current_policy - oracle_action))
                    current_risk = risk_head.score(obs)
                    _, current_memory_distance = recovery_memory.predict(obs)
                    observations.append(np.asarray(obs, dtype=np.float32))
                    oracle_actions.append(oracle_action)
                    step_rows.append(
                        {
                            "episode": episode,
                            "seed": episode_seed,
                            "step": step,
                            "intervention": interventions,
                            "intervention_step": intervention_step,
                            "predicted_risk": current_risk,
                            "memory_distance": current_memory_distance,
                            "policy_oracle_action_l2": action_gap,
                            "goal_distance_before": goal_distance(env.last_raw_obs),
                            "eligible_high_gap": action_gap >= args.action_gap_threshold,
                        }
                    )
                    obs, _, done, info = env.step(oracle_action)
                    step += 1
                    success = float(info.get("is_success", 0.0))
                    min_distance = min(min_distance, goal_distance(env.last_raw_obs))
                    if done or step >= args.max_episode_steps:
                        break
                if done or step >= args.max_episode_steps:
                    break
                continue

            action = recovery_action if risk >= args.risk_threshold else policy_action
            obs, _, done, info = env.step(action)
            step += 1
            success = float(info.get("is_success", 0.0))
            min_distance = min(min_distance, goal_distance(env.last_raw_obs))
            if done:
                break

        episode_rows.append(
            {
                "episode": episode,
                "seed": episode_seed,
                "success": success,
                "steps": step,
                "interventions": interventions,
                "collected_steps": len(observations) - collected_start,
                "eligible_high_gap_steps": int(
                    sum(row["eligible_high_gap"] for row in step_rows if row["episode"] == episode)
                ),
                "min_distance": min_distance,
                "final_distance": goal_distance(env.last_raw_obs),
            }
        )
    env.close()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.out_dir / "ood_recovery_dagger.npz",
        observations=np.asarray(observations, dtype=np.float32),
        actions=np.asarray(oracle_actions, dtype=np.float32),
    )
    write_csv(args.out_dir / "ood_recovery_steps.csv", step_rows)
    write_csv(args.out_dir / "ood_recovery_episodes.csv", episode_rows)
    eligible = int(sum(row["eligible_high_gap"] for row in step_rows))
    summary = {
        "episodes": args.episodes,
        "success_rate_with_collection_oracle": float(np.mean([row["success"] for row in episode_rows])),
        "episodes_with_intervention": int(sum(row["interventions"] > 0 for row in episode_rows)),
        "collected_steps": len(observations),
        "eligible_high_gap_steps": eligible,
        "vision_corruption": args.vision_corruption,
        "vision_corruption_prob": args.vision_corruption_prob,
        "vision_corruption_severity": args.vision_corruption_severity,
        "visual_adapter": None if args.visual_adapter is None else str(args.visual_adapter),
        "collection_mode": args.collection_mode,
        "note": "Oracle is used only to label targeted OOD DAgger collection, not in deployment evaluation.",
    }
    (args.out_dir / "collection_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"dataset={args.out_dir / 'ood_recovery_dagger.npz'}")
    print(f"collected_steps={len(observations)}")
    print(f"eligible_high_gap_steps={eligible}")


if __name__ == "__main__":
    main()
