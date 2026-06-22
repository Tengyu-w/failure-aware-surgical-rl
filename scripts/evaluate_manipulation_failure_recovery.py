from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from constraint_surgical_rl import make_tool_manipulation_env


FAILURE_MODES = ("none", "object_state_bias", "object_dropout", "execution_slip", "contact_loss")
CONTROLLERS = ("base_controller", "monitor_recovery")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", default="conditioned_tangent_shielded")
    parser.add_argument("--failure-mode", choices=FAILURE_MODES, default="object_state_bias")
    parser.add_argument("--controller", choices=CONTROLLERS, default="base_controller")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--seed", type=int, default=9500)
    parser.add_argument("--failure-step", type=int, default=5)
    parser.add_argument("--bias-magnitude", type=float, default=0.45)
    parser.add_argument("--slip-scale", type=float, default=0.20)
    parser.add_argument("--contact-loss-delay", type=int, default=6)
    parser.add_argument("--recovery-steps", type=int, default=18)
    parser.add_argument("--out", type=Path, default=Path("runs") / "manipulation_failure_eval.csv")
    return parser.parse_args()


def sample_offset(rng: np.random.Generator, shape: tuple[int, ...], magnitude: float) -> np.ndarray:
    direction = rng.normal(size=shape).astype(np.float32)
    norm = np.linalg.norm(direction)
    if norm < 1e-8:
        direction = np.ones(shape, dtype=np.float32)
        norm = np.linalg.norm(direction)
    return (direction / norm * magnitude).astype(np.float32)


def classify_failure(
    object_bias: np.ndarray | None,
    object_dropout: bool,
    execution_slip: bool,
    contact_loss_ready: bool,
) -> str:
    if object_dropout:
        return "object_dropout"
    if object_bias is not None:
        return "object_state_bias"
    if execution_slip:
        return "execution_slip"
    if contact_loss_ready:
        return "contact_loss"
    return "none"


def manipulation_action(env, object_estimate: np.ndarray | None = None, goal_estimate: np.ndarray | None = None) -> np.ndarray:
    unwrapped = env.unwrapped
    object_xyz = unwrapped.object_xy if object_estimate is None else object_estimate
    goal_xyz = unwrapped.goal_xy if goal_estimate is None else goal_estimate

    if unwrapped.object_delivered:
        target = unwrapped.retract_xy
    else:
        push_dir = goal_xyz - object_xyz
        push_norm = np.linalg.norm(push_dir)
        if push_norm < 1e-8:
            push_dir = np.ones_like(push_dir, dtype=np.float32)
            push_norm = np.linalg.norm(push_dir)
        push_dir = push_dir / push_norm
        pre_push = object_xyz - push_dir * (unwrapped.config.contact_radius * 0.6)
        if np.linalg.norm(unwrapped.tool_xy - pre_push) > unwrapped.config.contact_radius * 0.5:
            target = pre_push
        else:
            target = unwrapped.tool_xy + push_dir

    action = target - unwrapped.tool_xy
    norm = np.linalg.norm(action)
    if norm < 1e-8:
        return np.zeros_like(unwrapped.tool_xy, dtype=np.float32)
    action = action / norm

    to_forbidden = unwrapped.tool_xy - unwrapped.forbidden_xy
    forbidden_dist = np.linalg.norm(to_forbidden)
    caution_radius = unwrapped.config.forbidden_radius + 0.18
    if forbidden_dist < caution_radius:
        avoid = to_forbidden / max(forbidden_dist, 1e-8)
        action = action + 1.2 * avoid
        action = action / max(np.linalg.norm(action), 1e-8)
    return action.astype(np.float32)


def run_episode(
    variant: str,
    failure_mode: str,
    controller: str,
    seed: int,
    failure_step: int,
    bias_magnitude: float,
    slip_scale: float,
    contact_loss_delay: int,
    recovery_steps: int,
) -> dict:
    env = make_tool_manipulation_env(variant=variant)
    env.reset(seed=seed)
    rng = np.random.default_rng(seed + 50_000)

    total_reward = 0.0
    terminated = False
    truncated = False
    info = {}
    failure_injected = False
    failure_detected = False
    recovery_remaining = 0
    recovery_steps_used = 0
    object_bias: np.ndarray | None = None
    object_dropout = False
    execution_slip = False
    contact_loss = False
    contact_loss_start_step = -1
    detected_step = -1
    predicted_failure_type = "none"

    while not (terminated or truncated):
        step = env.unwrapped.step_count
        if not failure_injected and step >= failure_step and failure_mode != "none":
            if failure_mode == "object_state_bias":
                object_bias = sample_offset(rng, env.unwrapped.object_xy.shape, bias_magnitude)
            elif failure_mode == "object_dropout":
                object_dropout = True
            elif failure_mode == "execution_slip":
                execution_slip = True
            elif failure_mode == "contact_loss":
                contact_loss = True
                contact_loss_start_step = step
            else:
                raise ValueError(f"Unknown failure mode: {failure_mode}")
            failure_injected = True

        reliability_signal = 0.0
        if object_bias is not None:
            reliability_signal = float(np.linalg.norm(object_bias))
        if object_dropout:
            reliability_signal = max(reliability_signal, 1.0)
        if execution_slip:
            reliability_signal = max(reliability_signal, 1.0 - slip_scale)
        contact_loss_ready = contact_loss and step - contact_loss_start_step >= contact_loss_delay
        if contact_loss_ready:
            reliability_signal = max(reliability_signal, 1.0)

        if failure_injected and reliability_signal > 0.1 and not failure_detected:
            failure_detected = True
            detected_step = step
            predicted_failure_type = classify_failure(
                object_bias=object_bias,
                object_dropout=object_dropout,
                execution_slip=execution_slip,
                contact_loss_ready=contact_loss_ready,
            )
            if controller == "monitor_recovery":
                recovery_remaining = recovery_steps
                object_bias = None
                object_dropout = False
                execution_slip = False
                contact_loss = False

        if object_dropout:
            object_estimate = np.zeros_like(env.unwrapped.object_xy, dtype=np.float32)
        elif object_bias is not None:
            object_estimate = np.clip(env.unwrapped.object_xy + object_bias, -1.0, 1.0)
        else:
            object_estimate = None

        action = manipulation_action(env, object_estimate=object_estimate)
        if recovery_remaining > 0:
            recovery_remaining -= 1
            recovery_steps_used += 1
        if execution_slip:
            action = action * slip_scale

        prev_object = env.unwrapped.object_xy.copy()
        _, reward, terminated, truncated, info = env.step(action)
        if contact_loss:
            env.unwrapped.object_xy = prev_object
            env.unwrapped.object_delivered = False
            env.unwrapped._update_target()
            info = env.unwrapped._info()
            info.update(
                {
                    "success": False,
                    "budget_exhausted": env.unwrapped.cumulative_cost > env.unwrapped.safety_budget,
                    "object_delivered": False,
                    "tool_object_distance": env.unwrapped._tool_object_distance(),
                    "object_goal_distance": env.unwrapped._object_goal_distance(),
                }
            )
        total_reward += reward

    detection_delay = float(detected_step - failure_step) if detected_step >= 0 else np.nan
    expected_failure_type = failure_mode if failure_injected else "none"
    failure_class_correct = float(predicted_failure_type == expected_failure_type)
    return {
        "return": total_reward,
        "success": float(info.get("success", False)),
        "object_delivered": float(info.get("object_delivered", False)),
        "budget_exhausted": float(info.get("budget_exhausted", False)),
        "cumulative_cost": float(info.get("cumulative_cost", 0.0)),
        "final_distance": float(info.get("distance_to_goal", np.nan)),
        "tool_object_distance": float(info.get("tool_object_distance", np.nan)),
        "object_goal_distance": float(info.get("object_goal_distance", np.nan)),
        "final_force_proxy": float(info.get("force_proxy", np.nan)),
        "shield_interventions": float(info.get("shield_interventions", 0.0)),
        "mean_action_deviation": float(info.get("mean_action_deviation", 0.0)),
        "task_phase": float(info.get("task_phase", np.nan)),
        "failure_injected": float(failure_injected),
        "failure_detected": float(failure_detected),
        "false_intervention": float((not failure_injected) and failure_detected),
        "predicted_failure_type": predicted_failure_type,
        "failure_class_correct": failure_class_correct,
        "detection_delay": detection_delay,
        "recovery_triggered": float(recovery_steps_used > 0),
        "recovery_steps_used": float(recovery_steps_used),
        "object_bias_active_at_end": float(object_bias is not None),
        "object_dropout_active_at_end": float(object_dropout),
        "execution_slip_active_at_end": float(execution_slip),
        "contact_loss_active_at_end": float(contact_loss),
    }


def summarize(rows: list[dict]) -> dict:
    out = {}
    for key in rows[0]:
        try:
            values = np.array([row[key] for row in rows], dtype=np.float64)
        except (TypeError, ValueError):
            continue
        if np.isnan(values).all():
            out[key] = 0.0
        else:
            out[key] = float(np.nanmean(values))
    return out


def main() -> None:
    args = parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        run_episode(
            variant=args.variant,
            failure_mode=args.failure_mode,
            controller=args.controller,
            seed=args.seed + idx,
            failure_step=args.failure_step,
            bias_magnitude=args.bias_magnitude,
            slip_scale=args.slip_scale,
            contact_loss_delay=args.contact_loss_delay,
            recovery_steps=args.recovery_steps,
        )
        for idx in range(args.episodes)
    ]
    summary = summarize(rows)

    with args.out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["episode", *rows[0].keys()])
        writer.writeheader()
        for idx, row in enumerate(rows):
            writer.writerow({"episode": idx, **row})

    print(f"variant={args.variant}")
    print(f"failure_mode={args.failure_mode}")
    print(f"controller={args.controller}")
    print(f"episodes={args.episodes}")
    print(f"eval_csv={args.out}")
    for key, value in summary.items():
        print(f"{key}_mean={value:.4f}")


if __name__ == "__main__":
    main()
