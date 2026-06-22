from __future__ import annotations

import gymnasium as gym
import numpy as np
from gymnasium import spaces


class DropObservationIndices(gym.ObservationWrapper):
    """Drop selected observation dimensions for baseline comparisons."""

    def __init__(self, env: gym.Env, drop_indices: tuple[int, ...]):
        super().__init__(env)
        if not isinstance(env.observation_space, spaces.Box):
            raise TypeError("DropObservationIndices requires a Box observation space.")

        self.drop_indices = tuple(sorted(drop_indices))
        keep_mask = np.ones(env.observation_space.shape[0], dtype=bool)
        keep_mask[list(self.drop_indices)] = False
        self.keep_indices = np.flatnonzero(keep_mask)

        self.observation_space = spaces.Box(
            low=env.observation_space.low[self.keep_indices],
            high=env.observation_space.high[self.keep_indices],
            dtype=env.observation_space.dtype,
        )

    def observation(self, observation):
        return np.asarray(observation, dtype=self.env.observation_space.dtype)[self.keep_indices]


class SafetyShieldAction(gym.ActionWrapper):
    """Simple backup controller that suppresses obviously unsafe tool motions."""

    def __init__(self, env: gym.Env):
        super().__init__(env)
        self.intervention_count = 0
        self.cumulative_action_deviation = 0.0
        self.last_action_deviation = 0.0

    def reset(self, **kwargs):
        self.intervention_count = 0
        self.cumulative_action_deviation = 0.0
        self.last_action_deviation = 0.0
        return self.env.reset(**kwargs)

    def action(self, action):
        unwrapped = self.env.unwrapped
        action = np.asarray(action, dtype=np.float32)
        clipped = np.clip(action, self.action_space.low, self.action_space.high)
        executed = clipped.astype(np.float32)
        proposed_xy = unwrapped.tool_xy + clipped * unwrapped.config.action_scale

        too_close_to_forbidden = (
            np.linalg.norm(proposed_xy - unwrapped.forbidden_xy)
            < unwrapped.config.forbidden_radius + unwrapped.config.tool_radius
        )
        outside_workspace = np.any(np.abs(proposed_xy) > 0.98)

        if too_close_to_forbidden or outside_workspace:
            self.intervention_count += 1
            direction_to_target = unwrapped.target_xy - unwrapped.tool_xy
            norm = np.linalg.norm(direction_to_target)
            if norm < 1e-6:
                executed = np.zeros_like(clipped, dtype=np.float32)
                self.last_action_deviation = float(np.linalg.norm(executed - clipped))
                self.cumulative_action_deviation += self.last_action_deviation
                return executed
            safe_action = (direction_to_target / norm).astype(np.float32)
            proposed_safe_xy = unwrapped.tool_xy + safe_action * unwrapped.config.action_scale
            if np.linalg.norm(proposed_safe_xy - unwrapped.forbidden_xy) < np.linalg.norm(
                proposed_xy - unwrapped.forbidden_xy
            ):
                executed = np.zeros_like(clipped, dtype=np.float32)
            else:
                executed = safe_action

        self.last_action_deviation = float(np.linalg.norm(executed - clipped))
        self.cumulative_action_deviation += self.last_action_deviation
        return executed.astype(np.float32)

    def step(self, action):
        obs, reward, terminated, truncated, info = super().step(action)
        info["shield_interventions"] = self.intervention_count
        info["last_action_deviation"] = self.last_action_deviation
        info["cumulative_action_deviation"] = self.cumulative_action_deviation
        info["mean_action_deviation"] = self.cumulative_action_deviation / max(self.env.unwrapped.step_count, 1)
        return obs, reward, terminated, truncated, info


class TangentSafetyShieldAction(SafetyShieldAction):
    """Backup controller that steers tangentially around forbidden regions."""

    @staticmethod
    def _orthogonal_unit(vector: np.ndarray) -> np.ndarray:
        basis = np.eye(vector.shape[0], dtype=np.float32)
        candidate = basis[int(np.argmin(np.abs(vector)))]
        orthogonal = candidate - np.dot(candidate, vector) * vector
        norm = np.linalg.norm(orthogonal)
        if norm < 1e-6:
            return np.zeros_like(vector, dtype=np.float32)
        return (orthogonal / norm).astype(np.float32)

    def action(self, action):
        unwrapped = self.env.unwrapped
        action = np.asarray(action, dtype=np.float32)
        clipped = np.clip(action, self.action_space.low, self.action_space.high)
        proposed_xy = unwrapped.tool_xy + clipped * unwrapped.config.action_scale

        clearance = unwrapped.config.forbidden_radius + unwrapped.config.tool_radius
        radial = unwrapped.tool_xy - unwrapped.forbidden_xy
        radial_norm = np.linalg.norm(radial)
        proposed_forbidden_dist = np.linalg.norm(proposed_xy - unwrapped.forbidden_xy)
        too_close_to_forbidden = proposed_forbidden_dist < clearance
        outside_workspace = np.any(np.abs(proposed_xy) > 0.98)

        if not (too_close_to_forbidden or outside_workspace):
            self.last_action_deviation = 0.0
            self.cumulative_action_deviation += self.last_action_deviation
            return clipped.astype(np.float32)

        self.intervention_count += 1
        to_target = unwrapped.target_xy - unwrapped.tool_xy
        target_norm = np.linalg.norm(to_target)
        if target_norm < 1e-6:
            executed = np.zeros_like(clipped, dtype=np.float32)
            self.last_action_deviation = float(np.linalg.norm(executed - clipped))
            self.cumulative_action_deviation += self.last_action_deviation
            return executed

        target_dir = to_target / target_norm
        if radial_norm < 1e-6:
            radial_dir = -target_dir
        else:
            radial_dir = radial / radial_norm

        tangent_component = clipped - np.dot(clipped, radial_dir) * radial_dir
        if np.linalg.norm(tangent_component) < 1e-6:
            tangent_a = self._orthogonal_unit(radial_dir)
            tangent_b = -tangent_a
            tangent_component = tangent_a if np.dot(tangent_a, target_dir) >= np.dot(tangent_b, target_dir) else tangent_b

        target_tangent = target_dir - np.dot(target_dir, radial_dir) * radial_dir
        if np.linalg.norm(target_tangent) < 1e-6:
            target_tangent = tangent_component

        safe_action = 0.55 * tangent_component + 0.35 * target_tangent + 0.25 * radial_dir
        if outside_workspace:
            workspace_push = np.zeros_like(safe_action)
            near_boundary = np.abs(unwrapped.tool_xy) > 0.9
            workspace_push[near_boundary] = -np.sign(unwrapped.tool_xy[near_boundary])
            safe_action = safe_action + 0.6 * workspace_push

        safe_norm = np.linalg.norm(safe_action)
        if safe_norm < 1e-6:
            executed = np.zeros_like(clipped, dtype=np.float32)
            self.last_action_deviation = float(np.linalg.norm(executed - clipped))
            self.cumulative_action_deviation += self.last_action_deviation
            return executed
        safe_action = safe_action / safe_norm

        proposed_safe_xy = unwrapped.tool_xy + safe_action * unwrapped.config.action_scale
        if np.any(np.abs(proposed_safe_xy) > 1.0):
            executed = np.zeros_like(clipped, dtype=np.float32)
        else:
            executed = safe_action.astype(np.float32)
        self.last_action_deviation = float(np.linalg.norm(executed - clipped))
        self.cumulative_action_deviation += self.last_action_deviation
        return executed.astype(np.float32)


def make_tool_navigation_env(
    variant: str = "conditioned", render_mode: str | None = None, config_preset: str = "default"
) -> gym.Env:
    from constraint_surgical_rl.envs.presets import get_config_preset
    from constraint_surgical_rl.envs.tool_navigation import ConstrainedToolNavigationEnv

    env = ConstrainedToolNavigationEnv(config=get_config_preset(config_preset), render_mode=render_mode)
    if variant == "conditioned":
        return env
    if variant == "conditioned_shielded":
        return SafetyShieldAction(env)
    if variant == "conditioned_tangent_shielded":
        return TangentSafetyShieldAction(env)
    if variant == "no_phase_budget":
        return DropObservationIndices(env, drop_indices=(12, 13))
    if variant == "no_phase_budget_shielded":
        return SafetyShieldAction(DropObservationIndices(env, drop_indices=(12, 13)))
    if variant == "no_phase_budget_tangent_shielded":
        return TangentSafetyShieldAction(DropObservationIndices(env, drop_indices=(12, 13)))
    if variant == "no_budget":
        return DropObservationIndices(env, drop_indices=(13,))
    raise ValueError(f"Unknown environment variant: {variant}")


def make_tool_manipulation_env(variant: str = "conditioned", render_mode: str | None = None) -> gym.Env:
    from constraint_surgical_rl.envs.tool_manipulation import ConstrainedToolManipulationEnv

    env = ConstrainedToolManipulationEnv(render_mode=render_mode)
    if variant == "conditioned":
        return env
    if variant == "conditioned_shielded":
        return SafetyShieldAction(env)
    if variant == "conditioned_tangent_shielded":
        return TangentSafetyShieldAction(env)
    if variant == "no_phase_budget":
        return DropObservationIndices(env, drop_indices=(19, 20))
    if variant == "no_phase_budget_shielded":
        return SafetyShieldAction(DropObservationIndices(env, drop_indices=(19, 20)))
    if variant == "no_phase_budget_tangent_shielded":
        return TangentSafetyShieldAction(DropObservationIndices(env, drop_indices=(19, 20)))
    if variant == "no_budget":
        return DropObservationIndices(env, drop_indices=(20,))
    raise ValueError(f"Unknown manipulation variant: {variant}")
