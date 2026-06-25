from __future__ import annotations

from collections.abc import Callable

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


class RiskGatedTangentSafetyShieldAction(TangentSafetyShieldAction):
    """Gate tangent backup control with an interpretable timestep risk score.

    The default gate is deliberately simple and transparent: it raises risk
    from forbidden-zone clearance, force proxy, remaining budget, recent
    progress, normalized time, and action magnitude. A learned model can be
    passed as a callable that accepts the feature dict and returns a risk
    probability.
    """

    def __init__(
        self,
        env: gym.Env,
        risk_model: Callable[[dict[str, float]], float] | None = None,
        threshold: float = 0.5,
        safety_margin: float = 0.08,
        budget_floor: float = 0.25,
        stall_distance: float = 0.35,
        progress_window: int = 5,
    ):
        super().__init__(env)
        self.risk_model = risk_model
        self.threshold = float(threshold)
        self.safety_margin = float(safety_margin)
        self.budget_floor = float(budget_floor)
        self.stall_distance = float(stall_distance)
        self.progress_window = int(progress_window)

        self.risk_gate_activation_count = 0
        self.risk_gated_tangent_intervention_count = 0
        self.last_risk_score = 0.0
        self.last_risk_reasons = "low_risk"
        self.last_risk_gate_active = False
        self._distance_history: list[float] = []

    def reset(self, **kwargs):
        self.risk_gate_activation_count = 0
        self.risk_gated_tangent_intervention_count = 0
        self.last_risk_score = 0.0
        self.last_risk_reasons = "low_risk"
        self.last_risk_gate_active = False
        self._distance_history = []
        return super().reset(**kwargs)

    @staticmethod
    def _clip01(value: float) -> float:
        return float(np.clip(value, 0.0, 1.0))

    def _risk_features(self, clipped_action: np.ndarray) -> dict[str, float]:
        unwrapped = self.env.unwrapped
        distance_to_goal = float(np.linalg.norm(unwrapped.target_xy - unwrapped.tool_xy))
        previous_distance = (
            self._distance_history[-self.progress_window]
            if len(self._distance_history) >= self.progress_window
            else distance_to_goal
        )
        progress_5 = float(previous_distance - distance_to_goal)

        forbidden_center_distance = float(np.linalg.norm(unwrapped.tool_xy - unwrapped.forbidden_xy))
        clearance = float(unwrapped.config.forbidden_radius + unwrapped.config.tool_radius)
        distance_to_forbidden = forbidden_center_distance - clearance
        proposed_xy = unwrapped.tool_xy + clipped_action * unwrapped.config.action_scale
        proposed_distance_to_forbidden = float(np.linalg.norm(proposed_xy - unwrapped.forbidden_xy) - clearance)
        proposed_outside_workspace = float(np.any(np.abs(proposed_xy) > 0.98))
        force_proxy = float(unwrapped._force_proxy())
        remaining_budget = float(unwrapped.safety_budget - unwrapped.cumulative_cost)
        normalized_time = float(unwrapped.step_count / max(unwrapped.config.max_steps, 1))
        action_norm = float(np.linalg.norm(clipped_action))

        self._distance_history.append(distance_to_goal)
        return {
            "distance_to_goal": distance_to_goal,
            "distance_to_forbidden": distance_to_forbidden,
            "proposed_distance_to_forbidden": proposed_distance_to_forbidden,
            "proposed_outside_workspace": proposed_outside_workspace,
            "force_proxy": force_proxy,
            "remaining_budget": remaining_budget,
            "normalized_time": normalized_time,
            "progress_5": progress_5,
            "action_norm": action_norm,
        }

    def _default_risk_score(self, features: dict[str, float]) -> tuple[float, str]:
        forbidden_score = self._clip01(1.0 - features["distance_to_forbidden"] / max(self.safety_margin, 1e-6))
        proposed_forbidden_score = self._clip01(
            1.0 - features["proposed_distance_to_forbidden"] / max(self.safety_margin, 1e-6)
        )
        closing_forbidden_score = self._clip01(
            (features["distance_to_forbidden"] - features["proposed_distance_to_forbidden"])
            / max(self.safety_margin, 1e-6)
        )
        force_score = self._clip01(features["force_proxy"] / max(self.env.unwrapped.config.max_force, 1e-6))
        budget_score = self._clip01((self.budget_floor - features["remaining_budget"]) / max(self.budget_floor, 1e-6))
        stalled = features["progress_5"] <= 0.0 and features["distance_to_goal"] >= self.stall_distance
        stall_score = 1.0 if stalled else 0.0
        late_stall_score = self._clip01(features["normalized_time"]) if stalled else 0.0
        action_score = self._clip01((features["action_norm"] - 0.85) / 0.55)

        weighted = (
            0.18 * forbidden_score
            + 0.34 * proposed_forbidden_score
            + 0.10 * closing_forbidden_score
            + 0.16 * force_score
            + 0.12 * budget_score
            + 0.06 * stall_score
            + 0.02 * late_stall_score
            + 0.02 * action_score
        )
        score = max(
            weighted,
            0.65 if features["proposed_distance_to_forbidden"] < self.safety_margin else 0.0,
            0.7 if features["proposed_outside_workspace"] > 0.0 else 0.0,
            forbidden_score if features["distance_to_forbidden"] <= 0.0 else 0.0,
        )

        reasons = []
        if features["distance_to_forbidden"] < self.safety_margin:
            reasons.append("near_forbidden")
        if features["proposed_distance_to_forbidden"] < self.safety_margin:
            reasons.append("proposed_near_forbidden")
        if features["proposed_outside_workspace"] > 0.0:
            reasons.append("proposed_outside_workspace")
        if force_score >= 0.75:
            reasons.append("force_proxy_high")
        if features["remaining_budget"] < self.budget_floor:
            reasons.append("remaining_budget_low")
        if stalled:
            reasons.append("progress_stalled")
        if action_score >= 0.5:
            reasons.append("large_action")
        return self._clip01(score), ",".join(reasons) if reasons else "low_risk"

    def _score_risk(self, features: dict[str, float]) -> tuple[float, str]:
        if self.risk_model is None:
            return self._default_risk_score(features)
        score = float(self.risk_model(features))
        return self._clip01(score), "learned_risk_model"

    def action(self, action):
        action = np.asarray(action, dtype=np.float32)
        clipped = np.clip(action, self.action_space.low, self.action_space.high).astype(np.float32)
        features = self._risk_features(clipped)
        risk_score, reasons = self._score_risk(features)

        self.last_risk_score = risk_score
        self.last_risk_reasons = reasons
        self.last_risk_gate_active = risk_score >= self.threshold

        if not self.last_risk_gate_active:
            self.last_action_deviation = 0.0
            self.cumulative_action_deviation += self.last_action_deviation
            return clipped

        self.risk_gate_activation_count += 1
        previous_interventions = self.intervention_count
        executed = super().action(clipped)
        if self.intervention_count > previous_interventions:
            self.risk_gated_tangent_intervention_count += 1
        return executed

    def step(self, action):
        obs, reward, terminated, truncated, info = super().step(action)
        info["risk_score"] = self.last_risk_score
        info["risk_reasons"] = self.last_risk_reasons
        info["risk_gate_active"] = float(self.last_risk_gate_active)
        info["risk_gate_activations"] = self.risk_gate_activation_count
        info["risk_gated_tangent_interventions"] = self.risk_gated_tangent_intervention_count
        info["risk_gate_threshold"] = self.threshold
        return obs, reward, terminated, truncated, info


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
    if variant == "conditioned_risk_gated_tangent_shielded":
        return RiskGatedTangentSafetyShieldAction(env)
    if variant == "no_phase_budget":
        return DropObservationIndices(env, drop_indices=(12, 13))
    if variant == "no_phase_budget_shielded":
        return SafetyShieldAction(DropObservationIndices(env, drop_indices=(12, 13)))
    if variant == "no_phase_budget_tangent_shielded":
        return TangentSafetyShieldAction(DropObservationIndices(env, drop_indices=(12, 13)))
    if variant == "no_phase_budget_risk_gated_tangent_shielded":
        return RiskGatedTangentSafetyShieldAction(DropObservationIndices(env, drop_indices=(12, 13)))
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
    if variant == "conditioned_risk_gated_tangent_shielded":
        return RiskGatedTangentSafetyShieldAction(env)
    if variant == "no_phase_budget":
        return DropObservationIndices(env, drop_indices=(19, 20))
    if variant == "no_phase_budget_shielded":
        return SafetyShieldAction(DropObservationIndices(env, drop_indices=(19, 20)))
    if variant == "no_phase_budget_tangent_shielded":
        return TangentSafetyShieldAction(DropObservationIndices(env, drop_indices=(19, 20)))
    if variant == "no_phase_budget_risk_gated_tangent_shielded":
        return RiskGatedTangentSafetyShieldAction(DropObservationIndices(env, drop_indices=(19, 20)))
    if variant == "no_budget":
        return DropObservationIndices(env, drop_indices=(20,))
    raise ValueError(f"Unknown manipulation variant: {variant}")
