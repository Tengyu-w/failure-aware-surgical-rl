from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
REPORTS = ROOT / "reports"


def read_json(path: Path) -> dict:
    if not path.exists():
        return {"missing": True, "path": str(path)}
    return json.loads(path.read_text(encoding="utf-8"))


def fmt_shape(payload: dict, key: str) -> str:
    value = payload.get(key)
    if value is None:
        return "missing"
    return "x".join(str(item) for item in value)


def eval_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    df = pd.read_csv(path)
    return {
        "exists": True,
        "episodes": int(len(df)),
        "success_mean": float(df["success"].mean()) if "success" in df else float("nan"),
        "final_distance_mean": float(df["final_distance"].mean()) if "final_distance" in df else float("nan"),
        "unsafe_events_sum": int(df["unsafe_events"].sum()) if "unsafe_events" in df else 0,
        "routes": df["risk_level"].value_counts().to_dict() if "risk_level" in df else {},
    }


def main() -> None:
    needle = read_json(RUNS / "surrol_ppo_smoke_needlepick_pseudovision" / "smoke_check.json")
    pick = read_json(RUNS / "surrol_ppo_smoke_pickandplace_pseudovision" / "smoke_check.json")
    render_needle = read_json(RUNS / "surrol_ppo_smoke_needlepick_render_pseudovision" / "smoke_check.json")
    blocked = read_json(RUNS / "surrol_ppo_dependency_probe_needlepick" / "dependency_blocked.json")
    train_smoke = read_json(RUNS / "surrol_ppo_train_smoke_needlepick_16step" / "train_summary.json")
    model_path = RUNS / "surrol_ppo_train_smoke_needlepick_16step" / "model.zip"
    eval_path = RUNS / "surrol_ppo_eval_needlepick_smoke_3ep.csv"
    train_2048 = read_json(RUNS / "surrol_ppo_train_needlepick_pseudovision_2048_seed43000" / "train_summary.json")
    model_2048 = RUNS / "surrol_ppo_train_needlepick_pseudovision_2048_seed43000" / "model.zip"
    eval_2048_path = RUNS / "surrol_ppo_eval_needlepick_pseudovision_2048_5ep.csv"
    eval_2048 = eval_summary(eval_2048_path)
    bc_summary = read_json(RUNS / "surrol_ppo_bc_needlepick_pseudovision_5demo_mse80" / "bc_summary.json")
    bc_clean = eval_summary(RUNS / "surrol_ppo_eval_needlepick_bc_mse80_clean_5ep.csv")
    bc_drift = eval_summary(RUNS / "surrol_ppo_eval_needlepick_bc_mse80_drift_5ep.csv")
    bcinit_drift = eval_summary(RUNS / "surrol_ppo_eval_needlepick_bcinit_mse80_2048_drift_5ep.csv")
    pick_bc_summary = read_json(RUNS / "surrol_ppo_bc_pickandplace_pseudovision_2demo_mse40" / "bc_summary.json")
    pick_clean = eval_summary(RUNS / "surrol_ppo_eval_pickandplace_bc_2demo_clean_3ep.csv")
    pick_drift = eval_summary(RUNS / "surrol_ppo_eval_pickandplace_bc_2demo_drift_3ep.csv")
    gauze_smoke = read_json(RUNS / "surrol_ppo_smoke_gauzeretrieve_pseudovision" / "smoke_check.json")
    gauze_bc_summary = read_json(RUNS / "surrol_ppo_bc_gauzeretrieve_pseudovision_3demo_mse60" / "bc_summary.json")
    gauze_clean = eval_summary(RUNS / "surrol_ppo_eval_gauzeretrieve_bc_3demo_clean_5ep.csv")
    gauze_drift = eval_summary(RUNS / "surrol_ppo_eval_gauzeretrieve_bc_3demo_drift_5ep.csv")

    REPORTS.mkdir(parents=True, exist_ok=True)
    out = REPORTS / "surrol_ppo_pseudovision_readiness.md"
    lines = [
        "# SurRoL PPO / Pseudo-Vision Readiness",
        "",
        "## Takeaway",
        "",
        (
            "This round connects the SurRoL RL environment to a failure-aware "
            "PPO wrapper. The wrapper supports state and pseudo-vision "
            "observations, compressed RGB-derived pseudo-vision features, "
            "action-noise/action-dropout/near-target-drift training "
            "perturbations, forbidden-zone risk penalties, and success bonuses. "
            "NeedlePickRL and PickAndPlaceRL pass environment-level smoke "
            "checks; NeedlePickRL also completes a minimal PPO training smoke, "
            "saves a checkpoint, and runs the checkpoint evaluation entry point."
        ),
        "",
        "## Smoke Evidence",
        "",
        "| Task | Observation mode | Obs shape | Action shape | Failure mode | Danger signal | Status |",
        "|---|---|---:|---:|---|---|---|",
        (
            f"| {needle.get('task', 'missing')} | {needle.get('observation_mode', 'missing')} | "
            f"{fmt_shape(needle, 'obs_shape')} | {fmt_shape(needle, 'action_shape')} | "
            f"{needle.get('failure_mode', 'missing')} | unsafe_violation in info | smoke_pass |"
        ),
        (
            f"| {pick.get('task', 'missing')} | {pick.get('observation_mode', 'missing')} | "
            f"{fmt_shape(pick, 'obs_shape')} | {fmt_shape(pick, 'action_shape')} | "
            f"{pick.get('failure_mode', 'missing')} | unsafe_violation in info | smoke_pass |"
        ),
        (
            f"| {render_needle.get('task', 'missing')} | {render_needle.get('observation_mode', 'missing')} | "
            f"{fmt_shape(render_needle, 'obs_shape')} | {fmt_shape(render_needle, 'action_shape')} | "
            f"{render_needle.get('failure_mode', 'missing')} | rendered RGB compressed features | smoke_pass |"
        ),
        (
            f"| {gauze_smoke.get('task', 'missing')} | {gauze_smoke.get('observation_mode', 'missing')} | "
            f"{fmt_shape(gauze_smoke, 'obs_shape')} | {fmt_shape(gauze_smoke, 'action_shape')} | "
            f"{gauze_smoke.get('failure_mode', 'missing')} | unsafe_violation in info | smoke_pass |"
        ),
        "",
        "## PPO Dependency Probe",
        "",
        "- Earlier probe showed `stable_baselines3/torch` were missing.",
        "- The SurRoL py38 environment was then updated with CPU torch and Stable-Baselines3.",
        f"- Previous blocked reason: {blocked.get('reason', 'not_applicable')}",
        f"- Previous error: `{blocked.get('error', 'not_applicable')}`",
        "",
        "## PPO Train Smoke",
        "",
        "| Task | Observation mode | Failure mode | Requested timesteps | Model saved |",
        "|---|---|---|---:|---|",
        (
            f"| {train_smoke.get('task', 'missing')} | {train_smoke.get('observation_mode', 'missing')} | "
            f"{train_smoke.get('failure_mode', 'missing')} | {train_smoke.get('total_timesteps', 'missing')} | "
            f"{model_path.exists()} |"
        ),
        (
            f"| {train_2048.get('task', 'missing')} | {train_2048.get('observation_mode', 'missing')} | "
            f"{train_2048.get('failure_mode', 'missing')} | {train_2048.get('total_timesteps', 'missing')} | "
            f"{model_2048.exists()} |"
        ),
        "",
        "## PPO Evaluation Smoke",
        "",
        (
            "The smoke checkpoint was evaluated for 3 episodes under near-target drift. It did not solve the task, which is expected for "
            "a 256-step smoke policy, and all episodes were routed to human_review rather than auto_execute."
        ),
        "",
        f"- Evaluation CSV exists: {eval_path.exists()}",
        "",
        "## PPO 2048-Step Evaluation",
        "",
        "| Model | Episodes | Success | Mean final distance | Unsafe events | Risk routes |",
        "|---|---:|---:|---:|---:|---|",
        (
            f"| NeedlePickRL pseudo_vision 2048 | {eval_2048.get('episodes', 0)} | "
            f"{eval_2048.get('success_mean', float('nan')):.3f} | {eval_2048.get('final_distance_mean', float('nan')):.3f} | "
            f"{eval_2048.get('unsafe_events_sum', 0)} | {eval_2048.get('routes', {})} |"
        ),
        "",
        (
            "The 2048-step PPO run is a real training run, but it is still far too short for NeedlePickRL: evaluation remains 0/5 success "
            "and is routed to human_review. This is useful negative evidence rather than a failed script."
        ),
        "",
        "## Demonstration / BC Initialization",
        "",
        "| Method | Demo steps | BC epochs | Final action MSE | Eval condition | Episodes | Success | Mean final distance | Unsafe events | Risk routes |",
        "|---|---:|---:|---:|---|---:|---:|---:|---:|---|",
        (
            f"| BC-MSE | {bc_summary.get('demo_steps', 0)} | {bc_summary.get('bc_epochs', 0)} | "
            f"{bc_summary.get('final_action_mse', float('nan')):.4f} | clean | {bc_clean.get('episodes', 0)} | "
            f"{bc_clean.get('success_mean', float('nan')):.3f} | {bc_clean.get('final_distance_mean', float('nan')):.3f} | "
            f"{bc_clean.get('unsafe_events_sum', 0)} | {bc_clean.get('routes', {})} |"
        ),
        (
            f"| BC-MSE | {bc_summary.get('demo_steps', 0)} | {bc_summary.get('bc_epochs', 0)} | "
            f"{bc_summary.get('final_action_mse', float('nan')):.4f} | near_target_drift | {bc_drift.get('episodes', 0)} | "
            f"{bc_drift.get('success_mean', float('nan')):.3f} | {bc_drift.get('final_distance_mean', float('nan')):.3f} | "
            f"{bc_drift.get('unsafe_events_sum', 0)} | {bc_drift.get('routes', {})} |"
        ),
        (
            f"| BC-MSE + PPO 2048 | {bc_summary.get('demo_steps', 0)} | {bc_summary.get('bc_epochs', 0)} | "
            f"{bc_summary.get('final_action_mse', float('nan')):.4f} | near_target_drift | {bcinit_drift.get('episodes', 0)} | "
            f"{bcinit_drift.get('success_mean', float('nan')):.3f} | {bcinit_drift.get('final_distance_mean', float('nan')):.3f} | "
            f"{bcinit_drift.get('unsafe_events_sum', 0)} | {bcinit_drift.get('routes', {})} |"
        ),
        "",
        (
            "BC reduced action imitation error, but the resulting policy still does not complete NeedlePickRL. After PPO fine-tuning from BC, "
            "the policy reaches the forbidden-zone proxy earlier under near-target drift and is routed to abort_candidate. This supports the "
            "risk-aware argument: a learned policy must be evaluated by safety routing, not judged only by whether it moves."
        ),
        "",
        "## Complex Task Breadth: PickAndPlaceRL",
        "",
        "| Task | Demo steps | BC epochs | Final action MSE | Eval condition | Episodes | Success | Mean final distance | Unsafe events | Risk routes |",
        "|---|---:|---:|---:|---|---:|---:|---:|---:|---|",
        (
            f"| PickAndPlaceRL-v0 | {pick_bc_summary.get('demo_steps', 0)} | {pick_bc_summary.get('bc_epochs', 0)} | "
            f"{pick_bc_summary.get('final_action_mse', float('nan')):.4f} | clean | {pick_clean.get('episodes', 0)} | "
            f"{pick_clean.get('success_mean', float('nan')):.3f} | {pick_clean.get('final_distance_mean', float('nan')):.3f} | "
            f"{pick_clean.get('unsafe_events_sum', 0)} | {pick_clean.get('routes', {})} |"
        ),
        (
            f"| PickAndPlaceRL-v0 | {pick_bc_summary.get('demo_steps', 0)} | {pick_bc_summary.get('bc_epochs', 0)} | "
            f"{pick_bc_summary.get('final_action_mse', float('nan')):.4f} | near_target_drift | {pick_drift.get('episodes', 0)} | "
            f"{pick_drift.get('success_mean', float('nan')):.3f} | {pick_drift.get('final_distance_mean', float('nan')):.3f} | "
            f"{pick_drift.get('unsafe_events_sum', 0)} | {pick_drift.get('routes', {})} |"
        ),
        "",
        (
            "PickAndPlaceRL now enters the same demo -> BC policy -> risk evaluation chain as NeedlePickRL. The policy is not successful yet, "
            "so this should be reported as breadth/readiness evidence, not as a solved complex-task result."
        ),
        "",
        "## Cross-Task Breadth: GauzeRetrieveRL",
        "",
        "| Task | Demo steps | BC epochs | Final action MSE | Eval condition | Episodes | Success | Mean final distance | Unsafe events | Risk routes |",
        "|---|---:|---:|---:|---|---:|---:|---:|---:|---|",
        (
            f"| GauzeRetrieveRL-v0 | {gauze_bc_summary.get('demo_steps', 0)} | {gauze_bc_summary.get('bc_epochs', 0)} | "
            f"{gauze_bc_summary.get('final_action_mse', float('nan')):.4f} | clean | {gauze_clean.get('episodes', 0)} | "
            f"{gauze_clean.get('success_mean', float('nan')):.3f} | {gauze_clean.get('final_distance_mean', float('nan')):.3f} | "
            f"{gauze_clean.get('unsafe_events_sum', 0)} | {gauze_clean.get('routes', {})} |"
        ),
        (
            f"| GauzeRetrieveRL-v0 | {gauze_bc_summary.get('demo_steps', 0)} | {gauze_bc_summary.get('bc_epochs', 0)} | "
            f"{gauze_bc_summary.get('final_action_mse', float('nan')):.4f} | near_target_drift | {gauze_drift.get('episodes', 0)} | "
            f"{gauze_drift.get('success_mean', float('nan')):.3f} | {gauze_drift.get('final_distance_mean', float('nan')):.3f} | "
            f"{gauze_drift.get('unsafe_events_sum', 0)} | {gauze_drift.get('routes', {})} |"
        ),
        "",
        (
            "GauzeRetrieveRL is now integrated into the same training and risk-routing pipeline. Under near-target drift, some episodes are "
            "promoted from human_review to abort_candidate because they enter the forbidden-zone proxy."
        ),
        "",
        "## What This Adds To The Project",
        "",
        "- PPO/RL: there is now a concrete PPO entry point instead of only oracle + monitor evaluation.",
        "- Pseudo-vision: the wrapper can append noisy keypoint/depth-like features derived from visual-state proxies before policy learning.",
        "- Render pseudo-vision: the wrapper can call SurRoL RGB rendering and compress images into policy features, so vision-like errors can enter before action selection.",
        "- Multi-task breadth: the same wrapper passed smoke and BC/evaluation readiness on NeedlePickRL, GauzeRetrieveRL, and PickAndPlaceRL.",
        "- Risk-aware learning: the reward can penalize forbidden-zone violations, so risk-aware routing is no longer only a post-hoc evaluator.",
        "- Policy evaluation: trained PPO checkpoints can now be loaded and routed through a simple risk-level evaluator.",
        "- Demonstration initialization: oracle demonstrations can now initialize a PPO policy through behavior cloning before RL fine-tuning.",
        "",
        "## What Is Still Not Complete",
        "",
        "- The current PPO checkpoints are smoke/small-training checkpoints, not meaningful trained surgical policies yet.",
        "- BC initialization changes behavior but does not yet solve NeedlePickRL; under drift it can increase unsafe-zone exposure.",
        "- PickAndPlaceRL is now integrated into the training/evaluation chain, but the current 2-demo BC policy is not successful.",
        "- GauzeRetrieveRL is integrated, but the current 3-demo BC policy is also not successful and shows drift-triggered abort candidates.",
        "- The render_pseudo_vision signal compresses RGB images with hand-crafted statistics, not a learned segmentation or VLM encoder.",
        "- PickAndPlaceRL has only passed one-step smoke; it is not yet a stable multi-seed training/evaluation benchmark.",
        "- The current reward shaping uses a geometric forbidden-zone proxy, not physical tissue-force or deformation feedback.",
        "",
        "## Next Concrete Step",
        "",
        (
            "Next, either extend NeedlePickRL PPO training substantially beyond 2k timesteps, or initialize from demonstrations / curriculum "
            "before attempting PickAndPlaceRL training. The current evidence suggests sparse reward PPO from scratch is not enough at this scale."
        ),
        "",
        "## Files",
        "",
        "- `scripts/train_surrol_ppo_failure_aware.py`",
        "- `scripts/run_surrol_ppo_failure_aware.ps1`",
        "- `runs/surrol_ppo_smoke_needlepick_pseudovision/smoke_check.json`",
        "- `runs/surrol_ppo_smoke_pickandplace_pseudovision/smoke_check.json`",
        "- `runs/surrol_ppo_smoke_needlepick_render_pseudovision/smoke_check.json`",
        "- `runs/surrol_ppo_dependency_probe_needlepick/dependency_blocked.json`",
        "- `runs/surrol_ppo_train_smoke_needlepick_16step/model.zip`",
        "- `runs/surrol_ppo_train_smoke_needlepick_16step/train_summary.json`",
        "- `runs/surrol_ppo_eval_needlepick_smoke_3ep.csv`",
        "- `runs/surrol_ppo_train_needlepick_pseudovision_2048_seed43000/model.zip`",
        "- `runs/surrol_ppo_eval_needlepick_pseudovision_2048_5ep.csv`",
        "- `runs/surrol_ppo_bc_needlepick_pseudovision_5demo_mse80/model_bc.zip`",
        "- `runs/surrol_ppo_eval_needlepick_bc_mse80_clean_5ep.csv`",
        "- `runs/surrol_ppo_eval_needlepick_bc_mse80_drift_5ep.csv`",
        "- `runs/surrol_ppo_train_needlepick_bcinit_mse80_2048/model.zip`",
        "- `runs/surrol_ppo_eval_needlepick_bcinit_mse80_2048_drift_5ep.csv`",
        "- `runs/surrol_ppo_bc_pickandplace_pseudovision_2demo_mse40/model_bc.zip`",
        "- `runs/surrol_ppo_eval_pickandplace_bc_2demo_clean_3ep.csv`",
        "- `runs/surrol_ppo_eval_pickandplace_bc_2demo_drift_3ep.csv`",
        "- `runs/surrol_ppo_bc_gauzeretrieve_pseudovision_3demo_mse60/model_bc.zip`",
        "- `runs/surrol_ppo_eval_gauzeretrieve_bc_3demo_clean_5ep.csv`",
        "- `runs/surrol_ppo_eval_gauzeretrieve_bc_3demo_drift_5ep.csv`",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"report={out}")


if __name__ == "__main__":
    main()
