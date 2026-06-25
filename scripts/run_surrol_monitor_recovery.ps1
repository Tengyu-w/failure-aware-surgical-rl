param(
    [string]$SurrolRoot = "external/SurRoL_clean_SR-VPPV",
    [string]$EnvPath = "external/surrol_py38_env",
    [string]$MambaRoot = "external/micromamba",
    [string]$EpisodeOut = "runs/surrol_needlepick_monitor_recovery.csv",
    [string]$StepOut = "runs/surrol_needlepick_monitor_recovery_steps.csv",
    [string]$Report = "reports/surrol_needlepick_monitor_recovery_zh.md",
    [string]$Task = "NeedlePick",
    [int]$Seeds = 3,
    [int]$Episodes = 1,
    [int]$MaxSteps = 200,
    [int]$RecoverySteps = 8,
    [string]$TriggerMode = "goalaware",
    [string]$RecoveryPolicy = "oracle_override",
    [string]$Failures = "none,action_noise,action_dropout,execution_slip",
    [double]$PerceptionBiasScale = 1.0,
    [double]$PerceptionJitterStd = 0.006,
    [double]$DepthScaleError = 0.12,
    [double]$NearTargetDriftScale = 1.0,
    [double]$NearTargetThreshold = 0.12,
    [double]$PerceptionReviewThreshold = 0.004,
    [string]$DangerZone = "none",
    [double]$DangerRadius = 0.035,
    [double]$DangerWarningRadius = 0.060
)

$ErrorActionPreference = "Stop"

$workdir = "$SurrolRoot/Benchmark/state_based"
$micromamba = "$MambaRoot/bin/micromamba"

$experimentScript = @'
import argparse
import csv
from pathlib import Path

import numpy as np

from surrol.tasks.gauze_retrieve_org import GauzeRetrieve
from surrol.tasks.needle_pick_org import NeedlePick
from surrol.tasks.needle_reach_org import NeedleReach


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode-out", required=True)
    parser.add_argument("--step-out", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--task", choices=["NeedlePick", "GauzeRetrieve", "NeedleReach"], required=True)
    parser.add_argument("--failures", required=True)
    parser.add_argument("--seeds", type=int, required=True)
    parser.add_argument("--episodes", type=int, required=True)
    parser.add_argument("--max-steps", type=int, required=True)
    parser.add_argument("--recovery-steps", type=int, required=True)
    parser.add_argument("--trigger-mode", choices=["coarse", "goalaware"], required=True)
    parser.add_argument("--recovery-policy", choices=["oracle_override", "contact_replan", "phase_replan", "observable_phase_replan", "review_reestimate", "risk_aware_abort"], required=True)
    parser.add_argument("--perception-bias-scale", type=float, default=1.0)
    parser.add_argument("--perception-jitter-std", type=float, default=0.006)
    parser.add_argument("--depth-scale-error", type=float, default=0.12)
    parser.add_argument("--near-target-drift-scale", type=float, default=1.0)
    parser.add_argument("--near-target-threshold", type=float, default=0.12)
    parser.add_argument("--perception-review-threshold", type=float, default=0.004)
    parser.add_argument("--danger-zone", default="none")
    parser.add_argument("--danger-radius", type=float, default=0.035)
    parser.add_argument("--danger-warning-radius", type=float, default=0.060)
    return parser.parse_args()


TASKS = {
    "NeedlePick": NeedlePick,
    "GauzeRetrieve": GauzeRetrieve,
    "NeedleReach": NeedleReach,
}


def goal_distance(obs):
    return float(np.linalg.norm(np.asarray(obs["achieved_goal"]) - np.asarray(obs["desired_goal"])))


def resolve_danger_center(obs, danger_zone):
    if danger_zone in {"", "none", None}:
        return None
    if danger_zone == "goal_drift_proxy":
        goal = np.asarray(obs["desired_goal"], dtype=np.float64)
        return goal + np.array([0.045, -0.025, 0.010], dtype=np.float64)
    parts = [p.strip() for p in str(danger_zone).split(",")]
    if len(parts) != 3:
        raise ValueError(f"DangerZone must be none, goal_drift_proxy, or x,y,z. Got: {danger_zone}")
    return np.array([float(p) for p in parts], dtype=np.float64)


def corrupt_observation(obs, failure, rng, step_idx, perception_bias_scale, perception_jitter_std, depth_scale_error):
    corrupted = {
        key: np.asarray(value).copy() if isinstance(value, np.ndarray) else value
        for key, value in obs.items()
    }
    perception_error_norm = 0.0
    if failure == "perception_bias":
        bias = perception_bias_scale * np.array([0.012, -0.008, 0.006], dtype=np.float64)
        corrupted["observation"][:3] = corrupted["observation"][:3] + bias
        perception_error_norm = float(np.linalg.norm(bias))
    elif failure == "perception_jitter":
        bias = rng.normal(0.0, perception_jitter_std, size=3)
        corrupted["observation"][:3] = corrupted["observation"][:3] + bias
        perception_error_norm = float(np.linalg.norm(bias))
    elif failure == "depth_scale_error":
        before = float(corrupted["observation"][2])
        corrupted["observation"][2] = corrupted["observation"][2] * (1.0 + depth_scale_error)
        perception_error_norm = abs(float(corrupted["observation"][2]) - before)
    return corrupted, perception_error_norm


def perturb_action(action, failure, rng, step_idx, current_distance=None, near_target_drift_scale=1.0, near_target_threshold=0.12):
    base = np.asarray(action, dtype=np.float64)
    proposed = base.copy()
    silent_fault = False
    if failure == "none":
        pass
    elif failure == "action_noise":
        proposed = proposed + rng.normal(0.0, 0.25, size=proposed.shape)
    elif failure == "action_dropout":
        if rng.random() < 0.30:
            proposed = np.zeros_like(proposed)
    elif failure == "action_freeze":
        if step_idx < 200:
            proposed = np.zeros_like(proposed)
    elif failure == "execution_slip":
        if step_idx % 4 == 0:
            proposed = -0.35 * proposed + rng.normal(0.0, 0.10, size=proposed.shape)
    elif failure == "near_target_drift":
        if current_distance is not None and current_distance < near_target_threshold:
            drift = np.zeros_like(proposed)
            drift[:3] = near_target_drift_scale * np.array([0.45, -0.25, 0.10])[: min(3, proposed.shape[0])]
            proposed = proposed + drift
    elif failure == "jaw_stuck_open":
        if step_idx < 70 and proposed.shape[0] >= 5 and base[-1] < 0:
            proposed[-1] = 0.5
            silent_fault = True
    elif failure in {"perception_bias", "perception_jitter", "depth_scale_error"}:
        pass
    else:
        raise ValueError(f"Unknown failure: {failure}")
    clipped = np.clip(proposed, -1.0, 1.0)
    action_deviation = 0.0 if silent_fault else float(np.linalg.norm(clipped - base))
    return clipped.astype(np.float32), action_deviation, float(np.max(np.abs(proposed - clipped)) > 1e-8)


def risk_event_for_mode(progress, current_distance, initial_distance, action_deviation, clip_event, stalled_count, mode):
    if mode == "coarse":
        regressed = progress < -1e-4
        farther_than_start = current_distance > initial_distance + 1e-4
        sustained_stall = stalled_count >= 5
    elif mode == "goalaware":
        regressed = progress < -0.01
        farther_than_start = current_distance > initial_distance + 0.01
        sustained_stall = False
    else:
        raise ValueError(f"Unknown trigger mode: {mode}")
    action_anomaly = action_deviation > 0.35 or clip_event > 0.0
    return regressed or farther_than_start or action_anomaly or sustained_stall


def should_trigger(progress, current_distance, initial_distance, action_deviation, clip_event, stalled_count, mode):
    return risk_event_for_mode(progress, current_distance, initial_distance, action_deviation, clip_event, stalled_count, mode)


def all_waypoints_consumed(env):
    return all(waypoint is None for waypoint in getattr(env, "_waypoints", []))


def contact_replan_needed(env, success):
    return success < 1.0 and all_waypoints_consumed(env) and int(getattr(env, "_activated", -1)) < 0


def active_waypoint(env):
    for idx, waypoint in enumerate(getattr(env, "_waypoints", [])):
        if waypoint is not None:
            return idx
    return -1


def phase_replan(env, success):
    if success >= 1.0:
        return None

    activated = int(getattr(env, "_activated", -1))
    has_constraint = getattr(env, "_contact_constraint", None) is not None
    waypoint_idx = active_waypoint(env)

    if activated >= 0 or has_constraint:
        if waypoint_idx < 0:
            env._sample_goal_callback()
            for idx in range(max(0, len(env._waypoints) - 1)):
                env._waypoints[idx] = None
            return "lift_retry"
        return None

    if waypoint_idx < 0:
        env._sample_goal_callback()
        return "grasp_retry"

    return None


def observable_phase_replan(env, success, step_idx, current_distance, initial_distance, min_distance, stalled_count, close_command_count):
    if success >= 1.0:
        return None
    if step_idx < 30:
        return None
    if close_command_count < 4:
        return None

    still_far = current_distance > 0.08 or current_distance > initial_distance * 0.55
    barely_improved = (initial_distance - min_distance) < 0.035
    stalled = stalled_count >= 8
    if still_far and (barely_improved or stalled):
        env._sample_goal_callback()
        return "observable_grasp_retry"
    return None


def run_episode(
    env, task, failure, controller, seed, episode, max_steps, recovery_steps, trigger_mode, recovery_policy,
    perception_bias_scale, perception_jitter_std, depth_scale_error, near_target_drift_scale, near_target_threshold,
    perception_review_threshold, danger_zone, danger_radius, danger_warning_radius
):
    rng = np.random.default_rng(seed * 1009 + episode * 97 + sum(ord(c) for c in failure + controller))
    np.random.seed(seed)
    env.seed(seed)
    obs = env.reset()
    danger_center = resolve_danger_center(obs, danger_zone)
    initial_distance = goal_distance(obs)
    prev_distance = initial_distance
    min_distance = initial_distance
    total_reward = 0.0
    risk_events = 0
    monitor_triggers = 0
    recovery_override_steps = 0
    recovery_replans = 0
    recovery_phase_replans = 0
    last_recovery_phase = ""
    stalled_count = 0
    close_command_count = 0
    observable_replan_signal = 0.0
    recovery_remaining = 0
    step_rows = []
    success = 0.0
    perception_error_norm = 0.0
    visual_reestimate_active = False
    visual_reestimate_triggers = 0
    unsafe_warning_events = 0
    unsafe_abort = 0
    min_danger_distance = float("nan")

    for step_idx in range(max_steps):
        if controller == "monitor_corrected" and recovery_policy == "contact_replan":
            if contact_replan_needed(env, success):
                env._sample_goal_callback()
                recovery_remaining = recovery_steps
                recovery_replans += 1
                monitor_triggers += 1
                last_recovery_phase = "contact_replan"
        elif controller == "monitor_corrected" and recovery_policy == "phase_replan":
            phase = phase_replan(env, success)
            if phase is not None:
                recovery_remaining = recovery_steps
                recovery_replans += 1
                recovery_phase_replans += 1
                monitor_triggers += 1
                last_recovery_phase = phase
        elif controller == "monitor_corrected" and recovery_policy == "observable_phase_replan" and recovery_remaining == 0:
            phase = observable_phase_replan(
                env, success, step_idx, prev_distance, initial_distance, min_distance, stalled_count, close_command_count
            )
            if phase is not None:
                recovery_remaining = recovery_steps
                recovery_replans += 1
                recovery_phase_replans += 1
                monitor_triggers += 1
                observable_replan_signal = 1.0
                last_recovery_phase = phase

        obs_for_policy = obs
        perception_error_norm = 0.0
        visual_reestimate_trigger = False
        if controller in {"perturbed", "monitor_corrected"} and recovery_remaining == 0 and not visual_reestimate_active:
            obs_for_policy, perception_error_norm = corrupt_observation(
                obs, failure, rng, step_idx, perception_bias_scale, perception_jitter_std, depth_scale_error
            )
            if (
                controller == "monitor_corrected"
                and recovery_policy == "review_reestimate"
                and failure in {"perception_bias", "perception_jitter", "depth_scale_error"}
                and perception_error_norm >= perception_review_threshold
            ):
                visual_reestimate_active = True
                visual_reestimate_trigger = True
                visual_reestimate_triggers += 1
                monitor_triggers += 1
                recovery_replans += 1
                last_recovery_phase = "visual_state_reestimate"
                obs_for_policy = obs

        oracle_action = env.get_oracle_action(obs_for_policy)
        if np.asarray(oracle_action).shape[0] >= 5 and float(np.asarray(oracle_action)[-1]) < 0:
            close_command_count += 1
        action_deviation = 0.0
        clip_event = 0.0
        trigger_before = recovery_remaining > 0
        override = False

        if controller == "clean":
            action = oracle_action
        elif controller == "perturbed":
            action, action_deviation, clip_event = perturb_action(
                oracle_action, failure, rng, step_idx, prev_distance, near_target_drift_scale, near_target_threshold
            )
        elif controller == "monitor_corrected":
            if recovery_remaining > 0:
                action = oracle_action
                if failure == "jaw_stuck_open" and step_idx < 70:
                    action, _, _ = perturb_action(
                        action, failure, rng, step_idx, prev_distance, near_target_drift_scale, near_target_threshold
                    )
                recovery_remaining -= 1
                override = True
                recovery_override_steps += 1
            else:
                action, action_deviation, clip_event = perturb_action(
                    oracle_action, failure, rng, step_idx, prev_distance, near_target_drift_scale, near_target_threshold
                )
        else:
            raise ValueError(f"Unknown controller: {controller}")

        obs, reward, done, info = env.step(action)
        current_distance = goal_distance(obs)
        tool_pos = np.asarray(obs["observation"][:3], dtype=np.float64)
        if danger_center is None:
            danger_distance = float("nan")
            unsafe_warning = False
            unsafe_violation = False
        else:
            danger_distance = float(np.linalg.norm(tool_pos - danger_center))
            min_danger_distance = danger_distance if np.isnan(min_danger_distance) else min(min_danger_distance, danger_distance)
            unsafe_warning = danger_distance <= danger_warning_radius
            unsafe_violation = danger_distance <= danger_radius
        unsafe_warning_events += int(unsafe_warning)
        progress = prev_distance - current_distance
        total_reward += float(reward)
        min_distance = min(min_distance, current_distance)
        stalled_count = stalled_count + 1 if abs(progress) < 1e-4 else 0

        risk_event = risk_event_for_mode(
            progress, current_distance, initial_distance, action_deviation, clip_event, stalled_count, trigger_mode
        )
        risk_events += int(risk_event)

        trigger_after = False
        if controller == "monitor_corrected" and recovery_remaining == 0 and not visual_reestimate_trigger:
            if should_trigger(
                progress, current_distance, initial_distance, action_deviation, clip_event, stalled_count, trigger_mode
            ):
                monitor_triggers += 1
                trigger_after = True
                if recovery_policy == "observable_phase_replan":
                    phase = observable_phase_replan(
                        env, success, step_idx, current_distance, initial_distance, min_distance, stalled_count, close_command_count
                    )
                    if phase is not None:
                        recovery_replans += 1
                        recovery_phase_replans += 1
                        observable_replan_signal = 1.0
                        last_recovery_phase = phase
                recovery_remaining = recovery_steps

        success = float(info.get("is_success", 0.0))
        if controller == "monitor_corrected" and recovery_policy == "risk_aware_abort" and unsafe_violation:
            unsafe_abort = 1
            monitor_triggers += 1
            trigger_after = True
            done = True
        step_rows.append({
            "failure": failure,
            "controller": controller,
            "trigger_mode": trigger_mode,
            "seed": seed,
            "episode": episode,
            "step": step_idx,
            "success": success,
            "distance": current_distance,
            "progress": progress,
            "reward": float(reward),
            "risk_event": float(risk_event),
            "monitor_trigger": float(trigger_after),
            "recovery_override": float(override),
            "recovery_replan": float(recovery_replans),
            "recovery_phase_replans": float(recovery_phase_replans),
            "recovery_phase": last_recovery_phase,
            "observable_replan_signal": observable_replan_signal,
            "visual_reestimate_trigger": float(visual_reestimate_trigger),
            "visual_reestimate_active": float(visual_reestimate_active),
            "close_command_count": close_command_count,
            "action_deviation": action_deviation,
            "clip_event": clip_event,
            "perception_error_norm": perception_error_norm,
            "stalled_count": stalled_count,
            "tool_x": float(tool_pos[0]),
            "tool_y": float(tool_pos[1]),
            "tool_z": float(tool_pos[2]),
            "danger_x": "" if danger_center is None else float(danger_center[0]),
            "danger_y": "" if danger_center is None else float(danger_center[1]),
            "danger_z": "" if danger_center is None else float(danger_center[2]),
            "danger_distance": danger_distance,
            "unsafe_warning": float(unsafe_warning),
            "unsafe_violation": float(unsafe_violation),
            "unsafe_abort": float(unsafe_abort),
        })
        observable_replan_signal = 0.0
        prev_distance = current_distance
        if success >= 1.0 or unsafe_abort:
            break

    episode_row = {
        "task": task,
        "failure": failure,
        "controller": controller,
        "trigger_mode": trigger_mode,
        "seed": seed,
        "episode": episode,
        "success": success,
        "steps": len(step_rows),
        "return": total_reward,
        "initial_distance": initial_distance,
        "final_distance": prev_distance,
        "min_distance": min_distance,
        "distance_reduction": initial_distance - prev_distance,
        "risk_event_rate": risk_events / float(len(step_rows)),
        "monitor_triggers": monitor_triggers,
        "recovery_replans": recovery_replans,
        "recovery_phase_replans": recovery_phase_replans,
        "recovery_override_rate": recovery_override_steps / float(len(step_rows)),
        "visual_reestimate_triggers": visual_reestimate_triggers,
        "unsafe_warning_events": unsafe_warning_events,
        "unsafe_abort": unsafe_abort,
        "min_danger_distance": min_danger_distance,
    }
    return episode_row, step_rows


def mean(rows, key):
    return float(np.mean([float(row[key]) for row in rows])) if rows else float("nan")


def fmt(value):
    return f"{value:.3f}"


def write_report(rows, report_path, task, failures, max_steps, recovery_steps, trigger_mode, recovery_policy):
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# SurRoL {task} Monitor Recovery",
        "",
        "## Takeaway",
        "",
        (
            f"This experiment tests whether a simple runtime monitor can supervise {task} under action, perception-state, "
            "or near-target drift corruptions. The monitor triggers on distance regression, moving farther than the initial state, "
            "action anomaly, clipping, or sustained stalls, then temporarily overrides the corrupted action with the clean scripted oracle."
        ),
        "",
        "## Setup",
        "",
        f"- Task: {task}",
        f"- Failures: {', '.join(failures)}",
        f"- Max steps: {max_steps}",
        f"- Recovery override window: {recovery_steps} steps",
        f"- Trigger mode: {trigger_mode}",
        f"- Recovery policy: {recovery_policy}",
        "- Controllers: clean, perturbed, monitor_corrected",
        "",
        "## Episode Summary",
        "",
        "| Failure | Controller | Episodes | Success | Final Distance | Distance Reduction | Risk Event | Monitor Triggers | Replans | Override Rate | Mean Steps |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    controllers = ["clean", "perturbed", "monitor_corrected"]
    for failure in failures:
        for controller in controllers:
            selected = [row for row in rows if row["failure"] == failure and row["controller"] == controller]
            if not selected:
                continue
            lines.append(
                f"| {failure} | {controller} | {len(selected)} | {fmt(mean(selected, 'success'))} | "
                f"{fmt(mean(selected, 'final_distance'))} | {fmt(mean(selected, 'distance_reduction'))} | "
                f"{fmt(mean(selected, 'risk_event_rate'))} | {fmt(mean(selected, 'monitor_triggers'))} | "
                f"{fmt(mean(selected, 'recovery_replans'))} | {fmt(mean(selected, 'recovery_override_rate'))} | "
                f"{fmt(mean(selected, 'steps'))} |"
            )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- If monitor_corrected improves success over perturbed, the risk trigger is doing useful control work.",
        "- If monitor_corrected only lowers final distance but not success, the recovery action is partially helpful but the case may need review or re-estimation rather than blind retry.",
        f"- If clean succeeds and perturbed fails, {task} is a valid failure-aware benchmark.",
        "",
    ])
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    args = parse_args()
    failures = [item.strip() for item in args.failures.split(",") if item.strip()]
    episode_out = Path(args.episode_out)
    step_out = Path(args.step_out)
    report = Path(args.report)
    episode_out.parent.mkdir(parents=True, exist_ok=True)
    step_out.parent.mkdir(parents=True, exist_ok=True)

    controllers = ["clean", "perturbed", "monitor_corrected"]
    episode_rows = []
    step_rows_all = []

    env = TASKS[args.task](render_mode=None)
    try:
        for failure in failures:
            print(f"FAILURE {failure}", flush=True)
            for controller in controllers:
                if failure == "none" and controller == "perturbed":
                    continue
                print(f"  controller={controller}", flush=True)
                for seed_idx in range(args.seeds):
                    seed = 43000 + seed_idx
                    for episode in range(args.episodes):
                        episode_row, step_rows = run_episode(
                            env, args.task, failure, controller, seed, episode, args.max_steps, args.recovery_steps, args.trigger_mode
                            , args.recovery_policy, args.perception_bias_scale, args.perception_jitter_std,
                            args.depth_scale_error, args.near_target_drift_scale, args.near_target_threshold,
                            args.perception_review_threshold, args.danger_zone, args.danger_radius, args.danger_warning_radius
                        )
                        episode_rows.append(episode_row)
                        step_rows_all.extend(step_rows)
                        print(
                            "    seed", seed,
                            "success", episode_row["success"],
                            "final_distance", f"{episode_row['final_distance']:.4f}",
                            "triggers", episode_row["monitor_triggers"],
                            "steps", episode_row["steps"],
                            flush=True,
                        )
    finally:
        if hasattr(env, "close"):
            env.close()

    with episode_out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(episode_rows[0].keys()))
        writer.writeheader()
        writer.writerows(episode_rows)

    with step_out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(step_rows_all[0].keys()))
        writer.writeheader()
        writer.writerows(step_rows_all)

    write_report(episode_rows, report, args.task, failures, args.max_steps, args.recovery_steps, args.trigger_mode, args.recovery_policy)
    print(f"episode_csv={episode_out}")
    print(f"step_csv={step_out}")
    print(f"report={report}")


if __name__ == "__main__":
    main()
'@

$experimentScript | wsl --cd $workdir $micromamba run -p $EnvPath python - `
    --episode-out $EpisodeOut `
    --step-out $StepOut `
    --report $Report `
    --task $Task `
    --failures $Failures `
    --seeds $Seeds `
    --episodes $Episodes `
    --max-steps $MaxSteps `
    --recovery-steps $RecoverySteps `
    --trigger-mode $TriggerMode `
    --recovery-policy $RecoveryPolicy `
    --perception-bias-scale $PerceptionBiasScale `
    --perception-jitter-std $PerceptionJitterStd `
    --depth-scale-error $DepthScaleError `
    --near-target-drift-scale $NearTargetDriftScale `
    --near-target-threshold $NearTargetThreshold `
    --perception-review-threshold $PerceptionReviewThreshold `
    --danger-zone $DangerZone `
    --danger-radius $DangerRadius `
    --danger-warning-radius $DangerWarningRadius
