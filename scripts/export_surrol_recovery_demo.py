from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a SurRoL/PyBullet NeedlePick fault-to-recovery video."
    )
    parser.add_argument("--surrol-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "reports" / "media" / "surrol_recovery_demo")
    parser.add_argument("--seed", type=int, default=43123)
    parser.add_argument("--fault-steps", type=int, default=16)
    parser.add_argument("--max-steps", type=int, default=90)
    parser.add_argument("--fps", type=int, default=4)
    parser.add_argument("--post-success-hold-sec", type=float, default=4.0)
    return parser.parse_args()


def configure_surrol_path(surrol_root: Path) -> None:
    state_based = surrol_root / "Benchmark" / "state_based"
    if not state_based.exists():
        raise FileNotFoundError(f"SurRoL state_based path not found: {state_based}")
    sys.path.insert(0, str(state_based))


def goal_distance(obs: dict) -> float:
    achieved = np.asarray(obs["achieved_goal"], dtype=np.float64)
    desired = np.asarray(obs["desired_goal"], dtype=np.float64)
    return float(np.linalg.norm(achieved - desired))


def load_font(size: int):
    for name in ("DejaVuSans.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    return ImageFont.load_default()


def annotate_frame(rgb: np.ndarray, lines: list[str], banner_color: tuple[int, int, int, int]) -> np.ndarray:
    image = Image.fromarray(np.asarray(rgb).astype(np.uint8)).convert("RGB")
    draw = ImageDraw.Draw(image, "RGBA")
    width, _ = image.size
    box_height = 92
    draw.rectangle((0, 0, width, box_height), fill=(0, 0, 0, 155))
    draw.rectangle((0, 0, 12, box_height), fill=banner_color)
    title_font = load_font(18)
    body_font = load_font(15)
    y = 10
    draw.text((22, y), lines[0], fill=(255, 255, 255, 255), font=title_font)
    y += 29
    for line in lines[1:]:
        draw.text((22, y), line, fill=(235, 235, 235, 255), font=body_font)
        y += 22
    return np.asarray(image)


def downsample_for_gif(frames: list[np.ndarray]) -> list[Image.Image]:
    out = []
    for frame in frames:
        image = Image.fromarray(frame)
        out.append(image.resize((320, 240), resample=Image.Resampling.BILINEAR).convert("P", palette=Image.Palette.ADAPTIVE))
    return out


def write_mp4_with_ffmpeg(path: Path, frames: list[np.ndarray], fps: int) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg was not found on PATH; cannot export MP4.")
    tmp_dir = path.parent / "_tmp_surrol_recovery_frames"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)
    try:
        for idx, frame in enumerate(frames):
            imageio.imwrite(tmp_dir / f"frame_{idx:04d}.png", frame)
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-framerate",
                str(fps),
                "-i",
                str(tmp_dir / "frame_%04d.png"),
                "-pix_fmt",
                "yuv420p",
                "-vf",
                "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                str(path),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def write_gif(path: Path, frames: list[np.ndarray], fps: int) -> None:
    gif_frames = downsample_for_gif(frames)
    duration_ms = max(1, int(round(1000 / max(1, fps))))
    first, rest = gif_frames[0], gif_frames[1:]
    first.save(
        path,
        save_all=True,
        append_images=rest,
        duration=duration_ms,
        loop=0,
        optimize=False,
    )


def write_trace(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_readme(
    out_dir: Path,
    success: float,
    final_distance: float,
    trigger_step: int | None,
    total_steps: int,
) -> None:
    lines = [
        "# SurRoL Recovery Demo",
        "",
        "This directory contains a SurRoL/PyBullet NeedlePick recovery video. It is separate from the CircleRL proxy media.",
        "",
        "| Asset | File |",
        "| --- | --- |",
        "| MP4 video | [surrol_needlepick_action_freeze_monitor_recovery.mp4](surrol_needlepick_action_freeze_monitor_recovery.mp4) |",
        "| GIF preview | [surrol_needlepick_action_freeze_monitor_recovery.gif](surrol_needlepick_action_freeze_monitor_recovery.gif) |",
        "| Trace CSV | [surrol_needlepick_action_freeze_monitor_recovery_trace.csv](surrol_needlepick_action_freeze_monitor_recovery_trace.csv) |",
        "| Final preview frame | [surrol_needlepick_action_freeze_monitor_recovery_preview.png](surrol_needlepick_action_freeze_monitor_recovery_preview.png) |",
        "| Fault start frame | [step_000_fault_start.png](frames/step_000_fault_start.png) |",
        "| Monitor trigger frame | [step_016_monitor_trigger.png](frames/step_016_monitor_trigger.png) |",
        "| Recovery completion frame | [step_final_recovered.png](frames/step_final_recovered.png) |",
        "",
        (
            f"Result: success={success:.1f}, final_distance={final_distance:.4f}, "
            f"trigger_step={trigger_step}, total_steps={total_steps}."
        ),
        (
            "The MP4/GIF are slowed and hold the recovered final frame so the "
            "monitor-recovery segment and completion are visible rather than "
            "cutting off immediately at success."
        ),
        "",
        (
            "Fault protocol: the first segment freezes the executed action, causing no meaningful progress. "
            "The monitor then routes execution to a bounded recovery override using the SurRoL scripted task action."
        ),
        "",
        (
            "Scope note: this is SurRoL/PyBullet simulator footage with a scripted monitor recovery override; "
            "it is not real-robot or clinical validation."
        ),
    ]
    (out_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    configure_surrol_path(args.surrol_root)

    from surrol.tasks.needle_pick_org import NeedlePick

    out_dir = args.out_dir
    frames_dir = out_dir / "frames"
    out_dir.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)

    np.random.seed(args.seed)
    env = NeedlePick(render_mode=None)
    rows: list[dict[str, object]] = []
    frames: list[np.ndarray] = []
    keyframes: dict[str, np.ndarray] = {}
    trigger_step: int | None = None
    success = 0.0
    final_distance = float("nan")

    try:
        env.seed(args.seed)
        obs = env.reset()
        initial_distance = goal_distance(obs)
        previous_distance = initial_distance
        min_distance = initial_distance

        for step_idx in range(args.max_steps):
            oracle_action = np.asarray(env.get_oracle_action(obs), dtype=np.float32)
            if step_idx < args.fault_steps:
                phase = "fault_start" if step_idx == 0 else "fault_action_freeze"
                route = "perturbed_action_freeze"
                action = np.zeros_like(oracle_action)
                monitor_trigger = 0.0
                banner = (210, 70, 70, 230)
            else:
                if trigger_step is None:
                    trigger_step = step_idx
                    monitor_trigger = 1.0
                    phase = "monitor_trigger"
                else:
                    monitor_trigger = 0.0
                    phase = "monitor_recovery"
                route = "monitor_recovery_oracle_override"
                action = oracle_action
                banner = (70, 155, 220, 230)

            obs, reward, done, info = env.step(action)
            distance = goal_distance(obs)
            progress = previous_distance - distance
            min_distance = min(min_distance, distance)
            success = float(info.get("is_success", 0.0))
            final_distance = distance

            if success >= 1.0:
                phase = "recovery_complete"
                route = "success_after_monitor_recovery"
                banner = (80, 190, 110, 230)

            rgb = env.render(mode="rgb_array")
            frame = annotate_frame(
                rgb,
                [
                    f"SurRoL NeedlePick recovery | step {step_idx:03d} | {phase}",
                    f"route={route} | success={success:.1f} | distance={distance:.4f}",
                    f"fault: action freeze first {args.fault_steps} steps, then monitor recovery override",
                ],
                banner,
            )
            frames.append(frame)

            if step_idx == 0:
                keyframes["step_000_fault_start.png"] = frame
            if step_idx == args.fault_steps:
                keyframes["step_016_monitor_trigger.png"] = frame
            if success >= 1.0:
                keyframes["step_final_recovered.png"] = frame

            rows.append(
                {
                    "task": "NeedlePick",
                    "seed": args.seed,
                    "step": step_idx,
                    "phase": phase,
                    "route": route,
                    "monitor_trigger": monitor_trigger,
                    "success": success,
                    "distance": distance,
                    "progress": progress,
                    "initial_distance": initial_distance,
                    "min_distance": min_distance,
                    "final_distance_so_far": final_distance,
                    "reward": float(reward),
                    "action_norm": float(np.linalg.norm(action)),
                    "oracle_action_norm": float(np.linalg.norm(oracle_action)),
                }
            )
            print(
                f"step={step_idx} phase={phase} success={success:.1f} distance={distance:.4f}",
                flush=True,
            )
            previous_distance = distance
            if success >= 1.0 or done:
                break
    finally:
        if hasattr(env, "close"):
            env.close()

    if not rows or not frames:
        raise RuntimeError("No frames were generated.")
    if "step_final_recovered.png" not in keyframes:
        keyframes["step_final_not_recovered.png"] = frames[-1]

    mp4_path = out_dir / "surrol_needlepick_action_freeze_monitor_recovery.mp4"
    gif_path = out_dir / "surrol_needlepick_action_freeze_monitor_recovery.gif"
    trace_path = out_dir / "surrol_needlepick_action_freeze_monitor_recovery_trace.csv"

    if frames and args.post_success_hold_sec > 0:
        frames = frames + [frames[-1]] * int(round(args.fps * args.post_success_hold_sec))

    write_mp4_with_ffmpeg(mp4_path, frames, args.fps)
    write_gif(gif_path, frames, args.fps)
    imageio.imwrite(out_dir / "surrol_needlepick_action_freeze_monitor_recovery_preview.png", frames[-1])
    write_trace(trace_path, rows)

    for name, frame in keyframes.items():
        imageio.imwrite(frames_dir / name, frame)

    write_readme(out_dir, success, final_distance, trigger_step, len(rows))
    print(f"mp4={mp4_path}", flush=True)
    print(f"gif={gif_path}", flush=True)
    print(f"trace={trace_path}", flush=True)
    print(
        f"result success={success:.1f} final_distance={final_distance:.4f} "
        f"steps={len(rows)} trigger_step={trigger_step}",
        flush=True,
    )


if __name__ == "__main__":
    main()
