from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from stable_baselines3 import PPO

from constraint_surgical_rl import make_tool_navigation_env
from constraint_surgical_rl.envs.presets import CONFIG_PRESET_NAMES

try:
    from scripts.evaluate_heuristic import heuristic_action
except ModuleNotFoundError:
    from evaluate_heuristic import heuristic_action


VARIANTS = (
    "conditioned",
    "conditioned_shielded",
    "conditioned_tangent_shielded",
    "no_phase_budget",
    "no_phase_budget_shielded",
    "no_phase_budget_tangent_shielded",
    "no_budget",
)

CONTROLLERS = ("policy_only", "monitor_recovery", "heuristic_only")
FAILURE_MODES = ("none", "target_drift", "state_target_bias", "state_dropout", "execution_slip")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--variant", choices=VARIANTS, default="conditioned_tangent_shielded")
    parser.add_argument("--config-preset", choices=CONFIG_PRESET_NAMES, default="prototype")
    parser.add_argument("--controller", choices=CONTROLLERS, default="policy_only")
    parser.add_argument("--failure-mode", choices=FAILURE_MODES, default="target_drift")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--seed", type=int, default=7000)
    parser.add_argument("--drift-step", type=int, default=35)
    parser.add_argument("--drift-magnitude", type=float, default=0.35)
    parser.add_argument("--detection-threshold", type=float, default=0.18)
    parser.add_argument("--recovery-steps", type=int, default=18)
    parser.add_argument("--dropout-steps", type=int, default=80)
    parser.add_argument("--slip-scale", type=float, default=0.25)
    parser.add_argument("--slip-detection-delay", type=int, default=4)
    parser.add_argument("--out", type=Path, default=Path("runs") / "failure_recovery_eval.csv")
    parser.add_argument("--deterministic", action="store_true")
    return parser.parse_args()


def drift_target(env, rng: np.random.Generator, magnitude: float) -> float:
    unwrapped = env.unwrapped
    direction = rng.normal(size=unwrapped.target_xy.shape).astype(np.float32)
    norm = np.linalg.norm(direction)
    if norm < 1e-8:
        direction = np.ones_like(direction, dtype=np.float32)
        norm = np.linalg.norm(direction)
    delta = direction / norm * magnitude
    old_target = unwrapped.target_xy.copy()
    unwrapped.target_xy = np.clip(unwrapped.target_xy + delta, -0.85, 0.85).astype(np.float32)
    return float(np.linalg.norm(unwrapped.target_xy - old_target))


def sample_offset(rng: np.random.Generator, shape: tuple[int, ...], magnitude: float) -> np.ndarray:
    direction = rng.normal(size=shape).astype(np.float32)
    norm = np.linalg.norm(direction)
    if norm < 1e-8:
        direction = np.ones(shape, dtype=np.float32)
        norm = np.linalg.norm(direction)
    return (direction / norm * magnitude).astype(np.float32)


def classify_failure(
    target_drift_active: bool,
    obs_bias: np.ndarray | None,
    dropout_remaining: int,
    slip_active: bool,
) -> str:
    if dropout_remaining > 0:
        return "state_dropout"
    if obs_bias is not None:
        return "state_target_bias"
    if slip_active:
        return "execution_slip"
    if target_drift_active:
        return "target_drift"
    return "none"


def observation_target(obs: np.ndarray) -> np.ndarray:
    if obs.shape[0] < 6:
        raise ValueError("Expected observation to include target xyz at indices 3:6.")
    return obs[3:6].copy()


def corrupt_target_observation(obs: np.ndarray, offset: np.ndarray | None) -> np.ndarray:
    if offset is None:
        return obs
    corrupted = np.asarray(obs, dtype=np.float32).copy()
    corrupted[3:6] = np.clip(corrupted[3:6] + offset, -1.0, 1.0)
    return corrupted


def dropout_target_observation(obs: np.ndarray, active: bool) -> np.ndarray:
    if not active:
        return obs
    corrupted = np.asarray(obs, dtype=np.float32).copy()
    corrupted[3:6] = 0.0
    return corrupted


def run_episode(
    model: PPO,
    variant: str,
    config_preset: str,
    controller: str,
    failure_mode: str,
    seed: int,
    drift_step: int,
    drift_magnitude: float,
    detection_threshold: float,
    recovery_steps: int,
    dropout_steps: int,
    slip_scale: float,
    slip_detection_delay: int,
    deterministic: bool,
) -> dict:
    env = make_tool_navigation_env(variant=variant, config_preset=config_preset)
    obs, _ = env.reset(seed=seed)
    rng = np.random.default_rng(seed + 100_000)

    total_reward = 0.0
    terminated = False
    truncated = False
    info = {}
    drifted = False
    drift_size = 0.0
    detected_step = -1
    recovery_remaining = 0
    recovery_steps_used = 0
    prev_target = env.unwrapped.target_xy.copy()
    obs_bias: np.ndarray | None = None
    dropout_remaining = 0
    slip_active = False
    target_drift_active = False
    prev_estimated_target = observation_target(obs)
    pre_drift_distance = np.nan
    low_progress_steps = 0
    prev_distance = env.unwrapped._distance_to_goal()
    predicted_failure_type = "none"

    while not (terminated or truncated):
        step = env.unwrapped.step_count
        if not drifted and step >= drift_step:
            if failure_mode == "none":
                pass
            elif failure_mode == "target_drift":
                pre_drift_distance = env.unwrapped._distance_to_goal()
                drift_size = drift_target(env, rng, drift_magnitude)
                target_drift_active = True
            elif failure_mode == "state_target_bias":
                pre_drift_distance = env.unwrapped._distance_to_goal()
                obs_bias = sample_offset(rng, env.unwrapped.target_xy.shape, drift_magnitude)
                drift_size = float(np.linalg.norm(obs_bias))
            elif failure_mode == "state_dropout":
                pre_drift_distance = env.unwrapped._distance_to_goal()
                dropout_remaining = dropout_steps
                drift_size = 1.0
            elif failure_mode == "execution_slip":
                pre_drift_distance = env.unwrapped._distance_to_goal()
                slip_active = True
                drift_size = 1.0 - slip_scale
            else:
                raise ValueError(f"Unknown failure mode: {failure_mode}")
            drifted = failure_mode != "none"

        obs_for_policy = corrupt_target_observation(obs, obs_bias)
        obs_for_policy = dropout_target_observation(obs_for_policy, dropout_remaining > 0)
        estimated_target = observation_target(obs_for_policy)
        if failure_mode == "target_drift":
            target_jump = float(np.linalg.norm(env.unwrapped.target_xy - prev_target))
        elif failure_mode == "execution_slip":
            current_distance = env.unwrapped._distance_to_goal()
            progress = prev_distance - current_distance
            low_progress_steps = low_progress_steps + 1 if progress < 0.01 else 0
            residual_ready = step - drift_step >= slip_detection_delay
            target_jump = drift_magnitude if slip_active and (residual_ready or low_progress_steps >= slip_detection_delay) else 0.0
        else:
            target_jump = float(np.linalg.norm(estimated_target - prev_estimated_target))
        detected_now = drifted and target_jump >= detection_threshold
        if detected_now and detected_step < 0:
            detected_step = step
            predicted_failure_type = classify_failure(
                target_drift_active=target_drift_active,
                obs_bias=obs_bias,
                dropout_remaining=dropout_remaining,
                slip_active=slip_active,
            )
            if controller == "monitor_recovery":
                recovery_remaining = recovery_steps
                target_drift_active = False
                obs_bias = None
                dropout_remaining = 0
                slip_active = False
                obs_for_policy = obs

        if controller == "heuristic_only" or recovery_remaining > 0:
            action = heuristic_action(env)
            if recovery_remaining > 0:
                recovery_remaining -= 1
                recovery_steps_used += 1
        else:
            action, _ = model.predict(obs_for_policy, deterministic=deterministic)

        prev_target = env.unwrapped.target_xy.copy()
        prev_estimated_target = estimated_target.copy()
        prev_distance = env.unwrapped._distance_to_goal()
        executed_action = np.asarray(action, dtype=np.float32)
        if slip_active:
            executed_action = executed_action * slip_scale
        obs, reward, terminated, truncated, info = env.step(executed_action)
        if dropout_remaining > 0:
            dropout_remaining -= 1
        total_reward += reward

    success = float(info.get("success", False))
    detection_delay = float(detected_step - drift_step) if detected_step >= 0 else np.nan
    expected_failure_type = failure_mode if drifted else "none"
    failure_class_correct = float(predicted_failure_type == expected_failure_type)
    return {
        "return": total_reward,
        "success": success,
        "success_after_drift": success if drifted else 0.0,
        "budget_exhausted": float(info.get("budget_exhausted", False)),
        "cumulative_cost": float(info.get("cumulative_cost", 0.0)),
        "remaining_budget": float(info.get("remaining_budget", 0.0)),
        "final_distance": float(info.get("distance_to_goal", np.nan)),
        "final_force_proxy": float(info.get("force_proxy", np.nan)),
        "shield_interventions": float(info.get("shield_interventions", 0.0)),
        "mean_action_deviation": float(info.get("mean_action_deviation", 0.0)),
        "cumulative_action_deviation": float(info.get("cumulative_action_deviation", 0.0)),
        "target_drifted": float(drifted),
        "target_drift_size": drift_size,
        "drift_detected": float(detected_step >= 0),
        "failure_detected": float(detected_step >= 0),
        "false_intervention": float((not drifted) and detected_step >= 0),
        "predicted_failure_type": predicted_failure_type,
        "failure_class_correct": failure_class_correct,
        "detection_delay": detection_delay,
        "recovery_triggered": float(recovery_steps_used > 0),
        "recovery_steps_used": float(recovery_steps_used),
        "pre_drift_distance": float(pre_drift_distance),
        "state_bias_active_at_end": float(obs_bias is not None),
        "state_dropout_active_at_end": float(dropout_remaining > 0),
        "execution_slip_active_at_end": float(slip_active),
    }


def summarize(rows: list[dict]) -> dict:
    summary = {}
    for key in rows[0]:
        try:
            values = np.array([row[key] for row in rows], dtype=np.float64)
        except (TypeError, ValueError):
            continue
        if np.isnan(values).all():
            summary[key] = 0.0
        else:
            summary[key] = float(np.nanmean(values))
    return summary


def main() -> None:
    args = parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    model = PPO.load(args.model)
    rows = [
        run_episode(
            model,
            variant=args.variant,
            config_preset=args.config_preset,
            controller=args.controller,
            failure_mode=args.failure_mode,
            seed=args.seed + idx,
            drift_step=args.drift_step,
            drift_magnitude=args.drift_magnitude,
            detection_threshold=args.detection_threshold,
            recovery_steps=args.recovery_steps,
            dropout_steps=args.dropout_steps,
            slip_scale=args.slip_scale,
            slip_detection_delay=args.slip_detection_delay,
            deterministic=args.deterministic,
        )
        for idx in range(args.episodes)
    ]
    summary = summarize(rows)

    with args.out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["episode", *rows[0].keys()])
        writer.writeheader()
        for idx, row in enumerate(rows):
            writer.writerow({"episode": idx, **row})

    print(f"episodes={args.episodes}")
    print(f"variant={args.variant}")
    print(f"config_preset={args.config_preset}")
    print(f"controller={args.controller}")
    print(f"failure_mode={args.failure_mode}")
    print(f"model={args.model}")
    print(f"eval_csv={args.out}")
    for key, value in summary.items():
        print(f"{key}_mean={value:.4f}")


if __name__ == "__main__":
    main()
