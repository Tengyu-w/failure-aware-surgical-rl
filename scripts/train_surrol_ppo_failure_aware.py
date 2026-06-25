from __future__ import annotations

import argparse
import json
import sys
import importlib.util
import random
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
try:
    import gym

    GymBase = gym.Env
except Exception:
    GymBase = object


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--surrol-root", type=Path, default=Path("external/SurRoL_clean_SR-VPPV"))
    parser.add_argument("--task", default="NeedlePickRL-v0")
    parser.add_argument("--seed", type=int, default=43000)
    parser.add_argument("--total-timesteps", type=int, default=2048)
    parser.add_argument("--max-episode-steps", type=int, default=100)
    parser.add_argument("--failure-mode", default="none", choices=["none", "action_noise", "action_dropout", "near_target_drift"])
    parser.add_argument("--failure-prob", type=float, default=0.25)
    parser.add_argument("--observation-mode", default="state", choices=["state", "pseudo_vision", "render_pseudo_vision", "render_proprio_vision"])
    parser.add_argument("--pseudo-vision-noise", type=float, default=0.003)
    parser.add_argument(
        "--vision-corruption",
        default="none",
        choices=["none", "gaussian_noise", "brightness_shift", "occlusion", "blackout", "mixed"],
    )
    parser.add_argument("--vision-corruption-prob", type=float, default=0.0)
    parser.add_argument("--vision-corruption-severity", type=float, default=0.25)
    parser.add_argument("--vision-stride", type=int, default=1)
    parser.add_argument("--proprio-dim", type=int, default=7)
    parser.add_argument("--image-grid-size", type=int, default=4)
    parser.add_argument("--image-feature-mode", default="stats_gray", choices=["stats_gray", "stats_rgb"])
    parser.add_argument("--visual-adapter", type=Path, default=None)
    parser.add_argument("--danger-zone", default="none")
    parser.add_argument("--danger-radius", type=float, default=0.052)
    parser.add_argument("--danger-penalty", type=float, default=2.0)
    parser.add_argument("--success-bonus", type=float, default=5.0)
    parser.add_argument("--progress-reward-scale", type=float, default=0.0)
    parser.add_argument("--progress-clip", type=float, default=0.03)
    parser.add_argument("--distance-reward-scale", type=float, default=0.0)
    parser.add_argument("--near-target-action-penalty", type=float, default=0.0)
    parser.add_argument("--near-target-threshold", type=float, default=0.12)
    parser.add_argument("--torch-num-threads", type=int, default=1)
    parser.add_argument("--ppo-learning-rate", type=float, default=3e-4)
    parser.add_argument("--ppo-clip-range", type=float, default=0.2)
    parser.add_argument("--ppo-ent-coef", type=float, default=0.0)
    parser.add_argument("--freeze-log-std", action="store_true")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "runs" / "surrol_ppo_failure_aware")
    parser.add_argument("--init-model", type=Path, default=None)
    parser.add_argument("--check-only", action="store_true")
    return parser.parse_args()


def configure_surrol_path(surrol_root: Path) -> None:
    state_based = surrol_root / "Benchmark" / "state_based"
    if not state_based.exists():
        raise FileNotFoundError(f"SurRoL state_based path not found: {state_based}")
    sys.path.insert(0, str(state_based))


def seed_global_randomness(seed: int) -> None:
    random.seed(int(seed))
    np.random.seed(int(seed))


def image_features(
    image: np.ndarray,
    rng: np.random.Generator,
    pseudo_vision_noise: float,
    grid_size: int = 4,
    feature_mode: str = "stats_gray",
) -> np.ndarray:
    rgb = np.asarray(image, dtype=np.float32)
    if rgb.ndim == 3 and rgb.shape[-1] > 3:
        rgb = rgb[..., :3]
    if rgb.max() > 1.0:
        rgb = rgb / 255.0
    means = rgb.mean(axis=(0, 1))
    stds = rgb.std(axis=(0, 1))
    gray = rgb.mean(axis=-1)
    threshold = float(gray.mean() + gray.std())
    mask = gray >= threshold
    if mask.any():
        yy, xx = np.nonzero(mask)
        centroid = np.array([xx.mean() / max(1, gray.shape[1] - 1), yy.mean() / max(1, gray.shape[0] - 1)], dtype=np.float32)
        area = np.array([mask.mean()], dtype=np.float32)
    else:
        centroid = np.array([0.5, 0.5], dtype=np.float32)
        area = np.array([0.0], dtype=np.float32)
    grid_size = max(1, int(grid_size))
    y_bins = np.linspace(0, gray.shape[0], grid_size + 1, dtype=int)
    x_bins = np.linspace(0, gray.shape[1], grid_size + 1, dtype=int)
    pooled = []
    for y0, y1 in zip(y_bins[:-1], y_bins[1:]):
        for x0, x1 in zip(x_bins[:-1], x_bins[1:]):
            if feature_mode == "stats_rgb":
                pooled.extend(rgb[y0:y1, x0:x1].mean(axis=(0, 1)).tolist())
            elif feature_mode == "stats_gray":
                pooled.append(float(gray[y0:y1, x0:x1].mean()))
            else:
                raise ValueError(f"Unsupported image feature mode: {feature_mode}")
    features = np.concatenate([means, stds, centroid, area, np.array(pooled, dtype=np.float32)]).astype(np.float32)
    if pseudo_vision_noise > 0:
        features += rng.normal(0.0, pseudo_vision_noise, size=features.shape).astype(np.float32)
    return features.astype(np.float32)


def apply_linear_visual_adapter(
    features: np.ndarray,
    input_mean: np.ndarray,
    input_std: np.ndarray,
    residual_weights: np.ndarray,
    residual_bias: np.ndarray,
    blend: float,
) -> np.ndarray:
    vector = np.asarray(features, dtype=np.float64).ravel()
    standardized = (vector - input_mean) / input_std
    residual = standardized @ residual_weights + residual_bias
    return (vector + float(blend) * residual).astype(np.float32)


class LinearVisualDenoisingAdapter:
    def __init__(self, path: Path):
        values = np.load(path)
        self.input_mean = values["input_mean"]
        self.input_std = values["input_std"]
        self.residual_weights = values["residual_weights"]
        self.residual_bias = values["residual_bias"]
        self.blend = float(values["blend"][0])

    def transform(self, features: np.ndarray) -> np.ndarray:
        return apply_linear_visual_adapter(
            features,
            self.input_mean,
            self.input_std,
            self.residual_weights,
            self.residual_bias,
            self.blend,
        )


def corrupt_rendered_image(
    image: np.ndarray,
    rng: np.random.Generator,
    corruption: str,
    probability: float,
    severity: float,
) -> tuple[np.ndarray, float, str]:
    rgb = np.asarray(image, dtype=np.float32)
    original_scale = 255.0 if rgb.max() > 1.0 else 1.0
    normalized = np.clip(rgb / original_scale, 0.0, 1.0)
    probability = float(np.clip(probability, 0.0, 1.0))
    severity = float(np.clip(severity, 0.0, 1.0))
    if corruption == "none" or severity <= 0.0 or rng.random() > probability:
        return image, 0.0, "none"

    applied = corruption
    if corruption == "mixed":
        applied = str(rng.choice(["gaussian_noise", "brightness_shift", "occlusion"]))
    corrupted = normalized.copy()
    if applied == "gaussian_noise":
        corrupted += rng.normal(0.0, 0.20 * severity, size=corrupted.shape).astype(np.float32)
    elif applied == "brightness_shift":
        direction = -1.0 if rng.random() < 0.5 else 1.0
        corrupted *= 1.0 + direction * 0.75 * severity
    elif applied == "occlusion":
        height, width = corrupted.shape[:2]
        side_fraction = 0.15 + 0.45 * severity
        occ_h = max(1, min(height, int(round(height * side_fraction))))
        occ_w = max(1, min(width, int(round(width * side_fraction))))
        y0 = int(rng.integers(0, max(1, height - occ_h + 1)))
        x0 = int(rng.integers(0, max(1, width - occ_w + 1)))
        corrupted[y0 : y0 + occ_h, x0 : x0 + occ_w] = 0.0
    elif applied == "blackout":
        corrupted[:] = 0.0
    else:
        raise ValueError(f"Unsupported vision corruption: {applied}")

    corrupted = np.clip(corrupted, 0.0, 1.0)
    magnitude = float(np.mean(np.abs(corrupted - normalized)))
    output = corrupted * original_scale
    if np.issubdtype(np.asarray(image).dtype, np.integer):
        output = np.rint(output).astype(np.asarray(image).dtype)
    return output, magnitude, applied


def goal_distance(obs: Any) -> float:
    if not isinstance(obs, dict):
        return float("nan")
    achieved = np.asarray(obs.get("achieved_goal", []), dtype=np.float32).ravel()
    desired = np.asarray(obs.get("desired_goal", []), dtype=np.float32).ravel()
    n = min(achieved.size, desired.size)
    if n == 0:
        return float("nan")
    return float(np.linalg.norm(achieved[:n] - desired[:n]))


def progress_delta(previous_obs: Any, current_obs: Any, clip: float) -> tuple[float, bool]:
    previous_distance = goal_distance(previous_obs)
    current_distance = goal_distance(current_obs)
    if not np.isfinite(previous_distance) or not np.isfinite(current_distance):
        return 0.0, False
    previous_goal = np.asarray(previous_obs["desired_goal"], dtype=np.float32).ravel()
    current_goal = np.asarray(current_obs["desired_goal"], dtype=np.float32).ravel()
    goal_changed = previous_goal.shape != current_goal.shape or not np.allclose(previous_goal, current_goal, atol=1e-6)
    if goal_changed:
        return 0.0, True
    return float(np.clip(previous_distance - current_distance, -abs(clip), abs(clip))), False


def precision_shaping(
    distance: float,
    action: np.ndarray,
    distance_reward_scale: float,
    near_target_action_penalty: float,
    near_target_threshold: float,
) -> tuple[float, float]:
    if not np.isfinite(distance):
        return 0.0, 0.0
    distance_reward = -float(distance_reward_scale) * max(0.0, float(distance))
    threshold = max(1e-8, float(near_target_threshold))
    closeness = float(np.clip(1.0 - float(distance) / threshold, 0.0, 1.0))
    action_array = np.asarray(action, dtype=np.float32).ravel()
    controlled_action = action_array[: min(3, action_array.size)]
    action_penalty = float(near_target_action_penalty) * closeness * float(np.mean(controlled_action ** 2))
    return distance_reward, action_penalty


def flatten_obs(
    obs: Any,
    observation_mode: str,
    rng: np.random.Generator,
    pseudo_vision_noise: float,
    rendered_image: np.ndarray | None = None,
    vision_corruption: str = "none",
    vision_corruption_prob: float = 0.0,
    vision_corruption_severity: float = 0.25,
    vision_diagnostics: dict[str, Any] | None = None,
    proprio_dim: int = 7,
    image_grid_size: int = 4,
    image_feature_mode: str = "stats_gray",
) -> np.ndarray:
    if isinstance(obs, dict):
        if observation_mode == "render_proprio_vision":
            robot_state = np.asarray(obs["observation"], dtype=np.float32).ravel()
            flat = robot_state[: max(0, int(proprio_dim))].astype(np.float32)
        else:
            parts = [
                np.asarray(obs["observation"], dtype=np.float32).ravel(),
                np.asarray(obs["achieved_goal"], dtype=np.float32).ravel(),
                np.asarray(obs["desired_goal"], dtype=np.float32).ravel(),
            ]
            flat = np.concatenate(parts).astype(np.float32)
        if observation_mode == "pseudo_vision":
            achieved = np.asarray(obs["achieved_goal"], dtype=np.float32).ravel()
            desired = np.asarray(obs["desired_goal"], dtype=np.float32).ravel()
            n = min(6, achieved.size, desired.size)
            keypoint_delta = desired[:n] - achieved[:n]
            noisy_keypoints = achieved[:n] + rng.normal(0.0, pseudo_vision_noise, size=n).astype(np.float32)
            pseudo_depth = np.linalg.norm(keypoint_delta.reshape(-1, 3), axis=1) if n % 3 == 0 else np.array([np.linalg.norm(keypoint_delta)])
            flat = np.concatenate([flat, noisy_keypoints, keypoint_delta, pseudo_depth.astype(np.float32)]).astype(np.float32)
        elif observation_mode in {"render_pseudo_vision", "render_proprio_vision"}:
            if rendered_image is None:
                raise ValueError(f"{observation_mode} requires a rendered image")
            corrupted, magnitude, applied = corrupt_rendered_image(
                rendered_image,
                rng,
                vision_corruption,
                vision_corruption_prob,
                vision_corruption_severity,
            )
            if vision_diagnostics is not None:
                vision_diagnostics.update(
                    {"visual_corruption_magnitude": magnitude, "visual_corruption_applied": applied}
                )
            features = image_features(
                corrupted,
                rng,
                pseudo_vision_noise,
                grid_size=image_grid_size,
                feature_mode=image_feature_mode,
            )
            flat = np.concatenate([flat, features]).astype(np.float32)
        return flat
    return np.asarray(obs, dtype=np.float32).ravel()


def resolve_danger_center(obs: Any, danger_zone: str) -> np.ndarray | None:
    if danger_zone in {"", "none", None} or not isinstance(obs, dict):
        return None
    desired = np.asarray(obs["desired_goal"], dtype=np.float32).ravel()
    if desired.size < 3:
        return None
    if danger_zone == "goal_drift_proxy":
        return desired[:3] + np.array([0.045, -0.025, 0.010], dtype=np.float32)
    values = np.array([float(item.strip()) for item in str(danger_zone).split(",")], dtype=np.float32)
    if values.size != 3:
        raise ValueError("danger-zone must be none, goal_drift_proxy, or x,y,z")
    return values


def corrupt_action(
    action: np.ndarray,
    obs: Any,
    failure_mode: str,
    failure_prob: float,
    rng: np.random.Generator,
) -> np.ndarray:
    if failure_mode == "none" or rng.random() > failure_prob:
        return action
    out = np.asarray(action, dtype=np.float32).copy()
    if failure_mode == "action_noise":
        out += rng.normal(0.0, 0.20, size=out.shape).astype(np.float32)
    elif failure_mode == "action_dropout":
        out[:] = 0.0
    elif failure_mode == "near_target_drift":
        if isinstance(obs, dict):
            achieved = np.asarray(obs["achieved_goal"], dtype=np.float32).ravel()
            desired = np.asarray(obs["desired_goal"], dtype=np.float32).ravel()
            if achieved.size >= 3 and desired.size >= 3 and np.linalg.norm(achieved[:3] - desired[:3]) < 0.12:
                out[: min(3, out.size)] += np.array([0.45, -0.25, 0.10], dtype=np.float32)[: min(3, out.size)]
    return np.clip(out, -1.0, 1.0)


class FailureAwareSurrolWrapper(GymBase):
    def __init__(self, env: Any, args: argparse.Namespace):
        from gym import spaces

        self.env = env
        self.args = args
        adapter_path = getattr(args, "visual_adapter", None)
        self.visual_adapter = LinearVisualDenoisingAdapter(adapter_path) if adapter_path is not None else None
        self.rng = np.random.default_rng(args.seed)
        self.steps = 0
        self._cached_rendered_image: np.ndarray | None = None
        self._cached_visual_features: np.ndarray | None = None
        self._cached_visual_corruption_magnitude = 0.0
        self._cached_visual_corruption_applied = "none"
        self._last_render_step = -1
        self.visual_frame_updated = False
        self.visual_frame_age = 0
        self.last_visual_corruption_magnitude = 0.0
        self.last_visual_corruption_applied = "none"
        obs = self.env.reset()
        self.last_raw_obs = obs
        rendered = self._render_for_obs() if args.observation_mode in {"render_pseudo_vision", "render_proprio_vision"} else None
        flat = self._flatten(obs, rendered)
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=flat.shape, dtype=np.float32)
        self.action_space = env.action_space
        self.metadata = getattr(env, "metadata", {})

    def _render_for_obs(self) -> np.ndarray:
        stride = max(1, int(getattr(self.args, "vision_stride", 1)))
        should_update = (
            self._cached_rendered_image is None
            or self._last_render_step < 0
            or self.steps - self._last_render_step >= stride
        )
        if should_update:
            try:
                image = self.env.render(mode="rgb_array")
            except TypeError:
                image = self.env.render("rgb_array")
            self._cached_rendered_image = np.asarray(image)
            self._last_render_step = self.steps
        self.visual_frame_updated = should_update
        self.visual_frame_age = max(0, self.steps - self._last_render_step)
        return np.asarray(self._cached_rendered_image)

    def _flatten(self, obs: Any, rendered: np.ndarray | None = None) -> np.ndarray:
        if self.args.observation_mode in {"render_pseudo_vision", "render_proprio_vision"}:
            if rendered is None:
                raise ValueError(f"{self.args.observation_mode} requires a rendered image")
            if self.visual_frame_updated or self._cached_visual_features is None:
                corrupted, magnitude, applied = corrupt_rendered_image(
                    rendered,
                    self.rng,
                    getattr(self.args, "vision_corruption", "none"),
                    getattr(self.args, "vision_corruption_prob", 0.0),
                    getattr(self.args, "vision_corruption_severity", 0.25),
                )
                self._cached_visual_features = image_features(
                    corrupted,
                    self.rng,
                    self.args.pseudo_vision_noise,
                    grid_size=getattr(self.args, "image_grid_size", 4),
                    feature_mode=getattr(self.args, "image_feature_mode", "stats_gray"),
                )
                visual_adapter = getattr(self, "visual_adapter", None)
                if visual_adapter is not None:
                    self._cached_visual_features = visual_adapter.transform(self._cached_visual_features)
                self._cached_visual_corruption_magnitude = magnitude
                self._cached_visual_corruption_applied = applied
            self.last_visual_corruption_magnitude = self._cached_visual_corruption_magnitude
            self.last_visual_corruption_applied = self._cached_visual_corruption_applied
            if self.args.observation_mode == "render_proprio_vision":
                base = np.asarray(obs["observation"], dtype=np.float32).ravel()[
                    : max(0, int(getattr(self.args, "proprio_dim", 7)))
                ]
            else:
                base = np.concatenate(
                    [
                        np.asarray(obs["observation"], dtype=np.float32).ravel(),
                        np.asarray(obs["achieved_goal"], dtype=np.float32).ravel(),
                        np.asarray(obs["desired_goal"], dtype=np.float32).ravel(),
                    ]
                )
            return np.concatenate([base, self._cached_visual_features]).astype(np.float32)

        diagnostics: dict[str, Any] = {}
        flat = flatten_obs(
            obs,
            self.args.observation_mode,
            self.rng,
            self.args.pseudo_vision_noise,
            rendered,
            getattr(self.args, "vision_corruption", "none"),
            getattr(self.args, "vision_corruption_prob", 0.0),
            getattr(self.args, "vision_corruption_severity", 0.25),
            diagnostics,
            getattr(self.args, "proprio_dim", 7),
            getattr(self.args, "image_grid_size", 4),
            getattr(self.args, "image_feature_mode", "stats_gray"),
        )
        self.last_visual_corruption_magnitude = float(diagnostics.get("visual_corruption_magnitude", 0.0))
        self.last_visual_corruption_applied = str(diagnostics.get("visual_corruption_applied", "none"))
        return flat

    def seed(self, seed: int | None = None):
        if seed is not None:
            seed_global_randomness(seed)
            self.rng = np.random.default_rng(seed)
        if hasattr(self.env, "seed"):
            return self.env.seed(seed)
        return [seed]

    def reset(self):
        self.steps = 0
        self._cached_rendered_image = None
        self._cached_visual_features = None
        self._cached_visual_corruption_magnitude = 0.0
        self._cached_visual_corruption_applied = "none"
        self._last_render_step = -1
        obs = self.env.reset()
        self.last_raw_obs = obs
        rendered = self._render_for_obs() if self.args.observation_mode in {"render_pseudo_vision", "render_proprio_vision"} else None
        return self._flatten(obs, rendered)

    def step(self, action):
        self.steps += 1
        raw_action = corrupt_action(action, self.last_raw_obs, self.args.failure_mode, self.args.failure_prob, self.rng)
        obs, reward, done, info = self.env.step(raw_action)
        distance_change, goal_changed = progress_delta(
            self.last_raw_obs,
            obs,
            getattr(self.args, "progress_clip", 0.03),
        )
        progress_reward = getattr(self.args, "progress_reward_scale", 0.0) * distance_change
        current_distance = goal_distance(obs)
        distance_reward, near_target_action_cost = precision_shaping(
            current_distance,
            raw_action,
            getattr(self.args, "distance_reward_scale", 0.0),
            getattr(self.args, "near_target_action_penalty", 0.0),
            getattr(self.args, "near_target_threshold", 0.12),
        )
        success = float(info.get("is_success", 0.0))
        danger_center = resolve_danger_center(obs, self.args.danger_zone)
        unsafe_violation = 0.0
        if danger_center is not None and isinstance(obs, dict):
            tool_pos = np.asarray(obs["observation"], dtype=np.float32).ravel()[:3]
            unsafe_violation = float(np.linalg.norm(tool_pos - danger_center) <= self.args.danger_radius)
        shaped_reward = (
            float(reward)
            + self.args.success_bonus * success
            - self.args.danger_penalty * unsafe_violation
            + progress_reward
            + distance_reward
            - near_target_action_cost
        )
        done = bool(done or success >= 1.0 or unsafe_violation > 0 or self.steps >= self.args.max_episode_steps)
        info = dict(info)
        info.update(
            {
                "raw_reward": float(reward),
                "shaped_reward": shaped_reward,
                "unsafe_violation": unsafe_violation,
                "goal_distance": current_distance,
                "distance_progress": distance_change,
                "progress_reward": progress_reward,
                "distance_reward": distance_reward,
                "near_target_action_cost": near_target_action_cost,
                "goal_changed": goal_changed,
                "visual_corruption_magnitude": self.last_visual_corruption_magnitude,
                "visual_corruption_applied": self.last_visual_corruption_applied,
                "failure_mode": self.args.failure_mode,
                "observation_mode": self.args.observation_mode,
            }
        )
        self.last_raw_obs = obs
        rendered = self._render_for_obs() if self.args.observation_mode in {"render_pseudo_vision", "render_proprio_vision"} else None
        flattened = self._flatten(obs, rendered)
        info["visual_corruption_magnitude"] = self.last_visual_corruption_magnitude
        info["visual_corruption_applied"] = self.last_visual_corruption_applied
        info["visual_frame_updated"] = self.visual_frame_updated
        info["visual_frame_age"] = self.visual_frame_age
        return flattened, shaped_reward, done, info

    def render(self, mode="rgb_array"):
        return self.env.render(mode=mode)

    def close(self):
        if hasattr(self.env, "close"):
            self.env.close()


def make_env(args: argparse.Namespace):
    configure_surrol_path(args.surrol_root)
    seed_global_randomness(args.seed)
    import gym
    import surrol.gym  # noqa: F401

    env = gym.make(args.task)
    env.seed(args.seed)
    return FailureAwareSurrolWrapper(env, args)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def run_training(args: argparse.Namespace) -> None:
    args.out_dir.mkdir(parents=True, exist_ok=True)
    env = make_env(args)
    obs = env.reset()
    action = env.action_space.sample()
    next_obs, reward, done, info = env.step(action)
    smoke = {
        "task": args.task,
        "seed": args.seed,
        "observation_mode": args.observation_mode,
        "failure_mode": args.failure_mode,
        "vision_corruption": getattr(args, "vision_corruption", "none"),
        "vision_stride": getattr(args, "vision_stride", 1),
        "proprio_dim": getattr(args, "proprio_dim", 7),
        "image_grid_size": getattr(args, "image_grid_size", 4),
        "image_feature_mode": getattr(args, "image_feature_mode", "stats_gray"),
        "progress_reward_scale": getattr(args, "progress_reward_scale", 0.0),
        "distance_reward_scale": getattr(args, "distance_reward_scale", 0.0),
        "near_target_action_penalty": getattr(args, "near_target_action_penalty", 0.0),
        "obs_shape": list(obs.shape),
        "next_obs_shape": list(next_obs.shape),
        "action_shape": list(env.action_space.shape),
        "reward": float(reward),
        "done": bool(done),
        "info_keys": sorted(info.keys()),
    }
    write_json(args.out_dir / "smoke_check.json", smoke)
    if args.check_only:
        print(f"smoke_json={args.out_dir / 'smoke_check.json'}")
        env.close()
        return

    try:
        import torch
        from stable_baselines3 import PPO
        from stable_baselines3.common.monitor import Monitor
        from stable_baselines3.common.utils import get_schedule_fn
    except ImportError as exc:
        write_json(
            args.out_dir / "dependency_blocked.json",
            {
                "blocked": True,
                "reason": "stable_baselines3/torch is not installed in the active SurRoL environment",
                "error": str(exc),
            },
        )
        raise

    torch.set_num_threads(max(1, int(getattr(args, "torch_num_threads", 1))))

    env = Monitor(env, filename=str(args.out_dir / "monitor.csv"))
    if args.init_model is not None:
        model = PPO.load(
            args.init_model,
            env=env,
            custom_objects={
                "observation_space": env.observation_space,
                "action_space": env.action_space,
            },
        )
        model.verbose = 1
        model.learning_rate = args.ppo_learning_rate
        model.lr_schedule = get_schedule_fn(args.ppo_learning_rate)
        model.clip_range = get_schedule_fn(args.ppo_clip_range)
        model.ent_coef = args.ppo_ent_coef
        for param_group in model.policy.optimizer.param_groups:
            param_group["lr"] = args.ppo_learning_rate
    else:
        model = PPO(
            "MlpPolicy",
            env,
            seed=args.seed,
            verbose=1,
            n_steps=256,
            batch_size=64,
            gamma=0.97,
            learning_rate=args.ppo_learning_rate,
            clip_range=args.ppo_clip_range,
            ent_coef=args.ppo_ent_coef,
            tensorboard_log=str(args.out_dir / "tb") if importlib.util.find_spec("tensorboard") is not None else None,
        )
    if args.freeze_log_std and hasattr(model.policy, "log_std"):
        model.policy.log_std.requires_grad_(False)
    model.learn(total_timesteps=args.total_timesteps, progress_bar=False)
    model.save(args.out_dir / "model")
    write_json(
        args.out_dir / "train_summary.json",
        {
            **smoke,
            "total_timesteps": args.total_timesteps,
            "init_model": None if args.init_model is None else str(args.init_model),
            "model": str(args.out_dir / "model.zip"),
            "torch_num_threads": getattr(args, "torch_num_threads", 1),
            "ppo_learning_rate": args.ppo_learning_rate,
            "ppo_clip_range": args.ppo_clip_range,
            "ppo_ent_coef": args.ppo_ent_coef,
            "freeze_log_std": args.freeze_log_std,
        },
    )
    print(f"saved_model={args.out_dir / 'model.zip'}")


def main() -> None:
    run_training(parse_args())


if __name__ == "__main__":
    main()
