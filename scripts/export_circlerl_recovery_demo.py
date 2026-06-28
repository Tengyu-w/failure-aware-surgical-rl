from __future__ import annotations

import csv
import sys
import textwrap
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from constraint_surgical_rl import RiskGatedTangentSafetyShieldAction, make_tool_navigation_env


OUT_DIR = ROOT / "reports" / "media" / "circlerl_recovery_demo"
FPS = 12
SIZE = 256


def xy_to_px(xyz: np.ndarray) -> tuple[int, int]:
    px = ((xyz[:2] + 1.0) * 0.5 * (SIZE - 1)).astype(int)
    return int(px[0]), int(SIZE - 1 - px[1])


def unit(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm < 1e-8:
        return np.zeros_like(vector, dtype=np.float32)
    return (vector / norm).astype(np.float32)


def policy_action(tool: np.ndarray, target: np.ndarray, forbidden: np.ndarray) -> np.ndarray:
    """Simple policy proxy: move to the perceived target, with weak avoidance."""
    action = unit(target - tool)
    to_forbidden = tool - forbidden
    forbidden_dist = float(np.linalg.norm(to_forbidden))
    if forbidden_dist < 0.36:
        avoid = unit(to_forbidden)
        action = unit(action + 0.55 * avoid)
    return action.astype(np.float32)


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    fill: tuple[int, int, int],
    width: int = 68,
    line_step: int = 17,
) -> None:
    try:
        font = ImageFont.truetype("arial.ttf", 14)
        bold = ImageFont.truetype("arialbd.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
        bold = font
    x, y = xy
    wrapped: list[str] = []
    for raw in text.splitlines():
        wrapped.extend(textwrap.wrap(raw, width=width) or [""])
    for idx, line in enumerate(wrapped):
        draw.text((x, y + idx * line_step), line, fill=fill, font=bold if idx == 0 else font)


def annotate(
    frame: np.ndarray,
    path: list[np.ndarray],
    step: int,
    phase: str,
    observed_target: np.ndarray,
    true_target: np.ndarray,
    risk_score: float,
    risk_reasons: str,
    route: str,
    recovery_trigger_step: int,
) -> np.ndarray:
    image = Image.fromarray(frame).convert("RGB").resize((SIZE * 2, SIZE * 2), Image.Resampling.NEAREST)
    draw = ImageDraw.Draw(image, "RGBA")

    scale = 2

    def p(xyz: np.ndarray) -> tuple[int, int]:
        x, y = xy_to_px(xyz)
        return x * scale, y * scale

    if len(path) > 1:
        trail = [p(item) for item in path]
        draw.line(trail, fill=(35, 83, 171, 220), width=4)
        for item in trail[:: max(1, len(trail) // 12)]:
            draw.ellipse((item[0] - 3, item[1] - 3, item[0] + 3, item[1] + 3), fill=(35, 83, 171, 210))

    obs_x, obs_y = p(observed_target)
    draw.line((obs_x - 12, obs_y, obs_x + 12, obs_y), fill=(128, 70, 170, 230), width=4)
    draw.line((obs_x, obs_y - 12, obs_x, obs_y + 12), fill=(128, 70, 170, 230), width=4)
    label_x = max(8, min(obs_x - 120, SIZE * 2 - 130))
    draw.text((label_x, obs_y + 8), "biased estimate", fill=(80, 35, 130, 255))

    tgt_x, tgt_y = p(true_target)
    draw.ellipse((tgt_x - 11, tgt_y - 11, tgt_x + 11, tgt_y + 11), outline=(30, 125, 65, 255), width=4)

    banner_color = (255, 247, 220, 235) if step < recovery_trigger_step else (224, 244, 232, 235)
    draw.rectangle((0, 0, SIZE * 2, 74), fill=banner_color)
    short_reasons = risk_reasons if len(risk_reasons) <= 42 else risk_reasons[:39] + "..."
    draw_text(
        draw,
        (12, 8),
        f"{phase}\nstep={step:03d} | route={route}\nrisk={risk_score:.2f} | reasons={short_reasons}",
        fill=(30, 30, 30),
        width=64,
        line_step=16,
    )

    draw.rectangle((0, SIZE * 2 - 76, SIZE * 2, SIZE * 2), fill=(255, 255, 255, 235))
    draw_text(
        draw,
        (12, SIZE * 2 - 68),
        "CircleRL recovery demo: biased target estimate causes drift. Monitor recovery re-estimates the target and routes control back toward completion.",
        fill=(30, 30, 30),
        width=66,
        line_step=16,
    )
    return np.asarray(image)


def write_video(path: Path, frames: list[np.ndarray]) -> None:
    try:
        imageio.mimsave(path, frames, fps=FPS, quality=8, macro_block_size=16)
    except Exception:
        import cv2

        height, width = frames[0].shape[:2]
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (width, height))
        if not writer.isOpened():
            raise RuntimeError(f"Could not open video writer for {path}")
        for frame in frames:
            writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        writer.release()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frame_dir = OUT_DIR / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)

    base = make_tool_navigation_env("conditioned", render_mode="rgb_array", config_preset="prototype")
    env = RiskGatedTangentSafetyShieldAction(base, threshold=0.48, safety_margin=0.12, stall_distance=0.18)
    obs, _ = env.reset(seed=22)

    unwrapped = env.unwrapped
    unwrapped.tool_xy = np.array([-0.74, -0.54, 0.0], dtype=np.float32)
    unwrapped.target_xy = np.array([0.70, 0.58, 0.0], dtype=np.float32)
    unwrapped.forbidden_xy = np.array([-0.02, -0.06, 0.0], dtype=np.float32)
    unwrapped.safety_budget = 1.65
    unwrapped.cumulative_cost = 0.0
    unwrapped.step_count = 0
    obs = unwrapped._obs()

    true_target = unwrapped.target_xy.copy()
    biased_target = np.array([0.64, -0.63, 0.0], dtype=np.float32)
    recovery_trigger_step = 34
    max_steps = 90
    path = [unwrapped.tool_xy.copy()]
    frames: list[np.ndarray] = []
    rows: list[dict[str, float | int | str]] = []

    selected_frame_steps = {0: "step_000_fault_start.png", recovery_trigger_step: "step_034_recovery_trigger.png"}
    final_frame_name = "step_final_recovered.png"

    info: dict = {}
    terminated = truncated = False
    for step in range(max_steps):
        recovery_active = step >= recovery_trigger_step
        target_for_action = true_target if recovery_active else biased_target
        phase = "FAULT PHASE: biased target estimate" if not recovery_active else "RECOVERY PHASE: target re-estimated"
        route = "human_review_reestimate -> monitor_recovery" if recovery_active else "auto_execute_on_biased_state"

        action = policy_action(unwrapped.tool_xy, target_for_action, unwrapped.forbidden_xy)
        obs, reward, terminated, truncated, info = env.step(action)
        path.append(unwrapped.tool_xy.copy())

        if float(info.get("risk_gate_active", 0.0)) > 0:
            route = "risk_gated_tangent_backup" if not recovery_active else "monitor_recovery + tangent_backup"

        rendered = env.render()
        annotated = annotate(
            rendered,
            path,
            step,
            phase,
            biased_target,
            true_target,
            float(info.get("risk_score", 0.0)),
            str(info.get("risk_reasons", "low_risk")),
            route,
            recovery_trigger_step,
        )
        frames.append(annotated)
        if step in selected_frame_steps:
            imageio.imwrite(frame_dir / selected_frame_steps[step], annotated)

        rows.append(
            {
                "step": step,
                "phase": "recovery" if recovery_active else "fault",
                "tool_x": float(unwrapped.tool_xy[0]),
                "tool_y": float(unwrapped.tool_xy[1]),
                "tool_z": float(unwrapped.tool_xy[2]),
                "target_x": float(true_target[0]),
                "target_y": float(true_target[1]),
                "observed_target_x": float(target_for_action[0]),
                "observed_target_y": float(target_for_action[1]),
                "distance_to_goal": float(info.get("distance_to_goal", np.nan)),
                "force_proxy": float(info.get("force_proxy", np.nan)),
                "remaining_budget": float(info.get("remaining_budget", np.nan)),
                "risk_score": float(info.get("risk_score", 0.0)),
                "risk_gate_active": float(info.get("risk_gate_active", 0.0)),
                "risk_reasons": str(info.get("risk_reasons", "low_risk")),
                "route": route,
                "success": float(info.get("success", False)),
                "budget_exhausted": float(info.get("budget_exhausted", False)),
            }
        )

        if recovery_active and bool(info.get("success", False)):
            break
        if terminated or truncated:
            break

    if frames:
        imageio.imwrite(frame_dir / final_frame_name, frames[-1])
        hold = [frames[-1]] * (FPS * 2)
        frames = frames + hold

    mp4_path = OUT_DIR / "circlerl_bias_recovery.mp4"
    gif_path = OUT_DIR / "circlerl_bias_recovery.gif"
    trace_path = OUT_DIR / "circlerl_bias_recovery_trace.csv"
    write_video(mp4_path, frames)
    imageio.mimsave(gif_path, frames[::2], duration=2 / FPS)

    with trace_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    readme = OUT_DIR / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# CircleRL Recovery Demo",
                "",
                "This media asset shows the custom constrained tool-navigation proxy used before the SurRoL migration.",
                "A biased target estimate first drives the tool along the wrong route. At the recovery trigger, the target is re-estimated and the monitor uses the true target while the risk-gated tangent controller remains available near the forbidden zone.",
                "",
                "| Asset | Path |",
                "| --- | --- |",
                "| MP4 video | [circlerl_bias_recovery.mp4](circlerl_bias_recovery.mp4) |",
                "| GIF preview | [circlerl_bias_recovery.gif](circlerl_bias_recovery.gif) |",
                "| Trace CSV | [circlerl_bias_recovery_trace.csv](circlerl_bias_recovery_trace.csv) |",
                "| Fault start frame | [step_000_fault_start.png](frames/step_000_fault_start.png) |",
                "| Recovery trigger frame | [step_034_recovery_trigger.png](frames/step_034_recovery_trigger.png) |",
                "| Final recovered frame | [step_final_recovered.png](frames/step_final_recovered.png) |",
                "",
                "Scope note: this is a CircleRL/proxy controller visualization, not a SurRoL/PyBullet surgical rollout and not real-robot footage.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(f"mp4={mp4_path}")
    print(f"gif={gif_path}")
    print(f"trace={trace_path}")
    print(f"steps={len(rows)}")
    print(f"success={rows[-1]['success']}")
    print(f"final_distance={rows[-1]['distance_to_goal']:.4f}")


if __name__ == "__main__":
    main()
