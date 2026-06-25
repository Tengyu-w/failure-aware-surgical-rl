param(
    [string]$SurrolRoot = "external/SurRoL_clean_SR-VPPV",
    [string]$EnvPath = "external/surrol_py38_env",
    [string]$MambaRoot = "external/micromamba",
    [string]$Out = "runs/surrol_needlepick_phase_diagnostics.csv",
    [string]$SummaryOut = "runs/surrol_needlepick_phase_diagnostics_summary.csv",
    [int]$MaxSteps = 200,
    [int]$RecoverySteps = 32,
    [string]$Failures = "action_dropout,execution_slip",
    [string]$Seeds = "43001,43002,43004"
)

$ErrorActionPreference = "Stop"

$workdir = "$SurrolRoot/Benchmark/state_based"
$micromamba = "$MambaRoot/bin/micromamba"

$diagnosticScript = @'
import argparse
import csv
from pathlib import Path

import numpy as np
import pybullet as p

from surrol.tasks.needle_pick_org import NeedlePick
from surrol.utils.pybullet_utils import get_link_pose


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--summary-out", required=True)
    parser.add_argument("--failures", required=True)
    parser.add_argument("--seeds", required=True)
    parser.add_argument("--max-steps", type=int, required=True)
    parser.add_argument("--recovery-steps", type=int, required=True)
    return parser.parse_args()


def goal_distance(obs):
    return float(np.linalg.norm(np.asarray(obs["achieved_goal"]) - np.asarray(obs["desired_goal"])))


def perturb_action(action, failure, rng, step_idx):
    base = np.asarray(action, dtype=np.float64)
    proposed = base.copy()
    if failure == "action_dropout":
        if rng.random() < 0.30:
            proposed = np.zeros_like(proposed)
    elif failure == "execution_slip":
        if step_idx % 4 == 0:
            proposed = -0.35 * proposed + rng.normal(0.0, 0.10, size=proposed.shape)
    elif failure == "action_noise":
        proposed = proposed + rng.normal(0.0, 0.25, size=proposed.shape)
    else:
        raise ValueError(f"Unknown failure: {failure}")
    clipped = np.clip(proposed, -1.0, 1.0)
    return clipped.astype(np.float32), float(np.linalg.norm(clipped - base)), float(np.max(np.abs(proposed - clipped)) > 1e-8)


def risk_event(progress, current_distance, initial_distance, action_deviation, clip_event, stalled_count):
    return (
        progress < -1e-4
        or current_distance > initial_distance + 1e-4
        or action_deviation > 0.35
        or clip_event > 0.0
        or stalled_count >= 5
    )


def active_waypoint(env):
    for idx, waypoint in enumerate(getattr(env, "_waypoints", [])):
        if waypoint is not None:
            return idx
    return -1


def contact_counts(env):
    psm = env.psm1
    points_1 = p.getContactPoints(bodyA=psm.body, linkIndexA=6)
    points_2 = p.getContactPoints(bodyA=psm.body, linkIndexA=7)
    rigid = set(env.obj_ids.get("rigid", []))
    ids_1 = [point[2] for point in points_1 if point[2] in rigid]
    ids_2 = [point[2] for point in points_2 if point[2] in rigid]
    both = set(ids_1) & set(ids_2)
    return len(ids_1), len(ids_2), len(both)


def object_metrics(env, obs):
    object_pos, _ = get_link_pose(env.obj_id, -1)
    waypoint_pos, _ = get_link_pose(env.obj_id, env.obj_link1)
    tip_pos, _ = get_link_pose(env.psm1.body, env.psm1.TIP_LINK_INDEX)
    return {
        "object_goal_distance": float(np.linalg.norm(np.asarray(object_pos) - np.asarray(obs["desired_goal"]))),
        "waypoint_goal_distance": float(np.linalg.norm(np.asarray(waypoint_pos) - np.asarray(obs["desired_goal"]))),
        "tip_waypoint_distance": float(np.linalg.norm(np.asarray(tip_pos) - np.asarray(waypoint_pos))),
        "object_z": float(object_pos[2]),
        "waypoint_z": float(waypoint_pos[2]),
        "tip_z": float(tip_pos[2]),
    }


def run_episode(env, failure, seed, max_steps, recovery_steps):
    rng = np.random.default_rng(seed * 1009 + sum(ord(c) for c in failure + "monitor_corrected"))
    np.random.seed(seed)
    env.seed(seed)
    obs = env.reset()
    initial_distance = goal_distance(obs)
    prev_distance = initial_distance
    recovery_remaining = 0
    stalled_count = 0
    rows = []
    success = 0.0

    for step_idx in range(max_steps):
        oracle_action = env.get_oracle_action(obs)
        action_deviation = 0.0
        clip_event = 0.0
        override = False

        if recovery_remaining > 0:
            action = oracle_action
            recovery_remaining -= 1
            override = True
        else:
            action, action_deviation, clip_event = perturb_action(oracle_action, failure, rng, step_idx)

        obs, reward, done, info = env.step(action)
        current_distance = goal_distance(obs)
        progress = prev_distance - current_distance
        stalled_count = stalled_count + 1 if abs(progress) < 1e-4 else 0
        trigger = False
        if recovery_remaining == 0 and risk_event(
            progress, current_distance, initial_distance, action_deviation, clip_event, stalled_count
        ):
            recovery_remaining = recovery_steps
            trigger = True

        c1, c2, cboth = contact_counts(env)
        metrics = object_metrics(env, obs)
        success = float(info.get("is_success", 0.0))
        rows.append({
            "failure": failure,
            "seed": seed,
            "step": step_idx,
            "success": success,
            "distance": current_distance,
            "progress": progress,
            "active_waypoint": active_waypoint(env),
            "activated": int(getattr(env, "_activated", -1)),
            "has_constraint": float(getattr(env, "_contact_constraint", None) is not None),
            "contact_left": c1,
            "contact_right": c2,
            "contact_both": cboth,
            "monitor_trigger": float(trigger),
            "recovery_override": float(override),
            "recovery_remaining": recovery_remaining,
            "action_deviation": action_deviation,
            "clip_event": clip_event,
            "stalled_count": stalled_count,
            **metrics,
        })
        prev_distance = current_distance
        if success >= 1.0:
            break
    return rows


def summarize(rows):
    grouped = {}
    for row in rows:
        grouped.setdefault((row["failure"], row["seed"]), []).append(row)
    out = []
    for (failure, seed), seq in sorted(grouped.items()):
        success = max(float(row["success"]) for row in seq)
        min_distance = min(float(row["distance"]) for row in seq)
        final = float(seq[-1]["distance"])
        first_activation = next((int(row["step"]) for row in seq if int(row["activated"]) >= 0), -1)
        first_constraint = next((int(row["step"]) for row in seq if float(row["has_constraint"]) > 0), -1)
        first_waypoint3 = next((int(row["step"]) for row in seq if int(row["active_waypoint"]) == 3), -1)
        out.append({
            "failure": failure,
            "seed": seed,
            "success": success,
            "steps": len(seq),
            "final_distance": final,
            "min_distance": min_distance,
            "first_activation_step": first_activation,
            "first_constraint_step": first_constraint,
            "first_lift_waypoint_step": first_waypoint3,
            "trigger_count": sum(float(row["monitor_trigger"]) for row in seq),
            "override_steps": sum(float(row["recovery_override"]) for row in seq),
            "final_active_waypoint": int(seq[-1]["active_waypoint"]),
            "final_activated": int(seq[-1]["activated"]),
            "final_has_constraint": float(seq[-1]["has_constraint"]),
            "final_object_goal_distance": float(seq[-1]["object_goal_distance"]),
            "final_tip_waypoint_distance": float(seq[-1]["tip_waypoint_distance"]),
        })
    return out


def main():
    args = parse_args()
    failures = [item.strip() for item in args.failures.split(",") if item.strip()]
    seeds = [int(item.strip()) for item in args.seeds.split(",") if item.strip()]
    out_path = Path(args.out)
    summary_path = Path(args.summary_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    all_rows = []

    env = NeedlePick(render_mode=None)
    try:
        for failure in failures:
            print(f"FAILURE {failure}", flush=True)
            for seed in seeds:
                rows = run_episode(env, failure, seed, args.max_steps, args.recovery_steps)
                all_rows.extend(rows)
                print(
                    "  seed", seed,
                    "success", max(float(row["success"]) for row in rows),
                    "final", f"{float(rows[-1]['distance']):.4f}",
                    "min", f"{min(float(row['distance']) for row in rows):.4f}",
                    "active_wp", rows[-1]["active_waypoint"],
                    "activated", rows[-1]["activated"],
                    "constraint", rows[-1]["has_constraint"],
                    flush=True,
                )
    finally:
        if hasattr(env, "close"):
            env.close()

    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)

    summary_rows = summarize(all_rows)
    with summary_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"diagnostics_csv={out_path}")
    print(f"summary_csv={summary_path}")


if __name__ == "__main__":
    main()
'@

$diagnosticScript | wsl --cd $workdir $micromamba run -p $EnvPath python - `
    --out $Out `
    --summary-out $SummaryOut `
    --failures $Failures `
    --seeds $Seeds `
    --max-steps $MaxSteps `
    --recovery-steps $RecoverySteps
