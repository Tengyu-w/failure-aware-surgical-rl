from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from train_surrol_ppo_failure_aware import flatten_obs, make_env  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--surrol-root", type=Path, default=Path("/mnt/e/RL_projects/SurRoL_clean_SR-VPPV"))
    parser.add_argument("--task", default="NeedlePickRL-v0")
    parser.add_argument("--seed", type=int, default=43000)
    parser.add_argument("--demo-episodes", type=int, default=10)
    parser.add_argument("--max-episode-steps", type=int, default=60)
    parser.add_argument("--bc-epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--entropy-weight", type=float, default=0.001)
    parser.add_argument("--near-target-threshold", type=float, default=0.12)
    parser.add_argument("--near-target-weight", type=float, default=1.0)
    parser.add_argument("--observation-mode", default="pseudo_vision", choices=["state", "pseudo_vision", "render_pseudo_vision", "render_proprio_vision"])
    parser.add_argument("--pseudo-vision-noise", type=float, default=0.003)
    parser.add_argument("--vision-corruption", default="none", choices=["none", "gaussian_noise", "brightness_shift", "occlusion", "blackout", "mixed"])
    parser.add_argument("--vision-corruption-prob", type=float, default=0.0)
    parser.add_argument("--vision-corruption-severity", type=float, default=0.25)
    parser.add_argument("--vision-stride", type=int, default=1)
    parser.add_argument("--proprio-dim", type=int, default=7)
    parser.add_argument("--image-grid-size", type=int, default=4)
    parser.add_argument("--image-feature-mode", default="stats_gray", choices=["stats_gray", "stats_rgb"])
    parser.add_argument("--failure-mode", default="none", choices=["none", "action_noise", "action_dropout", "near_target_drift"])
    parser.add_argument("--failure-prob", type=float, default=0.0)
    parser.add_argument("--danger-zone", default="none")
    parser.add_argument("--danger-radius", type=float, default=0.052)
    parser.add_argument("--danger-penalty", type=float, default=2.0)
    parser.add_argument("--success-bonus", type=float, default=5.0)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "runs" / "surrol_ppo_bc_pretrain")
    return parser.parse_args()


def render_if_needed(env, observation_mode: str):
    if observation_mode not in {"render_pseudo_vision", "render_proprio_vision"}:
        return None
    return env._render_for_obs()


def collect_oracle_demos(args: argparse.Namespace):
    env = make_env(args)
    observations = []
    actions = []
    sample_weights = []
    rows = []
    for episode in range(args.demo_episodes):
        env.seed(args.seed + episode)
        raw_obs = env.env.reset()
        env.last_raw_obs = raw_obs
        env.steps = 0
        env._cached_rendered_image = None
        env._last_render_step = -1
        for step_idx in range(args.max_episode_steps):
            env.steps = step_idx
            rendered = render_if_needed(env, args.observation_mode)
            obs_vec = flatten_obs(
                raw_obs,
                args.observation_mode,
                env.rng,
                args.pseudo_vision_noise,
                rendered,
                getattr(args, "vision_corruption", "none"),
                getattr(args, "vision_corruption_prob", 0.0),
                getattr(args, "vision_corruption_severity", 0.25),
                None,
                args.proprio_dim,
                args.image_grid_size,
                args.image_feature_mode,
            )
            action = np.asarray(env.env.get_oracle_action(raw_obs), dtype=np.float32)
            achieved = np.asarray(raw_obs["achieved_goal"], dtype=np.float32).ravel()
            desired = np.asarray(raw_obs["desired_goal"], dtype=np.float32).ravel()
            goal_distance = float(np.linalg.norm(achieved[: min(achieved.size, desired.size)] - desired[: min(achieved.size, desired.size)]))
            sample_weight = args.near_target_weight if goal_distance < args.near_target_threshold else 1.0
            observations.append(obs_vec)
            actions.append(action)
            sample_weights.append(sample_weight)
            raw_obs, reward, done, info = env.env.step(action)
            success = float(info.get("is_success", 0.0))
            rows.append(
                {
                    "episode": episode,
                    "step": step_idx,
                    "success": success,
                    "reward": float(reward),
                    "action_norm": float(np.linalg.norm(action)),
                    "goal_distance": goal_distance,
                    "sample_weight": sample_weight,
                }
            )
            if success >= 1.0 or done:
                break
    env.close()
    return (
        np.asarray(observations, dtype=np.float32),
        np.asarray(actions, dtype=np.float32),
        np.asarray(sample_weights, dtype=np.float32),
        rows,
    )


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    from stable_baselines3 import PPO
    import torch
    import torch.nn.functional as F

    obs, actions, sample_weights, rows = collect_oracle_demos(args)
    np.savez_compressed(
        args.out_dir / "oracle_demos.npz",
        observations=obs,
        actions=actions,
        sample_weights=sample_weights,
    )
    with (args.out_dir / "oracle_demo_steps.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    train_env = make_env(args)
    model = PPO(
        "MlpPolicy",
        train_env,
        seed=args.seed,
        verbose=0,
        n_steps=256,
        batch_size=64,
        gamma=0.97,
        learning_rate=args.learning_rate,
    )
    optimizer = torch.optim.Adam(model.policy.parameters(), lr=args.learning_rate)
    obs_tensor = torch.as_tensor(obs, dtype=torch.float32, device=model.device)
    action_tensor = torch.as_tensor(actions, dtype=torch.float32, device=model.device)
    weight_tensor = torch.as_tensor(sample_weights, dtype=torch.float32, device=model.device)
    losses = []
    rng = np.random.default_rng(args.seed)
    for epoch in range(args.bc_epochs):
        order = rng.permutation(len(obs))
        epoch_losses = []
        for start in range(0, len(order), args.batch_size):
            idx = order[start : start + args.batch_size]
            batch_obs = obs_tensor[idx]
            batch_actions = action_tensor[idx]
            batch_weights = weight_tensor[idx]
            _, _, entropy = model.policy.evaluate_actions(batch_obs, batch_actions)
            pred_actions, _, _ = model.policy(batch_obs, deterministic=True)
            per_sample_mse = F.mse_loss(pred_actions, batch_actions, reduction="none").mean(dim=1)
            mse = (per_sample_mse * batch_weights).sum() / batch_weights.sum().clamp_min(1e-8)
            loss = mse - args.entropy_weight * entropy.mean()
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.policy.parameters(), 0.5)
            optimizer.step()
            epoch_losses.append(float(mse.detach().cpu()))
        losses.append({"epoch": epoch, "action_mse": float(np.mean(epoch_losses))})

    model.save(args.out_dir / "model_bc")
    with (args.out_dir / "bc_losses.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["epoch", "action_mse"])
        writer.writeheader()
        writer.writerows(losses)
    summary = {
        "task": args.task,
        "seed": args.seed,
        "demo_episodes": args.demo_episodes,
        "demo_steps": int(len(obs)),
        "observation_mode": args.observation_mode,
        "vision_corruption": args.vision_corruption,
        "vision_stride": args.vision_stride,
        "proprio_dim": args.proprio_dim,
        "image_grid_size": args.image_grid_size,
        "image_feature_mode": args.image_feature_mode,
        "bc_epochs": args.bc_epochs,
        "near_target_threshold": args.near_target_threshold,
        "near_target_weight": args.near_target_weight,
        "near_target_fraction": float(np.mean(sample_weights > 1.0)),
        "final_action_mse": losses[-1]["action_mse"] if losses else None,
        "model": str(args.out_dir / "model_bc.zip"),
    }
    (args.out_dir / "bc_summary.json").write_text(__import__("json").dumps(summary, indent=2), encoding="utf-8")
    train_env.close()
    print(f"model={args.out_dir / 'model_bc.zip'}")
    print(f"summary={args.out_dir / 'bc_summary.json'}")


if __name__ == "__main__":
    main()
