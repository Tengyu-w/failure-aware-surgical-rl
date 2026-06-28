param(
    [string]$SurrolRoot = "E:\RL_projects\SurRoL_clean_SR-VPPV",
    [string]$EnvPath = "E:\RL_projects\surrol_py38_env",
    [string]$MambaRoot = "E:\RL_projects\micromamba",
    [string]$EpisodeOut = "runs/surrol_true_mixed_faults_smoke.csv",
    [string]$StepOut = "runs/surrol_true_mixed_faults_smoke_steps.csv",
    [string]$Tasks = "NeedlePick,GauzeRetrieve",
    [string]$FailureCombos = "perception_bias+depth_scale_error,perception_bias+near_target_drift,depth_scale_error+near_target_drift,perception_bias+depth_scale_error+near_target_drift",
    [int]$Seeds = 5,
    [int]$Episodes = 1,
    [int]$MaxSteps = 180,
    [int]$RecoverySteps = 16,
    [string]$TriggerMode = "goalaware",
    [double]$PerceptionBiasScale = 1.0,
    [double]$DepthScaleError = 0.12,
    [double]$NearTargetDriftScale = 1.0,
    [double]$NearTargetThreshold = 0.12,
    [double]$PerceptionReviewThreshold = 0.004
)

$ErrorActionPreference = "Stop"

function Convert-ToWslPath {
    param([string]$PathValue)
    $full = [System.IO.Path]::GetFullPath($PathValue)
    $drive = $full.Substring(0, 1).ToLowerInvariant()
    $rest = $full.Substring(2).Replace("\", "/")
    return "/mnt/$drive$rest"
}

function Resolve-RepoPath {
    param([string]$PathValue)
    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return [System.IO.Path]::GetFullPath($PathValue)
    }
    return [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $PathValue))
}

$workdirWsl = "$(Convert-ToWslPath $SurrolRoot)/Benchmark/state_based"
$micromambaWsl = "$(Convert-ToWslPath $MambaRoot)/bin/micromamba"
$envPathWsl = Convert-ToWslPath $EnvPath
$episodeOutWsl = Convert-ToWslPath (Resolve-RepoPath $EpisodeOut)
$stepOutWsl = Convert-ToWslPath (Resolve-RepoPath $StepOut)

$experimentScript = @'
import argparse
import csv
from pathlib import Path

import numpy as np

from surrol.tasks.gauze_retrieve_org import GauzeRetrieve
from surrol.tasks.needle_pick_org import NeedlePick


TASKS = {
    "NeedlePick": NeedlePick,
    "GauzeRetrieve": GauzeRetrieve,
}

PRIORITY = ["depth_scale_error", "perception_bias", "near_target_drift"]
ROUTE_BY_COMPONENT = {
    "depth_scale_error": "depth_reestimate_or_cautious_approach",
    "perception_bias": "reobserve_reestimate",
    "near_target_drift": "low_gain_correction_or_replan",
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode-out", required=True)
    parser.add_argument("--step-out", required=True)
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--failure-combos", required=True)
    parser.add_argument("--seeds", type=int, required=True)
    parser.add_argument("--episodes", type=int, required=True)
    parser.add_argument("--max-steps", type=int, required=True)
    parser.add_argument("--recovery-steps", type=int, required=True)
    parser.add_argument("--trigger-mode", choices=["coarse", "goalaware"], required=True)
    parser.add_argument("--perception-bias-scale", type=float, default=1.0)
    parser.add_argument("--depth-scale-error", type=float, default=0.12)
    parser.add_argument("--near-target-drift-scale", type=float, default=1.0)
    parser.add_argument("--near-target-threshold", type=float, default=0.12)
    parser.add_argument("--perception-review-threshold", type=float, default=0.004)
    return parser.parse_args()


def parse_combo(combo):
    parts = [item.strip() for item in str(combo).split("+") if item.strip()]
    allowed = {"perception_bias", "depth_scale_error", "near_target_drift"}
    unknown = sorted(set(parts) - allowed)
    if unknown:
        raise ValueError(f"Unknown mixed-fault components: {unknown}")
    return parts


def priority_route(components):
    for component in PRIORITY:
        if component in components:
            return ROUTE_BY_COMPONENT[component]
    return "continue"


def priority_recovery_policy(components):
    if "depth_scale_error" in components or "perception_bias" in components:
        return "review_reestimate"
    if "near_target_drift" in components:
        return "phase_replan"
    return "none"


def goal_distance(obs):
    return float(np.linalg.norm(np.asarray(obs["achieved_goal"]) - np.asarray(obs["desired_goal"])))


def corrupt_observation(obs, components, perception_bias_scale, depth_scale_error):
    corrupted = {
        key: np.asarray(value).copy() if isinstance(value, np.ndarray) else value
        for key, value in obs.items()
    }
    total_error = 0.0
    if "perception_bias" in components:
        before = corrupted["observation"][:3].copy()
        bias = perception_bias_scale * np.array([0.012, -0.008, 0.006], dtype=np.float64)
        corrupted["observation"][:3] = corrupted["observation"][:3] + bias
        total_error += float(np.linalg.norm(corrupted["observation"][:3] - before))
    if "depth_scale_error" in components:
        before_z = float(corrupted["observation"][2])
        corrupted["observation"][2] = corrupted["observation"][2] * (1.0 + depth_scale_error)
        total_error += abs(float(corrupted["observation"][2]) - before_z)
    return corrupted, total_error


def perturb_action(action, components, current_distance, near_target_drift_scale, near_target_threshold):
    base = np.asarray(action, dtype=np.float64)
    proposed = base.copy()
    if "near_target_drift" in components and current_distance < near_target_threshold:
        drift = np.zeros_like(proposed)
        drift[:3] = near_target_drift_scale * np.array([0.45, -0.25, 0.10])[: min(3, proposed.shape[0])]
        proposed = proposed + drift
    clipped = np.clip(proposed, -1.0, 1.0)
    return clipped.astype(np.float32), float(np.linalg.norm(clipped - base)), float(np.max(np.abs(proposed - clipped)) > 1e-8)


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


def run_episode(
    env,
    task,
    combo,
    controller,
    seed,
    episode,
    max_steps,
    recovery_steps,
    trigger_mode,
    perception_bias_scale,
    depth_scale_error,
    near_target_drift_scale,
    near_target_threshold,
    perception_review_threshold,
):
    components = parse_combo(combo)
    route = priority_route(components)
    recovery_policy = priority_recovery_policy(components)
    rng = np.random.default_rng(seed * 1009 + episode * 97 + sum(ord(c) for c in combo + controller))
    np.random.seed(seed)
    env.seed(seed)
    obs = env.reset()
    initial_distance = goal_distance(obs)
    prev_distance = initial_distance
    min_distance = initial_distance
    total_reward = 0.0
    risk_events = 0
    monitor_triggers = 0
    recovery_override_steps = 0
    recovery_replans = 0
    visual_reestimate_triggers = 0
    recovery_phase_replans = 0
    last_recovery_phase = ""
    stalled_count = 0
    recovery_remaining = 0
    visual_reestimate_active = False
    success = 0.0
    step_rows = []

    for step_idx in range(max_steps):
        if controller == "priority_routed" and recovery_policy == "phase_replan":
            phase = phase_replan(env, success)
            if phase is not None:
                recovery_remaining = recovery_steps
                recovery_replans += 1
                recovery_phase_replans += 1
                monitor_triggers += 1
                last_recovery_phase = phase

        obs_for_policy = obs
        perception_error_norm = 0.0
        visual_reestimate_trigger = False
        if controller in {"perturbed", "priority_routed"} and recovery_remaining == 0 and not visual_reestimate_active:
            obs_for_policy, perception_error_norm = corrupt_observation(
                obs, components, perception_bias_scale, depth_scale_error
            )
            if (
                controller == "priority_routed"
                and recovery_policy == "review_reestimate"
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
        action_deviation = 0.0
        clip_event = 0.0
        override = False

        if controller == "clean":
            action = oracle_action
        elif controller == "perturbed":
            action, action_deviation, clip_event = perturb_action(
                oracle_action, components, prev_distance, near_target_drift_scale, near_target_threshold
            )
        elif controller == "priority_routed":
            if recovery_remaining > 0:
                action = oracle_action
                recovery_remaining -= 1
                override = True
                recovery_override_steps += 1
            else:
                action, action_deviation, clip_event = perturb_action(
                    oracle_action, components, prev_distance, near_target_drift_scale, near_target_threshold
                )
        else:
            raise ValueError(f"Unknown controller: {controller}")

        obs, reward, done, info = env.step(action)
        current_distance = goal_distance(obs)
        progress = prev_distance - current_distance
        total_reward += float(reward)
        min_distance = min(min_distance, current_distance)
        stalled_count = stalled_count + 1 if abs(progress) < 1e-4 else 0
        risk_event = risk_event_for_mode(
            progress, current_distance, initial_distance, action_deviation, clip_event, stalled_count, trigger_mode
        )
        risk_events += int(risk_event)

        trigger_after = False
        if controller == "priority_routed" and recovery_remaining == 0 and not visual_reestimate_trigger:
            if risk_event:
                monitor_triggers += 1
                trigger_after = True
                if recovery_policy == "phase_replan":
                    phase = phase_replan(env, success)
                    if phase is not None:
                        recovery_replans += 1
                        recovery_phase_replans += 1
                        last_recovery_phase = phase
                recovery_remaining = recovery_steps

        success = float(info.get("is_success", 0.0))
        step_rows.append(
            {
                "task": task,
                "failure_combo": combo,
                "components": "+".join(components),
                "expected_priority_route": route,
                "priority_recovery_policy": recovery_policy,
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
                "monitor_trigger": float(trigger_after or visual_reestimate_trigger),
                "recovery_override": float(override),
                "recovery_replan": float(recovery_replans),
                "recovery_phase_replans": float(recovery_phase_replans),
                "recovery_phase": last_recovery_phase,
                "visual_reestimate_trigger": float(visual_reestimate_trigger),
                "visual_reestimate_active": float(visual_reestimate_active),
                "action_deviation": action_deviation,
                "clip_event": clip_event,
                "perception_error_norm": perception_error_norm,
                "stalled_count": stalled_count,
            }
        )
        prev_distance = current_distance
        if success >= 1.0:
            break

    episode_row = {
        "task": task,
        "failure_combo": combo,
        "components": "+".join(components),
        "expected_priority_route": route,
        "priority_recovery_policy": recovery_policy,
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
        "visual_reestimate_triggers": visual_reestimate_triggers,
        "recovery_override_rate": recovery_override_steps / float(len(step_rows)),
    }
    return episode_row, step_rows


def main():
    args = parse_args()
    tasks = [item.strip() for item in args.tasks.split(",") if item.strip()]
    combos = [item.strip() for item in args.failure_combos.split(",") if item.strip()]
    episode_out = Path(args.episode_out)
    step_out = Path(args.step_out)
    episode_out.parent.mkdir(parents=True, exist_ok=True)
    step_out.parent.mkdir(parents=True, exist_ok=True)

    controllers = ["clean", "perturbed", "priority_routed"]
    episode_rows = []
    step_rows_all = []

    for task in tasks:
        print(f"TASK {task}", flush=True)
        env = TASKS[task](render_mode=None)
        try:
            for combo in combos:
                print(f"  COMBO {combo}", flush=True)
                for controller in controllers:
                    print(f"    controller={controller}", flush=True)
                    for seed_idx in range(args.seeds):
                        seed = 56000 + seed_idx
                        for episode in range(args.episodes):
                            episode_row, step_rows = run_episode(
                                env,
                                task,
                                combo,
                                controller,
                                seed,
                                episode,
                                args.max_steps,
                                args.recovery_steps,
                                args.trigger_mode,
                                args.perception_bias_scale,
                                args.depth_scale_error,
                                args.near_target_drift_scale,
                                args.near_target_threshold,
                                args.perception_review_threshold,
                            )
                            episode_rows.append(episode_row)
                            step_rows_all.extend(step_rows)
                            print(
                                "      seed",
                                seed,
                                "success",
                                episode_row["success"],
                                "final_distance",
                                f"{episode_row['final_distance']:.4f}",
                                "triggers",
                                episode_row["monitor_triggers"],
                                "steps",
                                episode_row["steps"],
                                flush=True,
                            )
        finally:
            if hasattr(env, "close"):
                env.close()

    with episode_out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(episode_rows[0].keys()))
        writer.writeheader()
        writer.writerows(episode_rows)

    with step_out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(step_rows_all[0].keys()))
        writer.writeheader()
        writer.writerows(step_rows_all)

    print(f"episode_csv={episode_out}")
    print(f"step_csv={step_out}")


if __name__ == "__main__":
    main()
'@

$experimentScript | wsl --cd $workdirWsl $micromambaWsl run -p $envPathWsl python - `
    --episode-out $episodeOutWsl `
    --step-out $stepOutWsl `
    --tasks $Tasks `
    --failure-combos $FailureCombos `
    --seeds $Seeds `
    --episodes $Episodes `
    --max-steps $MaxSteps `
    --recovery-steps $RecoverySteps `
    --trigger-mode $TriggerMode `
    --perception-bias-scale $PerceptionBiasScale `
    --depth-scale-error $DepthScaleError `
    --near-target-drift-scale $NearTargetDriftScale `
    --near-target-threshold $NearTargetThreshold `
    --perception-review-threshold $PerceptionReviewThreshold
