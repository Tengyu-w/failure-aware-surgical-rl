from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from constraint_surgical_rl import make_tool_navigation_env


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "outputs" / "risk_dataset" / "risk_dataset.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build timestep-level weak risk labels from rollout logs.")
    parser.add_argument("--runs-dir", type=Path, default=ROOT / "runs")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--max-files", type=int, default=120)
    parser.add_argument("--max-rows-per-file", type=int, default=5000)
    parser.add_argument("--safety-margin", type=float, default=0.04)
    parser.add_argument("--force-threshold", type=float, default=0.8)
    parser.add_argument("--budget-threshold", type=float, default=0.2)
    parser.add_argument("--synthetic-navigation-episodes", type=int, default=0)
    parser.add_argument("--synthetic-seed", type=int, default=7000)
    return parser.parse_args()


def find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lower_map = {column.lower(): column for column in df.columns}
    for candidate in candidates:
        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]
    for candidate in candidates:
        needle = candidate.lower()
        for lower, original in lower_map.items():
            if needle in lower:
                return original
    return None


def numeric(df: pd.DataFrame, column: str | None, default: float = 0.0) -> pd.Series:
    if column is None:
        return pd.Series(default, index=df.index, dtype="float64")
    return pd.to_numeric(df[column], errors="coerce").astype("float64")


def sample_rows(df: pd.DataFrame, max_rows: int, seed: int) -> pd.DataFrame:
    if max_rows <= 0 or len(df) <= max_rows:
        return df
    return df.sample(n=max_rows, random_state=seed).sort_index()


def source_files(runs_dir: Path, max_files: int) -> list[Path]:
    patterns = ("**/*_steps.csv", "**/risk_routing_steps.csv", "**/rollout_trace.csv")
    files: list[Path] = []
    for pattern in patterns:
        files.extend(runs_dir.glob(pattern))
    unique = sorted(set(files), key=lambda path: path.stat().st_mtime, reverse=True)
    return unique[:max_files] if max_files > 0 else unique


def build_from_step_file(path: Path, args: argparse.Namespace, file_index: int) -> pd.DataFrame | None:
    try:
        raw = pd.read_csv(path)
    except Exception as exc:
        print(f"skip {path}: {exc}")
        return None
    if raw.empty or "step" not in {column.lower() for column in raw.columns}:
        return None

    raw = sample_rows(raw, args.max_rows_per_file, seed=17 + file_index)
    df = pd.DataFrame(index=raw.index)
    run_name = path.parent.name if path.parent.name != "runs" else path.stem
    df["run_name"] = run_name
    df["source_file"] = str(path)
    df["source_kind"] = "step_log"

    task_col = find_col(raw, ["task"])
    failure_col = find_col(raw, ["failure"])
    controller_col = find_col(raw, ["controller"])
    seed_col = find_col(raw, ["seed"])
    episode_col = find_col(raw, ["episode", "episode_id"])
    step_col = find_col(raw, ["step"])

    df["task"] = raw[task_col].astype(str) if task_col else "unknown"
    df["controller"] = raw[controller_col].astype(str) if controller_col else "unknown"
    df["failure"] = raw[failure_col].astype(str) if failure_col else "unknown"
    df["seed"] = numeric(raw, seed_col, 0).fillna(0).astype(int)
    df["episode"] = numeric(raw, episode_col, 0).fillna(0).astype(int)
    df["step"] = numeric(raw, step_col, 0).fillna(0).astype(int)
    df["episode_id"] = (
        df["source_file"].astype(str)
        + "|seed="
        + df["seed"].astype(str)
        + "|episode="
        + df["episode"].astype(str)
    )

    distance_col = find_col(raw, ["distance_to_goal", "distance", "goal_distance", "final_distance"])
    danger_col = find_col(raw, ["distance_to_forbidden", "danger_distance", "forbidden_distance"])
    force_col = find_col(raw, ["force_proxy", "force", "contact"])
    budget_col = find_col(raw, ["remaining_budget", "safety_budget_remaining", "budget_remaining"])
    action_col = find_col(raw, ["action_norm", "action_deviation", "clip_event"])
    risk_event_col = find_col(raw, ["risk_event"])
    monitor_col = find_col(raw, ["monitor_trigger", "visual_reestimate_trigger"])
    unsafe_warning_col = find_col(raw, ["unsafe_warning"])
    unsafe_violation_col = find_col(raw, ["unsafe_violation"])
    unsafe_abort_col = find_col(raw, ["unsafe_abort"])
    success_col = find_col(raw, ["success", "is_success"])
    budget_exhausted_col = find_col(raw, ["budget_exhausted", "budget_exhaustion"])

    df["distance_to_goal"] = numeric(raw, distance_col, np.nan)
    if danger_col:
        df["distance_to_forbidden"] = numeric(raw, danger_col, np.nan)
    else:
        tool_cols = [find_col(raw, [axis]) for axis in ("tool_x", "tool_y", "tool_z")]
        danger_cols = [find_col(raw, [axis]) for axis in ("danger_x", "danger_y", "danger_z")]
        if all(tool_cols) and all(danger_cols):
            tool = np.column_stack([numeric(raw, col, np.nan).to_numpy() for col in tool_cols])
            danger = np.column_stack([numeric(raw, col, np.nan).to_numpy() for col in danger_cols])
            df["distance_to_forbidden"] = np.linalg.norm(tool - danger, axis=1)
        else:
            df["distance_to_forbidden"] = np.nan

    if force_col:
        df["force_proxy"] = numeric(raw, force_col, 0.0).fillna(0.0)
    else:
        warning = numeric(raw, unsafe_warning_col, 0.0).fillna(0.0)
        violation = numeric(raw, unsafe_violation_col, 0.0).fillna(0.0)
        abort = numeric(raw, unsafe_abort_col, 0.0).fillna(0.0)
        clip = numeric(raw, find_col(raw, ["clip_event"]), 0.0).fillna(0.0)
        df["force_proxy"] = 0.5 * warning + violation + abort + 0.25 * clip

    if budget_col:
        df["remaining_budget"] = numeric(raw, budget_col, np.nan)
    else:
        weak_cost = (
            0.05 * df["force_proxy"].clip(lower=0.0)
            + 0.02 * numeric(raw, risk_event_col, 0.0).fillna(0.0)
            + 0.05 * numeric(raw, unsafe_violation_col, 0.0).fillna(0.0)
        )
        df["remaining_budget"] = 1.0 - weak_cost.groupby(df["episode_id"]).cumsum().clip(lower=0.0, upper=1.5)

    max_step = df.groupby("episode_id")["step"].transform("max").replace(0, np.nan)
    df["normalized_time"] = (df["step"] / max_step).fillna(0.0).clip(0.0, 1.0)
    df["action_norm"] = numeric(raw, action_col, 0.0).fillna(0.0).abs()
    df["progress_5"] = df.groupby("episode_id")["distance_to_goal"].transform(lambda series: series.shift(5) - series)
    if find_col(raw, ["progress"]) is not None:
        df["progress_5"] = df["progress_5"].fillna(numeric(raw, find_col(raw, ["progress"]), 0.0))
    df["progress_5"] = df["progress_5"].fillna(0.0)

    explicit_risk = (
        numeric(raw, risk_event_col, 0.0).fillna(0.0)
        + numeric(raw, monitor_col, 0.0).fillna(0.0)
        + numeric(raw, unsafe_warning_col, 0.0).fillna(0.0)
        + numeric(raw, unsafe_violation_col, 0.0).fillna(0.0)
        + numeric(raw, unsafe_abort_col, 0.0).fillna(0.0)
    ) > 0.0
    success = numeric(raw, success_col, 0.0).fillna(0.0)
    budget_exhausted = numeric(raw, budget_exhausted_col, 0.0).fillna(0.0)
    episode_success = success.groupby(df["episode_id"]).transform("max")
    episode_budget_exhausted = budget_exhausted.groupby(df["episode_id"]).transform("max")
    df["episode_success"] = episode_success
    df["episode_budget_exhausted"] = episode_budget_exhausted

    finite_forbidden = df["distance_to_forbidden"].replace([np.inf, -np.inf], np.nan)
    quantile_margin = finite_forbidden.quantile(0.10) if finite_forbidden.notna().any() else np.nan
    forbidden_threshold = max(args.safety_margin, float(quantile_margin)) if np.isfinite(quantile_margin) else args.safety_margin
    near_forbidden = finite_forbidden < forbidden_threshold

    force_threshold = max(args.force_threshold, float(df["force_proxy"].quantile(0.90)))
    high_force = (df["force_proxy"] > force_threshold) & (df["force_proxy"] > 0.0)
    low_budget = df["remaining_budget"] < args.budget_threshold
    stalled = (df["progress_5"] <= 0.0) & (
        df["distance_to_goal"] > df["distance_to_goal"].median(skipna=True)
    )
    failed_episode = episode_success <= 0.0

    df["risk_label"] = (
        explicit_risk | near_forbidden.fillna(False) | high_force | low_budget | stalled | failed_episode
        | (episode_budget_exhausted > 0.0)
    ).astype(int)

    keep = [
        "run_name",
        "source_file",
        "source_kind",
        "task",
        "controller",
        "failure",
        "seed",
        "episode",
        "episode_id",
        "step",
        "distance_to_goal",
        "distance_to_forbidden",
        "force_proxy",
        "remaining_budget",
        "normalized_time",
        "progress_5",
        "action_norm",
        "episode_success",
        "episode_budget_exhausted",
        "risk_label",
    ]
    return df[keep]


def heuristic_action(env) -> np.ndarray:
    unwrapped = env.unwrapped
    to_target = unwrapped.target_xy - unwrapped.tool_xy
    norm = np.linalg.norm(to_target)
    if norm < 1e-8:
        return np.zeros_like(unwrapped.tool_xy, dtype=np.float32)
    action = to_target / norm
    to_forbidden = unwrapped.tool_xy - unwrapped.forbidden_xy
    forbidden_dist = np.linalg.norm(to_forbidden)
    caution_radius = unwrapped.config.forbidden_radius + 0.16
    if forbidden_dist < caution_radius:
        avoid = to_forbidden / max(forbidden_dist, 1e-8)
        action = action + 0.8 * avoid
        action = action / max(np.linalg.norm(action), 1e-8)
    return action.astype(np.float32)


def synthetic_navigation_rows(episodes: int, seed: int) -> pd.DataFrame:
    rows: list[dict[str, float | str | int]] = []
    methods = {
        "synthetic_unshielded": "conditioned",
        "synthetic_always_tangent": "conditioned_tangent_shielded",
        "synthetic_risk_gated_tangent": "conditioned_risk_gated_tangent_shielded",
    }
    rng = np.random.default_rng(seed)
    for method, variant in methods.items():
        for episode in range(episodes):
            env = make_tool_navigation_env(variant=variant, config_preset="prototype")
            env_seed = seed + 1000 * list(methods).index(method) + episode
            env.reset(seed=env_seed)
            distances: list[float] = []
            terminated = truncated = False
            step = 0
            final_info = {}
            while not (terminated or truncated):
                action = heuristic_action(env)
                if rng.random() < 0.25:
                    action = rng.uniform(-1.0, 1.0, size=env.action_space.shape).astype(np.float32)
                unwrapped = env.unwrapped
                distance = float(np.linalg.norm(unwrapped.target_xy - unwrapped.tool_xy))
                distances.append(distance)
                forbidden_distance = float(
                    np.linalg.norm(unwrapped.tool_xy - unwrapped.forbidden_xy)
                    - (unwrapped.config.forbidden_radius + unwrapped.config.tool_radius)
                )
                previous = distances[-6] if len(distances) > 5 else distance
                obs, reward, terminated, truncated, info = env.step(action)
                final_info = info
                rows.append(
                    {
                        "run_name": method,
                        "source_file": "synthetic_navigation_rollout",
                        "source_kind": "synthetic_navigation",
                        "task": "navigation",
                        "controller": method,
                        "failure": "none",
                        "seed": env_seed,
                        "episode": episode,
                        "episode_id": f"{method}|seed={env_seed}|episode={episode}",
                        "step": step,
                        "distance_to_goal": distance,
                        "distance_to_forbidden": forbidden_distance,
                        "force_proxy": float(unwrapped._force_proxy()),
                        "remaining_budget": float(unwrapped.safety_budget - unwrapped.cumulative_cost),
                        "normalized_time": float(unwrapped.step_count / max(unwrapped.config.max_steps, 1)),
                        "progress_5": float(previous - distance),
                        "action_norm": float(np.linalg.norm(action)),
                        "episode_success": 0.0,
                        "episode_budget_exhausted": 0.0,
                        "risk_label": 0,
                    }
                )
                step += 1
            success = float(final_info.get("success", False))
            budget_exhausted = float(final_info.get("budget_exhausted", False))
            for row in rows:
                if row["episode_id"] == f"{method}|seed={env_seed}|episode={episode}":
                    row["episode_success"] = success
                    row["episode_budget_exhausted"] = budget_exhausted
                    row["risk_label"] = int(
                        row["distance_to_forbidden"] < 0.04
                        or row["force_proxy"] > 0.8
                        or row["remaining_budget"] < 0.2
                        or (row["progress_5"] <= 0.0 and row["distance_to_goal"] > 0.35)
                        or budget_exhausted
                        or not success
                    )
    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    frames: list[pd.DataFrame] = []
    for file_index, path in enumerate(source_files(args.runs_dir, args.max_files)):
        frame = build_from_step_file(path, args, file_index)
        if frame is not None and not frame.empty:
            frames.append(frame)
            print(f"loaded {len(frame):6d} rows from {path}")

    if args.synthetic_navigation_episodes > 0:
        synthetic = synthetic_navigation_rows(args.synthetic_navigation_episodes, args.synthetic_seed)
        frames.append(synthetic)
        print(f"loaded {len(synthetic):6d} rows from synthetic navigation rollouts")

    if not frames:
        raise RuntimeError("No usable step logs found. Try --synthetic-navigation-episodes 20 for a smoke dataset.")

    out = pd.concat(frames, ignore_index=True)
    feature_cols = [
        "distance_to_goal",
        "distance_to_forbidden",
        "force_proxy",
        "remaining_budget",
        "normalized_time",
        "progress_5",
        "action_norm",
    ]
    out[feature_cols] = out[feature_cols].replace([np.inf, -np.inf], np.nan)
    out["distance_to_goal"] = out["distance_to_goal"].fillna(out["distance_to_goal"].median())
    out["distance_to_forbidden"] = out["distance_to_forbidden"].fillna(out["distance_to_forbidden"].median())
    out[feature_cols] = out[feature_cols].fillna(0.0)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    print(f"saved_rows={len(out)}")
    print(f"out={args.out}")
    print("risk_label_rate=" + f"{out['risk_label'].mean():.4f}")
    print(out["source_kind"].value_counts().to_string())


if __name__ == "__main__":
    main()
