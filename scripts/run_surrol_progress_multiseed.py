from __future__ import annotations

import argparse
import contextlib
import gc
import json
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRAIN_SCRIPT = ROOT / "scripts" / "train_surrol_ppo_failure_aware.py"
EVAL_SCRIPT = ROOT / "scripts" / "evaluate_surrol_ppo_failure_aware.py"

from evaluate_surrol_ppo_failure_aware import run_evaluation  # noqa: E402
from train_surrol_ppo_failure_aware import run_training  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--surrol-root", type=Path, default=Path("/mnt/e/RL_projects/SurRoL_clean_SR-VPPV"))
    parser.add_argument("--task", default="NeedleReachRL-v0")
    parser.add_argument("--scales", type=float, nargs="+", default=[0.0, 10.0, 30.0, 50.0])
    parser.add_argument("--seeds", type=int, nargs="+", default=[46000, 46001, 46002])
    parser.add_argument("--timesteps", type=int, default=2048)
    parser.add_argument("--eval-seed", type=int, default=47000)
    parser.add_argument("--eval-episodes", type=int, default=5)
    parser.add_argument("--max-episode-steps", type=int, default=75)
    parser.add_argument("--observation-mode", default="pseudo_vision", choices=["state", "pseudo_vision", "render_pseudo_vision", "render_proprio_vision"])
    parser.add_argument("--pseudo-vision-noise", type=float, default=0.003)
    parser.add_argument("--vision-corruption", default="none", choices=["none", "gaussian_noise", "brightness_shift", "occlusion", "blackout", "mixed"])
    parser.add_argument("--vision-corruption-prob", type=float, default=0.0)
    parser.add_argument("--vision-corruption-severity", type=float, default=0.25)
    parser.add_argument("--vision-stride", type=int, default=1)
    parser.add_argument("--eval-vision-corruption", default="none", choices=["none", "gaussian_noise", "brightness_shift", "occlusion", "blackout", "mixed"])
    parser.add_argument("--eval-vision-corruption-prob", type=float, default=0.0)
    parser.add_argument("--eval-vision-corruption-severity", type=float, default=0.25)
    parser.add_argument("--eval-vision-stride", type=int, default=1)
    parser.add_argument("--proprio-dim", type=int, default=7)
    parser.add_argument("--image-grid-size", type=int, default=4)
    parser.add_argument("--image-feature-mode", default="stats_gray", choices=["stats_gray", "stats_rgb"])
    parser.add_argument("--run-tag", default="")
    parser.add_argument("--out-root", type=Path, default=ROOT / "runs" / "surrol_progress_multiseed_round28")
    parser.add_argument("--execution-mode", choices=["subprocess", "in_process"], default="subprocess")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def scale_label(scale: float) -> str:
    return str(scale).replace("-", "m").replace(".", "p")


def run_logged(function, function_args: argparse.Namespace, log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as handle:
        with contextlib.redirect_stdout(handle), contextlib.redirect_stderr(handle):
            try:
                function(function_args)
            except Exception:
                traceback.print_exc(file=handle)
                return 1
            finally:
                gc.collect()
    return 0


def command_from_namespace(script: Path, function_args: argparse.Namespace) -> list[str]:
    command = [sys.executable, str(script)]
    for key, value in vars(function_args).items():
        if value is None or value is False:
            continue
        flag = "--" + key.replace("_", "-")
        if value is True:
            command.append(flag)
        else:
            command.extend([flag, str(value)])
    return command


def run_logged_subprocess(command: list[str], log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, text=True, check=False)
    return int(completed.returncode)


def write_manifest(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.out_root.mkdir(parents=True, exist_ok=True)
    manifest_name = f"manifest_{args.run_tag}.json" if args.run_tag else "manifest.json"
    manifest_path = args.out_root / manifest_name
    manifest = {
        "task": args.task,
        "scales": args.scales,
        "seeds": args.seeds,
        "timesteps": args.timesteps,
        "eval_seed": args.eval_seed,
        "eval_episodes": args.eval_episodes,
        "observation_mode": args.observation_mode,
        "vision_corruption": args.vision_corruption,
        "vision_corruption_prob": args.vision_corruption_prob,
        "vision_corruption_severity": args.vision_corruption_severity,
        "vision_stride": args.vision_stride,
        "eval_vision_corruption": args.eval_vision_corruption,
        "eval_vision_corruption_prob": args.eval_vision_corruption_prob,
        "eval_vision_corruption_severity": args.eval_vision_corruption_severity,
        "eval_vision_stride": args.eval_vision_stride,
        "proprio_dim": args.proprio_dim,
        "image_grid_size": args.image_grid_size,
        "image_feature_mode": args.image_feature_mode,
        "run_tag": args.run_tag,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "runs": [],
    }
    write_manifest(manifest_path, manifest)

    for scale in args.scales:
        for seed in args.seeds:
            run_dir = args.out_root / f"scale{scale_label(scale)}_seed{seed}"
            model_path = run_dir / "model.zip"
            eval_prefix = f"eval_{args.run_tag}" if args.run_tag else "eval"
            eval_path = run_dir / f"{eval_prefix}_seed{args.eval_seed}_{args.eval_episodes}ep.csv"
            record = {
                "scale": scale,
                "seed": seed,
                "run_dir": str(run_dir),
                "model": str(model_path),
                "eval": str(eval_path),
                "train_status": "pending",
                "eval_status": "pending",
            }
            manifest["runs"].append(record)
            write_manifest(manifest_path, manifest)

            if model_path.exists() and not args.force:
                record["train_status"] = "skipped_existing"
            else:
                train_args = argparse.Namespace(
                    surrol_root=args.surrol_root,
                    task=args.task,
                    seed=seed,
                    total_timesteps=args.timesteps,
                    max_episode_steps=args.max_episode_steps,
                    failure_mode="none",
                    failure_prob=0.0,
                    observation_mode=args.observation_mode,
                    pseudo_vision_noise=args.pseudo_vision_noise,
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
                    progress_reward_scale=scale,
                    progress_clip=0.03,
                    out_dir=run_dir,
                    init_model=None,
                    check_only=False,
                )
                print(f"TRAIN scale={scale:g} seed={seed}", flush=True)
                if args.execution_mode == "subprocess":
                    returncode = run_logged_subprocess(
                        command_from_namespace(TRAIN_SCRIPT, train_args), run_dir / "train.log"
                    )
                else:
                    returncode = run_logged(run_training, train_args, run_dir / "train.log")
                record["train_status"] = "complete" if returncode == 0 else f"failed_{returncode}"
                write_manifest(manifest_path, manifest)
                if returncode != 0:
                    print(f"TRAIN_FAILED scale={scale:g} seed={seed} log={run_dir / 'train.log'}", flush=True)
                    continue

            if eval_path.exists() and not args.force:
                record["eval_status"] = "skipped_existing"
            else:
                eval_args = argparse.Namespace(
                    model=model_path,
                    surrol_root=args.surrol_root,
                    task=args.task,
                    seed=args.eval_seed,
                    episodes=args.eval_episodes,
                    max_episode_steps=args.max_episode_steps,
                    failure_mode="none",
                    failure_prob=0.0,
                    observation_mode=args.observation_mode,
                    pseudo_vision_noise=args.pseudo_vision_noise,
                    vision_corruption=args.eval_vision_corruption,
                    vision_corruption_prob=args.eval_vision_corruption_prob,
                    vision_corruption_severity=args.eval_vision_corruption_severity,
                    vision_stride=args.eval_vision_stride,
                    proprio_dim=args.proprio_dim,
                    image_grid_size=args.image_grid_size,
                    image_feature_mode=args.image_feature_mode,
                    danger_zone="none",
                    danger_radius=0.052,
                    danger_penalty=2.0,
                    success_bonus=5.0,
                    progress_reward_scale=scale,
                    progress_clip=0.03,
                    out=eval_path,
                )
                print(f"EVAL scale={scale:g} seed={seed}", flush=True)
                if args.execution_mode == "subprocess":
                    returncode = run_logged_subprocess(
                        command_from_namespace(EVAL_SCRIPT, eval_args), run_dir / "eval.log"
                    )
                else:
                    returncode = run_logged(run_evaluation, eval_args, run_dir / "eval.log")
                record["eval_status"] = "complete" if returncode == 0 else f"failed_{returncode}"
                write_manifest(manifest_path, manifest)

    manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
    write_manifest(manifest_path, manifest)
    completed = sum(record["eval_status"] in {"complete", "skipped_existing"} for record in manifest["runs"])
    print(f"completed_evaluations={completed}/{len(manifest['runs'])}", flush=True)
    print(f"manifest={manifest_path}", flush=True)


if __name__ == "__main__":
    main()
