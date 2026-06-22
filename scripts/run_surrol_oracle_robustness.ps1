param(
    [string]$SurrolRoot = "/mnt/e/RL_projects/SurRoL_clean_SR-VPPV",
    [string]$EnvPath = "/mnt/e/RL_projects/surrol_py38_env",
    [string]$MambaRoot = "/mnt/e/RL_projects/micromamba",
    [string]$Out = "/mnt/e/RL_projects/constraint_surgical_rl/runs/surrol_oracle_robustness_pilot.csv",
    [string]$Report = "/mnt/e/RL_projects/constraint_surgical_rl/reports/surrol_oracle_robustness_pilot_zh.md",
    [int]$Seeds = 3,
    [int]$Episodes = 1,
    [int]$MaxSteps = 25,
    [string]$Tasks = "ECMReach,NeedlePick,BiPegTransfer",
    [string]$Conditions = "none,action_noise,action_dropout"
)

$ErrorActionPreference = "Stop"

$workdir = "$SurrolRoot/Benchmark/state_based"
$micromamba = "$MambaRoot/bin/micromamba"

$experimentScript = @'
import argparse
import csv
import importlib
import math
from pathlib import Path

import numpy as np

TASKS = {
    "ECMReach": ("surrol.tasks.ecm_reach", "ECMReach"),
    "NeedleReach": ("surrol.tasks.needle_reach_org", "NeedleReach"),
    "NeedlePick": ("surrol.tasks.needle_pick_org", "NeedlePick"),
    "GauzeRetrieve": ("surrol.tasks.gauze_retrieve_org", "GauzeRetrieve"),
    "BiPegTransfer": ("surrol.tasks.peg_transfer_bimanual_org", "BiPegTransfer"),
    "NeedleRegrasp": ("surrol.tasks.needle_regrasp_bimanual_org", "NeedleRegrasp"),
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--conditions", required=True)
    parser.add_argument("--seeds", type=int, required=True)
    parser.add_argument("--episodes", type=int, required=True)
    parser.add_argument("--max-steps", type=int, required=True)
    return parser.parse_args()


def load_env_class(task_name):
    module_name, class_name = TASKS[task_name]
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def distance(obs):
    return float(np.linalg.norm(np.asarray(obs["achieved_goal"]) - np.asarray(obs["desired_goal"])))


def perturb_action(action, condition, rng, step_idx):
    base = np.asarray(action, dtype=np.float64)
    proposed = base.copy()
    if condition == "none":
        pass
    elif condition == "action_noise":
        proposed = proposed + rng.normal(0.0, 0.25, size=proposed.shape)
    elif condition == "action_dropout":
        if rng.random() < 0.30:
            proposed = np.zeros_like(proposed)
    elif condition == "execution_slip":
        if step_idx % 4 == 0:
            proposed = -0.35 * proposed + rng.normal(0.0, 0.10, size=proposed.shape)
    else:
        raise ValueError(f"Unknown condition: {condition}")
    clipped = np.clip(proposed, -1.0, 1.0)
    clip_event = float(np.max(np.abs(proposed - clipped)) > 1e-8)
    action_deviation = float(np.linalg.norm(clipped - base))
    return clipped.astype(np.float32), clip_event, action_deviation


def run_episode(env, task, condition, seed, episode, max_steps):
    rng = np.random.default_rng(seed * 1009 + episode * 97 + sum(ord(c) for c in condition))
    np.random.seed(seed)
    env.seed(seed)
    obs = env.reset()
    initial_distance = distance(obs)
    prev_distance = initial_distance
    min_distance = initial_distance
    total_reward = 0.0
    risk_events = 0
    stalled_steps = 0
    regress_steps = 0
    action_clip_events = 0.0
    action_deviation_sum = 0.0
    success = 0.0
    final_info = {}

    for step_idx in range(max_steps):
        oracle_action = env.get_oracle_action(obs) if hasattr(env, "get_oracle_action") else env.action_space.sample()
        action, clip_event, action_deviation = perturb_action(oracle_action, condition, rng, step_idx)
        obs, reward, done, info = env.step(action)
        current_distance = distance(obs)
        progress = prev_distance - current_distance
        min_distance = min(min_distance, current_distance)
        total_reward += float(reward)
        final_info = info

        is_stalled = abs(progress) < 1e-4
        is_regressing = progress < -1e-4
        is_farther_than_start = current_distance > initial_distance + 1e-4
        risk_event = is_regressing or is_farther_than_start or bool(clip_event)

        risk_events += int(risk_event)
        stalled_steps += int(is_stalled)
        regress_steps += int(is_regressing)
        action_clip_events += clip_event
        action_deviation_sum += action_deviation

        success = float(info.get("is_success", 0.0))
        prev_distance = current_distance
        if success >= 1.0:
            return {
                "task": task,
                "condition": condition,
                "seed": seed,
                "episode": episode,
                "success": success,
                "steps": step_idx + 1,
                "return": total_reward,
                "initial_distance": initial_distance,
                "final_distance": current_distance,
                "min_distance": min_distance,
                "distance_reduction": initial_distance - current_distance,
                "risk_event_rate": risk_events / float(step_idx + 1),
                "stalled_rate": stalled_steps / float(step_idx + 1),
                "regress_rate": regress_steps / float(step_idx + 1),
                "action_clip_rate": action_clip_events / float(step_idx + 1),
                "mean_action_deviation": action_deviation_sum / float(step_idx + 1),
                "final_info_success": float(final_info.get("is_success", 0.0)),
            }

    return {
        "task": task,
        "condition": condition,
        "seed": seed,
        "episode": episode,
        "success": success,
        "steps": max_steps,
        "return": total_reward,
        "initial_distance": initial_distance,
        "final_distance": prev_distance,
        "min_distance": min_distance,
        "distance_reduction": initial_distance - prev_distance,
        "risk_event_rate": risk_events / float(max_steps),
        "stalled_rate": stalled_steps / float(max_steps),
        "regress_rate": regress_steps / float(max_steps),
        "action_clip_rate": action_clip_events / float(max_steps),
        "mean_action_deviation": action_deviation_sum / float(max_steps),
        "final_info_success": float(final_info.get("is_success", 0.0)),
    }


def mean(rows, key):
    return float(np.mean([float(row[key]) for row in rows])) if rows else math.nan


def std(rows, key):
    return float(np.std([float(row[key]) for row in rows], ddof=0)) if rows else math.nan


def fmt(value):
    return f"{value:.3f}"


def write_report(rows, report_path, tasks, conditions, seeds, episodes, max_steps):
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# SurRoL Oracle Robustness Pilot",
        "",
        "## Takeaway",
        "",
        (
            "This is the first formal SurRoL simulation experiment for this project: "
            "we run multi-seed scripted-oracle rollouts across surgical task entry points, "
            "then inject action noise/dropout to measure success, distance convergence, and risk events. "
            "The result is a baseline for later risk-monitor and recovery-policy experiments, not a trained-policy claim."
        ),
        "",
        "## Setup",
        "",
        f"- Tasks: {', '.join(tasks)}",
        f"- Conditions: {', '.join(conditions)}",
        f"- Seeds: {seeds}",
        f"- Episodes per seed-condition-task: {episodes}",
        f"- Max steps per episode: {max_steps}",
        "- Policy: SurRoL scripted oracle, with optional action perturbation.",
        "- Risk proxy: distance regression, moving farther than initial state, or action clipping.",
        "",
        "## Summary Table",
        "",
        "| Task | Condition | Episodes | Success | Success Std | Final Dist | Distance Reduction | Risk Event | Regress | Stalled | Action Deviation |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for task in tasks:
        for condition in conditions:
            selected = [row for row in rows if row["task"] == task and row["condition"] == condition]
            lines.append(
                f"| {task} | {condition} | {len(selected)} | {fmt(mean(selected, 'success'))} | "
                f"{fmt(std(selected, 'success'))} | {fmt(mean(selected, 'final_distance'))} | "
                f"{fmt(mean(selected, 'distance_reduction'))} | {fmt(mean(selected, 'risk_event_rate'))} | "
                f"{fmt(mean(selected, 'regress_rate'))} | {fmt(mean(selected, 'stalled_rate'))} | "
                f"{fmt(mean(selected, 'mean_action_deviation'))} |"
            )

    lines.extend([
        "",
        "## What This Shows",
        "",
        "- The run estimates basic task reachability under SurRoL scripted oracle control.",
        "- The perturbation conditions show whether action corruption creates measurable risk events.",
        "- If a task is weak even under `none`, it is likely a task/environment difficulty rather than a monitor issue.",
        "- If perturbations raise risk but still allow goal progress, that task is a good recovery/monitor benchmark.",
        "",
        "## What This Does Not Prove",
        "",
        "- This is not a learned-policy result.",
        "- The current risk proxy is heuristic and not yet a calibrated uncertainty model.",
        "- The seed count is still small, so this should be treated as a pilot.",
        "",
        "## Next Step",
        "",
        "Connect the same CSV interface to the existing failure-aware monitor and compare oracle-only, perturbed-oracle, and monitor-corrected rollouts before starting policy training.",
        "",
    ])
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    args = parse_args()
    tasks = [item.strip() for item in args.tasks.split(",") if item.strip()]
    conditions = [item.strip() for item in args.conditions.split(",") if item.strip()]
    out_path = Path(args.out)
    report_path = Path(args.report)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for task in tasks:
        print(f"TASK {task}", flush=True)
        env_cls = load_env_class(task)
        env = env_cls(render_mode=None)
        try:
            for condition in conditions:
                print(f"  condition={condition}", flush=True)
                for seed_idx in range(args.seeds):
                    seed = 42000 + seed_idx
                    for episode in range(args.episodes):
                        row = run_episode(env, task, condition, seed, episode, args.max_steps)
                        rows.append(row)
                        print(
                            "    seed", seed,
                            "episode", episode,
                            "success", row["success"],
                            "final_distance", f"{row['final_distance']:.4f}",
                            "risk", f"{row['risk_event_rate']:.3f}",
                            flush=True,
                        )
        finally:
            if hasattr(env, "close"):
                env.close()

    fieldnames = list(rows[0].keys())
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    write_report(rows, report_path, tasks, conditions, args.seeds, args.episodes, args.max_steps)
    print(f"csv={out_path}")
    print(f"report={report_path}")


if __name__ == "__main__":
    main()
'@

$experimentScript | wsl --cd $workdir $micromamba run -p $EnvPath python - `
    --out $Out `
    --report $Report `
    --tasks $Tasks `
    --conditions $Conditions `
    --seeds $Seeds `
    --episodes $Episodes `
    --max-steps $MaxSteps
