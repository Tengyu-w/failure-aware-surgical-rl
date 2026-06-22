from __future__ import annotations

import argparse
import json
from pathlib import Path

from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.monitor import Monitor

from constraint_surgical_rl import make_tool_navigation_env
from constraint_surgical_rl.envs.presets import CONFIG_PRESET_NAMES


VARIANTS = (
    "conditioned",
    "conditioned_shielded",
    "conditioned_tangent_shielded",
    "no_phase_budget",
    "no_phase_budget_shielded",
    "no_phase_budget_tangent_shielded",
    "no_budget",
)


def parse_stage(text: str) -> tuple[str, int]:
    if ":" not in text:
        raise argparse.ArgumentTypeError("Stage must look like preset:timesteps, e.g. easy:10000")
    preset, steps_text = text.split(":", 1)
    if preset not in CONFIG_PRESET_NAMES:
        raise argparse.ArgumentTypeError(f"Unknown preset {preset}. Choices: {', '.join(CONFIG_PRESET_NAMES)}")
    steps = int(steps_text)
    if steps <= 0:
        raise argparse.ArgumentTypeError("Stage timesteps must be positive.")
    return preset, steps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=VARIANTS, default="conditioned")
    parser.add_argument("--stage", action="append", type=parse_stage, default=None)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out-dir", type=Path, default=Path("runs") / "curriculum_tool_navigation")
    parser.add_argument("--verbose", type=int, default=1)
    return parser.parse_args()


def make_monitored_env(variant: str, preset: str, out_dir: Path, stage_idx: int):
    env = make_tool_navigation_env(variant=variant, config_preset=preset)
    if stage_idx == 0:
        check_env(env, warn=True)
    return Monitor(env, filename=str(out_dir / f"monitor_stage{stage_idx}_{preset}.csv"))


def main() -> None:
    args = parse_args()
    stages = args.stage or [("easy", 5_000), ("prototype", 5_000)]
    args.out_dir.mkdir(parents=True, exist_ok=True)

    model: PPO | None = None
    stage_records = []
    for stage_idx, (preset, steps) in enumerate(stages):
        env = make_monitored_env(args.variant, preset, args.out_dir, stage_idx)
        if model is None:
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
            model.set_env(env)

        reset_num_timesteps = stage_idx == 0
        model.learn(
            total_timesteps=steps,
            reset_num_timesteps=reset_num_timesteps,
            tb_log_name=f"stage{stage_idx}_{preset}",
            progress_bar=False,
        )
        stage_model_path = args.out_dir / f"model_stage{stage_idx}_{preset}"
        model.save(stage_model_path)
        stage_records.append({"stage": stage_idx, "preset": preset, "timesteps": steps, "model": str(stage_model_path)})

    assert model is not None
    model.save(args.out_dir / "model")
    metadata = {"variant": args.variant, "seed": args.seed, "stages": stage_records}
    (args.out_dir / "curriculum.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"saved_model={args.out_dir / 'model.zip'}")
    print(f"curriculum_metadata={args.out_dir / 'curriculum.json'}")


if __name__ == "__main__":
    main()
