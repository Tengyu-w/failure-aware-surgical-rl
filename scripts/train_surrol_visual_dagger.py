from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from train_surrol_ppo_failure_aware import goal_distance, make_env  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--init-model", type=Path, required=True)
    parser.add_argument("--base-dataset", type=Path, required=True)
    parser.add_argument("--surrol-root", type=Path, default=Path("/mnt/e/RL_projects/SurRoL_clean_SR-VPPV"))
    parser.add_argument("--task", default="NeedleReachRL-v0")
    parser.add_argument("--seed", type=int, default=50700)
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--rollout-episodes", type=int, default=10)
    parser.add_argument("--max-episode-steps", type=int, default=50)
    parser.add_argument("--beta-start", type=float, default=0.5)
    parser.add_argument("--beta-end", type=float, default=0.0)
    parser.add_argument("--epochs-per-round", type=int, default=60)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--entropy-weight", type=float, default=0.001)
    parser.add_argument("--near-target-threshold", type=float, default=0.12)
    parser.add_argument("--near-target-weight", type=float, default=4.0)
    parser.add_argument("--vision-corruption", default="mixed", choices=["none", "gaussian_noise", "brightness_shift", "occlusion", "blackout", "mixed"])
    parser.add_argument("--vision-corruption-prob", type=float, default=0.35)
    parser.add_argument("--vision-corruption-severity", type=float, default=0.25)
    parser.add_argument("--vision-stride", type=int, default=4)
    parser.add_argument("--proprio-dim", type=int, default=7)
    parser.add_argument("--image-grid-size", type=int, default=8)
    parser.add_argument("--image-feature-mode", default="stats_rgb", choices=["stats_gray", "stats_rgb"])
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args()


def build_env_args(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        surrol_root=args.surrol_root,
        task=args.task,
        seed=args.seed,
        max_episode_steps=args.max_episode_steps,
        failure_mode="none",
        failure_prob=0.0,
        observation_mode="render_proprio_vision",
        pseudo_vision_noise=0.003,
        vision_corruption=args.vision_corruption,
        vision_corruption_prob=args.vision_corruption_prob,
        vision_corruption_severity=args.vision_corruption_severity,
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


def choose_execution_action(
    policy_action: np.ndarray,
    oracle_action: np.ndarray,
    beta: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, str]:
    if rng.random() < float(np.clip(beta, 0.0, 1.0)):
        return np.asarray(oracle_action, dtype=np.float32), "oracle"
    return np.asarray(policy_action, dtype=np.float32), "policy"


def beta_for_round(args: argparse.Namespace, round_index: int) -> float:
    if args.rounds <= 1:
        return args.beta_end
    fraction = round_index / (args.rounds - 1)
    return float(args.beta_start + fraction * (args.beta_end - args.beta_start))


def collect_round(model, env, args: argparse.Namespace, round_index: int, rng: np.random.Generator):
    observations = []
    oracle_actions = []
    weights = []
    rows = []
    beta = beta_for_round(args, round_index)
    for episode in range(args.rollout_episodes):
        episode_seed = args.seed + round_index * 1000 + episode
        env.seed(episode_seed)
        obs = env.reset()
        start = len(rows)
        min_distance = goal_distance(env.last_raw_obs)
        success = 0.0
        final_distance = min_distance
        for step in range(args.max_episode_steps):
            raw_obs = env.last_raw_obs
            distance_before = goal_distance(raw_obs)
            oracle_action = np.asarray(env.env.get_oracle_action(raw_obs), dtype=np.float32)
            policy_action = np.asarray(model.predict(obs, deterministic=True)[0], dtype=np.float32)
            executed_action, source = choose_execution_action(policy_action, oracle_action, beta, rng)
            weight = args.near_target_weight if distance_before < args.near_target_threshold else 1.0
            observations.append(np.asarray(obs, dtype=np.float32))
            oracle_actions.append(oracle_action)
            weights.append(weight)
            next_obs, _, done, info = env.step(executed_action)
            final_distance = goal_distance(env.last_raw_obs)
            min_distance = min(min_distance, final_distance)
            success = float(info.get("is_success", 0.0))
            rows.append(
                {
                    "round": round_index,
                    "episode": episode,
                    "seed": episode_seed,
                    "step": step,
                    "beta": beta,
                    "executed_source": source,
                    "goal_distance_before": distance_before,
                    "goal_distance_after": final_distance,
                    "oracle_action_norm": float(np.linalg.norm(oracle_action)),
                    "policy_action_norm": float(np.linalg.norm(policy_action)),
                    "policy_oracle_action_l2": float(np.linalg.norm(policy_action - oracle_action)),
                    "sample_weight": weight,
                    "visual_corruption_magnitude": float(info.get("visual_corruption_magnitude", 0.0)),
                }
            )
            obs = next_obs
            if done:
                break
        for row in rows[start:]:
            row["episode_success"] = success
            row["episode_min_distance"] = min_distance
            row["episode_final_distance"] = final_distance
    return (
        np.asarray(observations, dtype=np.float32),
        np.asarray(oracle_actions, dtype=np.float32),
        np.asarray(weights, dtype=np.float32),
        rows,
    )


def train_supervised(model, observations, actions, weights, args, round_index: int):
    import torch
    import torch.nn.functional as F

    optimizer = torch.optim.Adam(model.policy.parameters(), lr=args.learning_rate)
    obs_tensor = torch.as_tensor(observations, dtype=torch.float32, device=model.device)
    action_tensor = torch.as_tensor(actions, dtype=torch.float32, device=model.device)
    weight_tensor = torch.as_tensor(weights, dtype=torch.float32, device=model.device)
    rng = np.random.default_rng(args.seed + 10000 + round_index)
    losses = []
    for epoch in range(args.epochs_per_round):
        order = rng.permutation(len(observations))
        epoch_losses = []
        for start in range(0, len(order), args.batch_size):
            idx = order[start : start + args.batch_size]
            batch_obs = obs_tensor[idx]
            batch_actions = action_tensor[idx]
            batch_weights = weight_tensor[idx]
            predicted_actions, _, _ = model.policy(batch_obs, deterministic=True)
            _, _, entropy = model.policy.evaluate_actions(batch_obs, batch_actions)
            per_sample_mse = F.mse_loss(predicted_actions, batch_actions, reduction="none").mean(dim=1)
            mse = (per_sample_mse * batch_weights).sum() / batch_weights.sum().clamp_min(1e-8)
            loss = mse - args.entropy_weight * entropy.mean()
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.policy.parameters(), 0.5)
            optimizer.step()
            epoch_losses.append(float(mse.detach().cpu()))
        losses.append(
            {
                "round": round_index,
                "epoch": epoch,
                "weighted_action_mse": float(np.mean(epoch_losses)),
            }
        )
    return losses


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    from stable_baselines3 import PPO

    dataset = np.load(args.base_dataset)
    observations = np.asarray(dataset["observations"], dtype=np.float32)
    actions = np.asarray(dataset["actions"], dtype=np.float32)
    if "sample_weights" in dataset.files:
        weights = np.asarray(dataset["sample_weights"], dtype=np.float32)
    else:
        weights = np.ones(len(observations), dtype=np.float32)

    config = build_env_args(args)
    env = make_env(config)
    model = PPO.load(
        args.init_model,
        env=env,
        custom_objects={"observation_space": env.observation_space, "action_space": env.action_space},
    )
    if tuple(observations.shape[1:]) != tuple(env.observation_space.shape):
        raise ValueError(
            f"Base dataset observation shape {observations.shape[1:]} does not match env {env.observation_space.shape}"
        )

    rng = np.random.default_rng(args.seed)
    all_rows = []
    all_losses = []
    summaries = []
    for round_index in range(args.rounds):
        new_obs, new_actions, new_weights, rows = collect_round(model, env, args, round_index, rng)
        observations = np.concatenate([observations, new_obs], axis=0)
        actions = np.concatenate([actions, new_actions], axis=0)
        weights = np.concatenate([weights, new_weights], axis=0)
        losses = train_supervised(model, observations, actions, weights, args, round_index)
        all_rows.extend(rows)
        all_losses.extend(losses)
        model_path = args.out_dir / f"model_dagger_round{round_index + 1}"
        model.save(model_path)
        np.savez_compressed(
            args.out_dir / f"dataset_round{round_index + 1}.npz",
            observations=observations,
            actions=actions,
            sample_weights=weights,
        )
        episode_successes = {
            int(row["episode"]): float(row["episode_success"])
            for row in rows
        }
        summaries.append(
            {
                "round": round_index,
                "beta": beta_for_round(args, round_index),
                "new_samples": len(new_obs),
                "total_samples": len(observations),
                "rollout_success_rate": float(np.mean(list(episode_successes.values()))) if episode_successes else 0.0,
                "mean_policy_oracle_action_l2": float(np.mean([row["policy_oracle_action_l2"] for row in rows])),
                "final_weighted_action_mse": losses[-1]["weighted_action_mse"],
                "model": str(model_path.with_suffix(".zip")),
            }
        )
    env.close()

    write_csv(args.out_dir / "dagger_steps.csv", all_rows)
    write_csv(args.out_dir / "dagger_losses.csv", all_losses)
    write_csv(args.out_dir / "dagger_round_summary.csv", summaries)
    (args.out_dir / "dagger_config.json").write_text(
        json.dumps({key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}, indent=2),
        encoding="utf-8",
    )
    print(f"summary={args.out_dir / 'dagger_round_summary.csv'}")
    print(f"final_model={summaries[-1]['model']}")


if __name__ == "__main__":
    main()
