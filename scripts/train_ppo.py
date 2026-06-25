from __future__ import annotations

import argparse
from pathlib import Path

from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.monitor import Monitor

from constraint_surgical_rl import make_tool_manipulation_env, make_tool_navigation_env
from constraint_surgical_rl.envs.presets import CONFIG_PRESET_NAMES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--total-timesteps", type=int, default=25_000)
    parser.add_argument("--task", choices=("navigation", "manipulation"), default="navigation")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--variant",
        choices=(
            "conditioned",
            "conditioned_embedding_risk_penalty",
            "conditioned_embedding_risk_curriculum",
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
    parser.add_argument("--embedding-risk-dataset", type=Path, default=None)
    parser.add_argument("--embedding-risk-penalty-scale", type=float, default=0.75)
    parser.add_argument("--embedding-risk-threshold", type=float, default=0.55)
    parser.add_argument("--embedding-risk-curriculum-probability", type=float, default=0.35)
    parser.add_argument("--embedding-risk-curriculum-candidates", type=int, default=8)
    parser.add_argument("--init-model", type=Path, default=None)
    parser.add_argument("--verbose", type=int, default=1)
    parser.add_argument("--out-dir", type=Path, default=Path("runs") / "ppo_tool_navigation")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    if args.task == "navigation":
        env = make_tool_navigation_env(
            variant=args.variant,
            config_preset=args.config_preset,
            embedding_risk_dataset=args.embedding_risk_dataset,
            embedding_risk_penalty_scale=args.embedding_risk_penalty_scale,
            embedding_risk_threshold=args.embedding_risk_threshold,
            embedding_risk_curriculum_probability=args.embedding_risk_curriculum_probability,
            embedding_risk_curriculum_candidates=args.embedding_risk_curriculum_candidates,
        )
    else:
        env = make_tool_manipulation_env(variant=args.variant)
    check_env(env, warn=True)
    env = Monitor(env, filename=str(args.out_dir / "monitor.csv"))

    if args.init_model is None:
        model = PPO(
            "MlpPolicy",
            env,
            seed=args.seed,
            verbose=args.verbose,
            tensorboard_log=str(args.out_dir / "tb"),
            n_steps=512,
            batch_size=128,
            gamma=0.97,
        )
    else:
        model = PPO.load(args.init_model, env=env)
        model.verbose = args.verbose
        model.tensorboard_log = str(args.out_dir / "tb")
    model.learn(total_timesteps=args.total_timesteps, progress_bar=False)
    model.save(args.out_dir / "model")
    print(f"saved_model={args.out_dir / 'model.zip'}")


if __name__ == "__main__":
    main()
