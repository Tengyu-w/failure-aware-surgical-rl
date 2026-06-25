param(
    [string]$SurrolRoot = "external/SurRoL_clean_SR-VPPV",
    [string]$EnvPath = "external/surrol_py38_env",
    [string]$MambaRoot = "external/micromamba",
    [string]$OutDir = "reports/media/surrol_render_evidence",
    [string]$Tasks = "NeedleReach,NeedlePick,GauzeRetrieve",
    [int]$Seed = 56000,
    [int]$MaxSteps = 120,
    [int]$FrameStride = 2
)

$ErrorActionPreference = "Stop"

$workdir = "$SurrolRoot/Benchmark/state_based"
$micromamba = "$MambaRoot/bin/micromamba"

$exportScript = @'
import argparse
import csv
import importlib
import shutil
import subprocess
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont


TASKS = {
    "NeedleReach": ("surrol.tasks.needle_reach_org", "NeedleReach"),
    "NeedlePick": ("surrol.tasks.needle_pick_org", "NeedlePick"),
    "GauzeRetrieve": ("surrol.tasks.gauze_retrieve_org", "GauzeRetrieve"),
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--max-steps", type=int, required=True)
    parser.add_argument("--frame-stride", type=int, required=True)
    return parser.parse_args()


def load_env_class(task_name):
    module_name, class_name = TASKS[task_name]
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def goal_distance(obs):
    return float(np.linalg.norm(np.asarray(obs["achieved_goal"]) - np.asarray(obs["desired_goal"])))


def render_frame(env):
    try:
        frame = env.render(mode="rgb_array")
    except TypeError:
        frame = env.render("rgb_array")
    frame = np.asarray(frame)
    if frame.ndim == 2:
        frame = np.repeat(frame[..., None], 3, axis=-1)
    if frame.shape[-1] > 3:
        frame = frame[..., :3]
    return np.ascontiguousarray(frame.astype(np.uint8))


def annotate(frame, task, step_idx, distance, success):
    image = Image.fromarray(frame)
    draw = ImageDraw.Draw(image)
    text = f"{task} | step={step_idx} | dist={distance:.4f} | success={int(success)}"
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 18)
    except Exception:
        font = ImageFont.load_default()
    pad = 8
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    draw.rectangle((0, 0, width + 2 * pad, height + 2 * pad), fill=(255, 255, 255))
    draw.text((pad, pad), text, fill=(20, 20, 20), font=font)
    return np.asarray(image)


def run_task(task, out_dir, seed, max_steps, frame_stride):
    env_cls = load_env_class(task)
    env = env_cls(render_mode="rgb_array")
    np.random.seed(seed)
    env.seed(seed)
    obs = env.reset()

    task_dir = out_dir / task.lower()
    frame_dir = task_dir / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    frames = []
    saved_steps = set()

    def capture(step_idx, obs, info):
        distance = goal_distance(obs)
        success = float(info.get("is_success", 0.0)) if info else 0.0
        frame = annotate(render_frame(env), task, step_idx, distance, success)
        frames.append(frame)
        if step_idx in {0, max_steps // 4, max_steps // 2, max_steps - 1} or success >= 1.0:
            if step_idx not in saved_steps:
                imageio.imwrite(frame_dir / f"{task.lower()}_step_{step_idx:03d}.png", frame)
                saved_steps.add(step_idx)
        return distance, success

    distance, success = capture(0, obs, {})
    rows.append({"task": task, "step": 0, "goal_distance": distance, "success": success})

    final_info = {}
    final_step = 0
    for step_idx in range(1, max_steps + 1):
        action = env.get_oracle_action(obs) if hasattr(env, "get_oracle_action") else env.action_space.sample()
        obs, reward, done, info = env.step(action)
        final_info = dict(info)
        final_step = step_idx
        distance = goal_distance(obs)
        success = float(info.get("is_success", 0.0))
        rows.append({"task": task, "step": step_idx, "goal_distance": distance, "success": success})
        if step_idx % max(1, frame_stride) == 0 or done or success >= 1.0:
            capture(step_idx, obs, info)
        if done or success >= 1.0:
            break

    if final_step not in saved_steps:
        capture(final_step, obs, final_info)

    csv_path = task_dir / "rollout_trace.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["task", "step", "goal_distance", "success"])
        writer.writeheader()
        writer.writerows(rows)

    gif_path = task_dir / f"{task.lower()}_oracle_rollout.gif"
    mp4_path = task_dir / f"{task.lower()}_oracle_rollout.mp4"
    imageio.mimsave(gif_path, frames, duration=0.08)
    video_frame_dir = task_dir / "video_frames"
    video_frame_dir.mkdir(parents=True, exist_ok=True)
    for idx, frame in enumerate(frames):
        imageio.imwrite(video_frame_dir / f"frame_{idx:04d}.png", frame)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            "12",
            "-i",
            str(video_frame_dir / "frame_%04d.png"),
            "-pix_fmt",
            "yuv420p",
            str(mp4_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    shutil.rmtree(video_frame_dir, ignore_errors=True)
    return {
        "task": task,
        "steps": final_step,
        "success": rows[-1]["success"],
        "final_distance": rows[-1]["goal_distance"],
        "gif": str(gif_path),
        "mp4": str(mp4_path),
        "frames": str(frame_dir),
        "trace": str(csv_path),
    }


def main():
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tasks = [item.strip() for item in args.tasks.split(",") if item.strip()]
    summaries = []
    for offset, task in enumerate(tasks):
        summaries.append(run_task(task, out_dir, args.seed + offset, args.max_steps, args.frame_stride))

    lines = [
        "# SurRoL Render Evidence",
        "",
        "These assets export raw SurRoL/PyBullet RGB rollouts for application and repository evidence.",
        "They complement the CSV metrics and recovery figures by showing that the project was actually run inside SurRoL simulation tasks.",
        "",
        "| Task | Steps | Success | Final distance | GIF | MP4 | Trace |",
        "|---|---:|---:|---:|---|---|---|",
    ]
    for item in summaries:
        lines.append(
            f"| {item['task']} | {item['steps']} | {item['success']:.0f} | {item['final_distance']:.4f} | "
            f"`{Path(item['gif']).name}` | `{Path(item['mp4']).name}` | `{Path(item['trace']).name}` |"
        )
    lines.extend(
        [
            "",
            "Recommended GitHub use: keep one GIF and two still frames under `reports/media/surrol_render_evidence/`,",
            "then link them from the main README as migration evidence from the custom 3D proxy to SurRoL.",
            "",
        ]
    )
    (out_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    for item in summaries:
        print(item)


if __name__ == "__main__":
    main()
'@

$tmpScript = "/tmp/export_surrol_render_assets.py"
$exportScript | wsl -e bash -lc "cat > $tmpScript"

wsl -e bash -lc "cd '$workdir' && PYTHONPATH='$workdir' '$micromamba' run -p '$EnvPath' python '$tmpScript' --out-dir '$OutDir' --tasks '$Tasks' --seed '$Seed' --max-steps '$MaxSteps' --frame-stride '$FrameStride'"
