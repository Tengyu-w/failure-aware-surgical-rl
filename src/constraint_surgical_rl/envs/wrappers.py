from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

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


class MechanismRoutedTangentSafetyShieldAction(RiskGatedTangentSafetyShieldAction):
    """Mechanism-separated hierarchical reliability router.

    Stage 1 handles irreversible boundary/safety risks with tangent backup.
    Stage 2 records residual mechanism risks with a reserved review budget, but
    does not automatically apply tangent correction unless Stage 1 is active.
    """

    def __init__(
        self,
        env: gym.Env,
        boundary_threshold: float = 0.55,
        residual_threshold: float = 0.60,
        residual_budget_reserve: float = 0.20,
        expected_activation_budget: float = 0.50,
        **kwargs,
    ):
        super().__init__(env, threshold=boundary_threshold, **kwargs)
        self.boundary_threshold = float(boundary_threshold)
        self.residual_threshold = float(residual_threshold)
        self.residual_budget_reserve = float(np.clip(residual_budget_reserve, 0.0, 1.0))
        self.expected_activation_budget = float(np.clip(expected_activation_budget, 0.01, 1.0))
        self.stage1_boundary_activations = 0
        self.stage2_residual_activations = 0
        self.mechanism_router_activations = 0
        self.last_boundary_score = 0.0
        self.last_residual_score = 0.0
        self.last_mechanism_route = "auto_execute"
        self.last_mechanism_reasons = "low_risk"

    def reset(self, **kwargs):
        self.stage1_boundary_activations = 0
        self.stage2_residual_activations = 0
        self.mechanism_router_activations = 0
        self.last_boundary_score = 0.0
        self.last_residual_score = 0.0
        self.last_mechanism_route = "auto_execute"
        self.last_mechanism_reasons = "low_risk"
        return super().reset(**kwargs)

    def _mechanism_scores(self, features: dict[str, float]) -> tuple[float, float, str, str]:
        current_boundary = self._clip01(1.0 - features["distance_to_forbidden"] / max(self.safety_margin, 1e-6))
        proposed_boundary = self._clip01(
            1.0 - features["proposed_distance_to_forbidden"] / max(self.safety_margin, 1e-6)
        )
        closing_boundary = self._clip01(
            (features["distance_to_forbidden"] - features["proposed_distance_to_forbidden"])
            / max(self.safety_margin, 1e-6)
        )
        force_score = self._clip01(features["force_proxy"] / max(self.env.unwrapped.config.max_force, 1e-6))
        workspace_score = 1.0 if features["proposed_outside_workspace"] > 0.0 else 0.0
        boundary_score = max(
            0.42 * proposed_boundary + 0.26 * current_boundary + 0.16 * closing_boundary + 0.16 * force_score,
            0.92 if features["proposed_distance_to_forbidden"] <= 0.0 else 0.0,
            0.86 if workspace_score else 0.0,
            0.82 if features["distance_to_forbidden"] <= 0.0 else 0.0,
        )

        budget_score = self._clip01((self.budget_floor - features["remaining_budget"]) / max(self.budget_floor, 1e-6))
        stalled = features["progress_5"] <= 0.0 and features["distance_to_goal"] >= self.stall_distance
        stall_score = 1.0 if stalled else 0.0
        late_score = self._clip01(features["normalized_time"]) if stalled else 0.0
        action_score = self._clip01((features["action_norm"] - 0.85) / 0.55)
        residual_score = self._clip01(
            0.38 * budget_score + 0.34 * stall_score + 0.18 * late_score + 0.10 * action_score
        )

        reasons = []
        route = "auto_execute"
        if boundary_score >= self.boundary_threshold:
            route = "stage1_boundary_tangent_backup"
            if proposed_boundary >= 0.5:
                reasons.append("proposed_boundary_risk")
            if current_boundary >= 0.5:
                reasons.append("current_clearance_low")
            if closing_boundary >= 0.5:
                reasons.append("moving_toward_boundary")
            if force_score >= 0.5:
                reasons.append("force_proxy")
            if workspace_score:
                reasons.append("workspace_boundary")
        elif residual_score >= self.residual_threshold:
            if budget_score >= 0.5:
                route = "stage2_budget_review"
                reasons.append("remaining_budget_low")
            elif stalled:
                route = "stage2_stagnation_review"
                reasons.append("progress_stalled")
            else:
                route = "stage2_action_review"
                reasons.append("large_or_late_action")

        return self._clip01(boundary_score), residual_score, route, ",".join(reasons) if reasons else "low_risk"

    def _residual_budget_available(self) -> bool:
        max_steps = max(self.env.unwrapped.config.max_steps, 1)
        reserved_steps = int(np.ceil(max_steps * self.expected_activation_budget * self.residual_budget_reserve))
        return self.stage2_residual_activations < max(reserved_steps, 1)

    def action(self, action):
        action = np.asarray(action, dtype=np.float32)
        clipped = np.clip(action, self.action_space.low, self.action_space.high).astype(np.float32)
        features = self._risk_features(clipped)
        boundary_score, residual_score, route, reasons = self._mechanism_scores(features)

        stage1_active = route == "stage1_boundary_tangent_backup"
        stage2_requested = route.startswith("stage2_")
        stage2_active = bool(stage2_requested and self._residual_budget_available())
        if stage2_requested and not stage2_active:
            route = "auto_execute_residual_budget_exhausted"
            reasons = "residual_budget_exhausted"

        self.last_boundary_score = boundary_score
        self.last_residual_score = residual_score
        self.last_mechanism_route = route
        self.last_mechanism_reasons = reasons
        self.last_risk_score = max(boundary_score, residual_score)
        self.last_risk_reasons = reasons
        self.last_risk_gate_active = bool(stage1_active or stage2_active)

        if stage1_active:
            self.stage1_boundary_activations += 1
            self.mechanism_router_activations += 1
            previous_interventions = self.intervention_count
            executed = TangentSafetyShieldAction.action(self, clipped)
            if self.intervention_count > previous_interventions:
                self.risk_gated_tangent_intervention_count += 1
            return executed

        if stage2_active:
            self.stage2_residual_activations += 1
            self.mechanism_router_activations += 1

        self.last_action_deviation = 0.0
        self.cumulative_action_deviation += self.last_action_deviation
        return clipped

    def step(self, action):
        obs, reward, terminated, truncated, info = super().step(action)
        info["mechanism_boundary_score"] = self.last_boundary_score
        info["mechanism_residual_score"] = self.last_residual_score
        info["mechanism_route"] = self.last_mechanism_route
        info["mechanism_reasons"] = self.last_mechanism_reasons
        info["stage1_boundary_activations"] = self.stage1_boundary_activations
        info["stage2_residual_activations"] = self.stage2_residual_activations
        info["mechanism_router_activations"] = self.mechanism_router_activations
        info["residual_budget_reserve"] = self.residual_budget_reserve
        return obs, reward, terminated, truncated, info


class EmbeddingRiskScorer:
    """Small NumPy KNN risk scorer over standardized PCA feature embeddings."""

    FEATURE_NAMES = (
        "distance_to_goal",
        "distance_to_forbidden",
        "force_proxy",
        "remaining_budget",
        "normalized_time",
        "progress_5",
        "action_norm",
    )

    def __init__(
        self,
        positive_embedding: np.ndarray,
        negative_embedding: np.ndarray,
        mean: np.ndarray,
        scale: np.ndarray,
        components: np.ndarray,
        k: int = 7,
        temperature: float = 1.0,
        ood_radius: float | None = None,
    ):
        self.positive_embedding = np.asarray(positive_embedding, dtype=np.float32)
        self.negative_embedding = np.asarray(negative_embedding, dtype=np.float32)
        self.mean = np.asarray(mean, dtype=np.float32)
        self.scale = np.asarray(scale, dtype=np.float32)
        self.components = np.asarray(components, dtype=np.float32)
        self.k = int(k)
        self.temperature = float(temperature)
        self.ood_radius = float(ood_radius) if ood_radius is not None else self._default_ood_radius()

    @classmethod
    def from_csv(
        cls,
        dataset_path: str | Path,
        source_kind: str = "synthetic_navigation",
        pca_dim: int = 4,
        k: int = 7,
    ) -> "EmbeddingRiskScorer":
        import csv

        rows: list[list[float]] = []
        labels: list[int] = []
        with Path(dataset_path).open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if source_kind and row.get("source_kind") != source_kind:
                    continue
                try:
                    values = [float(row[name]) for name in cls.FEATURE_NAMES]
                    label = int(float(row["risk_label"]))
                except (KeyError, TypeError, ValueError):
                    continue
                if np.all(np.isfinite(values)):
                    rows.append(values)
                    labels.append(label)

        if not rows:
            raise ValueError(f"No usable rows found in risk dataset: {dataset_path}")

        x = np.asarray(rows, dtype=np.float32)
        y = np.asarray(labels, dtype=np.int32)
        if not np.any(y == 1) or not np.any(y == 0):
            raise ValueError("Embedding risk scorer needs both risk and non-risk examples.")

        mean = x.mean(axis=0)
        scale = x.std(axis=0)
        scale[scale < 1e-6] = 1.0
        z = (x - mean) / scale

        _, _, vt = np.linalg.svd(z, full_matrices=False)
        components = vt[: min(int(pca_dim), vt.shape[0])]
        embedding = z @ components.T
        return cls(
            positive_embedding=embedding[y == 1],
            negative_embedding=embedding[y == 0],
            mean=mean,
            scale=scale,
            components=components,
            k=k,
        )

    def _default_ood_radius(self) -> float:
        combined = np.concatenate([self.positive_embedding, self.negative_embedding], axis=0)
        if combined.shape[0] < 2:
            return 3.0
        center = combined.mean(axis=0)
        distances = np.linalg.norm(combined - center, axis=1)
        return float(max(np.quantile(distances, 0.90), 1.0))

    def _embed(self, features: dict[str, float]) -> np.ndarray:
        x = np.asarray([float(features[name]) for name in self.FEATURE_NAMES], dtype=np.float32)
        z = (x - self.mean) / self.scale
        return z @ self.components.T

    def _knn_distance(self, embedding: np.ndarray, reference: np.ndarray) -> float:
        distances = np.linalg.norm(reference - embedding[None, :], axis=1)
        k = min(self.k, distances.shape[0])
        return float(np.partition(distances, k - 1)[:k].mean())

    def score(self, features: dict[str, float]) -> float:
        embedding = self._embed(features)
        positive_distance = self._knn_distance(embedding, self.positive_embedding)
        negative_distance = self._knn_distance(embedding, self.negative_embedding)
        relative_risk = negative_distance / max(positive_distance + negative_distance, 1e-6)

        nearest_distance = min(positive_distance, negative_distance)
        ood_risk = np.clip((nearest_distance / max(self.ood_radius, 1e-6) - 0.75) / 0.75, 0.0, 1.0)
        return float(np.clip(0.85 * relative_risk + 0.15 * ood_risk, 0.0, 1.0))


class EmbeddingRiskPenaltyReward(gym.Wrapper):
    """Turn embedding/KNN instability analysis into a reward penalty."""

    def __init__(
        self,
        env: gym.Env,
        scorer: EmbeddingRiskScorer,
        penalty_scale: float = 0.75,
        risk_threshold: float = 0.55,
        progress_window: int = 5,
    ):
        super().__init__(env)
        self.scorer = scorer
        self.penalty_scale = float(penalty_scale)
        self.risk_threshold = float(risk_threshold)
        self.progress_window = int(progress_window)
        self._distance_history: list[float] = []
        self.last_embedding_risk_score = 0.0
        self.cumulative_embedding_risk = 0.0
        self.max_embedding_risk = 0.0

    def reset(self, **kwargs):
        self._distance_history = []
        self.last_embedding_risk_score = 0.0
        self.cumulative_embedding_risk = 0.0
        self.max_embedding_risk = 0.0
        return self.env.reset(**kwargs)

    def _features(self, action: np.ndarray, info: dict) -> dict[str, float]:
        unwrapped = self.env.unwrapped
        distance_to_goal = float(info.get("distance_to_goal", np.linalg.norm(unwrapped.target_xy - unwrapped.tool_xy)))
        previous_distance = (
            self._distance_history[-self.progress_window]
            if len(self._distance_history) >= self.progress_window
            else distance_to_goal
        )
        progress_5 = float(previous_distance - distance_to_goal)
        self._distance_history.append(distance_to_goal)

        clearance = float(unwrapped.config.forbidden_radius + unwrapped.config.tool_radius)
        distance_to_forbidden = float(np.linalg.norm(unwrapped.tool_xy - unwrapped.forbidden_xy) - clearance)
        normalized_time = float(unwrapped.step_count / max(unwrapped.config.max_steps, 1))
        return {
            "distance_to_goal": distance_to_goal,
            "distance_to_forbidden": distance_to_forbidden,
            "force_proxy": float(info.get("force_proxy", 0.0)),
            "remaining_budget": float(info.get("remaining_budget", 0.0)),
            "normalized_time": normalized_time,
            "progress_5": progress_5,
            "action_norm": float(np.linalg.norm(action)),
        }

    def step(self, action):
        obs, reward, terminated, truncated, info = self.env.step(action)
        features = self._features(np.asarray(action, dtype=np.float32), info)
        risk_score = self.scorer.score(features)
        active_risk = float(np.clip((risk_score - self.risk_threshold) / max(1.0 - self.risk_threshold, 1e-6), 0.0, 1.0))
        penalty = self.penalty_scale * active_risk
        shaped_reward = float(reward - penalty)

        self.last_embedding_risk_score = risk_score
        self.cumulative_embedding_risk += risk_score
        self.max_embedding_risk = max(self.max_embedding_risk, risk_score)

        steps = max(self.env.unwrapped.step_count, 1)
        info["embedding_risk_score"] = risk_score
        info["embedding_risk_active_score"] = active_risk
        info["embedding_risk_penalty"] = penalty
        info["embedding_risk_threshold"] = self.risk_threshold
        info["mean_embedding_risk"] = self.cumulative_embedding_risk / steps
        info["max_embedding_risk"] = self.max_embedding_risk
        return obs, shaped_reward, terminated, truncated, info


class EmbeddingRiskCurriculumReset(gym.Wrapper):
    """Use embedding/KNN risk to sample hard-negative reset states."""

    def __init__(
        self,
        env: gym.Env,
        scorer: EmbeddingRiskScorer,
        probability: float = 0.35,
        candidate_count: int = 8,
        min_budget_fraction: float = 0.45,
    ):
        super().__init__(env)
        self.scorer = scorer
        self.probability = float(np.clip(probability, 0.0, 1.0))
        self.candidate_count = max(1, int(candidate_count))
        self.min_budget_fraction = float(np.clip(min_budget_fraction, 0.05, 1.0))
        self.last_curriculum_active = 0.0
        self.last_curriculum_score = 0.0

    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        self.last_curriculum_active = 0.0
        self.last_curriculum_score = self._score_current(action_norm=0.0)

        rng = self.env.unwrapped.np_random
        if rng.random() >= self.probability:
            info["embedding_curriculum_active"] = 0.0
            info["embedding_curriculum_score"] = self.last_curriculum_score
            return obs, info

        best_state = self._snapshot()
        best_score = self.last_curriculum_score
        for _ in range(self.candidate_count):
            self._sample_hard_negative_candidate()
            score = self._score_current(action_norm=0.0)
            if score > best_score:
                best_score = score
                best_state = self._snapshot()

        self._restore(best_state)
        self.last_curriculum_active = 1.0
        self.last_curriculum_score = best_score
        info = self.env.unwrapped._info()
        info["embedding_curriculum_active"] = 1.0
        info["embedding_curriculum_score"] = best_score
        return self.env.unwrapped._obs(), info

    def step(self, action):
        obs, reward, terminated, truncated, info = self.env.step(action)
        info["embedding_curriculum_active"] = self.last_curriculum_active
        info["embedding_curriculum_score"] = self.last_curriculum_score
        return obs, reward, terminated, truncated, info

    def _snapshot(self) -> dict[str, np.ndarray | float | int]:
        unwrapped = self.env.unwrapped
        return {
            "tool_xy": unwrapped.tool_xy.copy(),
            "target_xy": unwrapped.target_xy.copy(),
            "forbidden_xy": unwrapped.forbidden_xy.copy(),
            "step_count": int(unwrapped.step_count),
            "safety_budget": float(unwrapped.safety_budget),
            "cumulative_cost": float(unwrapped.cumulative_cost),
        }

    def _restore(self, state: dict[str, np.ndarray | float | int]) -> None:
        unwrapped = self.env.unwrapped
        unwrapped.tool_xy = np.asarray(state["tool_xy"], dtype=np.float32).copy()
        unwrapped.target_xy = np.asarray(state["target_xy"], dtype=np.float32).copy()
        unwrapped.forbidden_xy = np.asarray(state["forbidden_xy"], dtype=np.float32).copy()
        unwrapped.step_count = int(state["step_count"])
        unwrapped.safety_budget = float(state["safety_budget"])
        unwrapped.cumulative_cost = float(state["cumulative_cost"])

    def _sample_hard_negative_candidate(self) -> None:
        unwrapped = self.env.unwrapped
        rng = unwrapped.np_random
        cfg = unwrapped.config
        clearance = cfg.forbidden_radius + cfg.tool_radius
        direction = self._random_unit_vector(rng, cfg.workspace_dim)

        if rng.random() < 0.55:
            near_distance = clearance + float(rng.uniform(0.0, 0.09))
            forbidden = unwrapped.tool_xy + direction * near_distance
        else:
            path = unwrapped.target_xy - unwrapped.tool_xy
            path_norm = float(np.linalg.norm(path))
            if path_norm < 1e-6:
                path_direction = direction
            else:
                path_direction = path / path_norm
            alpha = float(rng.uniform(0.20, 0.72))
            perpendicular = self._perpendicular_unit_vector(rng, path_direction)
            lateral_offset = float(rng.uniform(-0.06, 0.06))
            forbidden = unwrapped.tool_xy + alpha * path + perpendicular * lateral_offset

        unwrapped.forbidden_xy = np.clip(forbidden, -0.85, 0.85).astype(np.float32)
        max_budget = max(cfg.safety_budget_low, cfg.safety_budget_high * self.min_budget_fraction)
        unwrapped.safety_budget = float(rng.uniform(cfg.safety_budget_low, max_budget))
        unwrapped.cumulative_cost = 0.0
        unwrapped.step_count = 0

    def _score_current(self, action_norm: float) -> float:
        unwrapped = self.env.unwrapped
        clearance = float(unwrapped.config.forbidden_radius + unwrapped.config.tool_radius)
        features = {
            "distance_to_goal": float(np.linalg.norm(unwrapped.target_xy - unwrapped.tool_xy)),
            "distance_to_forbidden": float(np.linalg.norm(unwrapped.tool_xy - unwrapped.forbidden_xy) - clearance),
            "force_proxy": float(unwrapped._force_proxy()),
            "remaining_budget": float(unwrapped.safety_budget - unwrapped.cumulative_cost),
            "normalized_time": float(unwrapped.step_count / max(unwrapped.config.max_steps, 1)),
            "progress_5": 0.0,
            "action_norm": float(action_norm),
        }
        return self.scorer.score(features)

    @staticmethod
    def _random_unit_vector(rng: np.random.Generator, dim: int) -> np.ndarray:
        vector = rng.normal(size=dim).astype(np.float32)
        norm = float(np.linalg.norm(vector))
        if norm < 1e-6:
            vector[0] = 1.0
            return vector
        return vector / norm

    @classmethod
    def _perpendicular_unit_vector(cls, rng: np.random.Generator, direction: np.ndarray) -> np.ndarray:
        vector = cls._random_unit_vector(rng, direction.shape[0])
        vector = vector - direction * float(np.dot(vector, direction))
        norm = float(np.linalg.norm(vector))
        if norm < 1e-6:
            return cls._random_unit_vector(rng, direction.shape[0])
        return vector / norm


def _default_risk_dataset_path() -> Path:
    return Path(__file__).resolve().parents[3] / "outputs" / "risk_dataset" / "risk_dataset.csv"


def make_embedding_risk_penalty_wrapper(
    env: gym.Env,
    dataset_path: str | Path | None = None,
    penalty_scale: float = 0.75,
    risk_threshold: float = 0.55,
    scorer: EmbeddingRiskScorer | None = None,
) -> EmbeddingRiskPenaltyReward:
    path = Path(dataset_path) if dataset_path is not None else _default_risk_dataset_path()
    scorer = scorer or EmbeddingRiskScorer.from_csv(path)
    return EmbeddingRiskPenaltyReward(env, scorer=scorer, penalty_scale=penalty_scale, risk_threshold=risk_threshold)


def make_embedding_risk_curriculum_wrapper(
    env: gym.Env,
    dataset_path: str | Path | None = None,
    penalty_scale: float = 0.75,
    risk_threshold: float = 0.55,
    curriculum_probability: float = 0.35,
    curriculum_candidates: int = 8,
) -> EmbeddingRiskCurriculumReset:
    path = Path(dataset_path) if dataset_path is not None else _default_risk_dataset_path()
    scorer = EmbeddingRiskScorer.from_csv(path)
    penalty_env = make_embedding_risk_penalty_wrapper(
        env,
        dataset_path=path,
        penalty_scale=penalty_scale,
        risk_threshold=risk_threshold,
        scorer=scorer,
    )
    return EmbeddingRiskCurriculumReset(
        penalty_env,
        scorer=scorer,
        probability=curriculum_probability,
        candidate_count=curriculum_candidates,
    )


def make_tool_navigation_env(
    variant: str = "conditioned",
    render_mode: str | None = None,
    config_preset: str = "default",
    embedding_risk_dataset: str | Path | None = None,
    embedding_risk_penalty_scale: float = 0.75,
    embedding_risk_threshold: float = 0.55,
    embedding_risk_curriculum_probability: float = 0.35,
    embedding_risk_curriculum_candidates: int = 8,
) -> gym.Env:
    from constraint_surgical_rl.envs.presets import get_config_preset
    from constraint_surgical_rl.envs.tool_navigation import ConstrainedToolNavigationEnv

    env = ConstrainedToolNavigationEnv(config=get_config_preset(config_preset), render_mode=render_mode)
    if variant == "conditioned":
        return env
    if variant == "conditioned_embedding_risk_penalty":
        return make_embedding_risk_penalty_wrapper(
            env,
            embedding_risk_dataset,
            embedding_risk_penalty_scale,
            embedding_risk_threshold,
        )
    if variant == "conditioned_embedding_risk_curriculum":
        return make_embedding_risk_curriculum_wrapper(
            env,
            embedding_risk_dataset,
            embedding_risk_penalty_scale,
            embedding_risk_threshold,
            embedding_risk_curriculum_probability,
            embedding_risk_curriculum_candidates,
        )
    if variant == "conditioned_shielded":
        return SafetyShieldAction(env)
    if variant == "conditioned_tangent_shielded":
        return TangentSafetyShieldAction(env)
    if variant == "conditioned_risk_gated_tangent_shielded":
        return RiskGatedTangentSafetyShieldAction(env)
    if variant == "conditioned_mechanism_routed_tangent_shielded":
        return MechanismRoutedTangentSafetyShieldAction(env)
    if variant == "no_phase_budget":
        return DropObservationIndices(env, drop_indices=(12, 13))
    if variant == "no_phase_budget_shielded":
        return SafetyShieldAction(DropObservationIndices(env, drop_indices=(12, 13)))
    if variant == "no_phase_budget_tangent_shielded":
        return TangentSafetyShieldAction(DropObservationIndices(env, drop_indices=(12, 13)))
    if variant == "no_phase_budget_risk_gated_tangent_shielded":
        return RiskGatedTangentSafetyShieldAction(DropObservationIndices(env, drop_indices=(12, 13)))
    if variant == "no_phase_budget_mechanism_routed_tangent_shielded":
        return MechanismRoutedTangentSafetyShieldAction(DropObservationIndices(env, drop_indices=(12, 13)))
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
