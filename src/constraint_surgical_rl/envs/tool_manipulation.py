from __future__ import annotations

from dataclasses import dataclass

import gymnasium as gym
import numpy as np
from gymnasium import spaces


@dataclass(frozen=True)
class ToolManipulationConfig:
    max_steps: int = 280
    action_scale: float = 0.04
    contact_radius: float = 0.10
    object_radius: float = 0.035
    goal_radius: float = 0.10
    tool_radius: float = 0.025
    forbidden_radius: float = 0.10
    max_force: float = 1.0
    dense_tool_weight: float = 0.45
    dense_object_weight: float = 1.25
    success_bonus: float = 12.0
    violation_penalty: float = 4.0
    force_penalty: float = 0.8
    motion_penalty: float = 0.04
    contact_push_gain: float = 1.0
    safety_budget_low: float = 3.0
    safety_budget_high: float = 4.0


class ConstrainedToolManipulationEnv(gym.Env):
    """3D multi-phase surgical-proxy manipulation task.

    The tool must approach an object, push it into a target zone, then retract
    to a safe retreat point while avoiding a forbidden volume.
    """

    metadata = {"render_modes": ["rgb_array"], "render_fps": 20}

    def __init__(self, config: ToolManipulationConfig | None = None, render_mode: str | None = None):
        super().__init__()
        self.config = config or ToolManipulationConfig()
        self.render_mode = render_mode
        self.workspace_dim = 3

        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(3,), dtype=np.float32)
        # tool_xyz, object_xyz, goal_xyz, forbidden_xyz, retract_xyz,
        # tool_object_distance, object_goal_distance, force_proxy,
        # normalized_time, task_phase, remaining_safety_budget
        coord_low = [-1.0] * 15
        coord_high = [1.0] * 15
        self.observation_space = spaces.Box(
            low=np.array([*coord_low, 0.0, 0.0, 0.0, 0.0, 0.0, -500.0], dtype=np.float32),
            high=np.array([*coord_high, 3.5, 3.5, 8.0, 1.0, 2.0, 5.0], dtype=np.float32),
            dtype=np.float32,
        )

        self.np_random: np.random.Generator
        self.tool_xy = np.zeros(3, dtype=np.float32)
        self.object_xy = np.zeros(3, dtype=np.float32)
        self.goal_xy = np.zeros(3, dtype=np.float32)
        self.target_xy = np.zeros(3, dtype=np.float32)
        self.retract_xy = np.zeros(3, dtype=np.float32)
        self.forbidden_xy = np.zeros(3, dtype=np.float32)
        self.step_count = 0
        self.safety_budget = 0.0
        self.cumulative_cost = 0.0
        self.object_delivered = False

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        self.step_count = 0
        self.cumulative_cost = 0.0
        self.object_delivered = False

        self.tool_xy = self.np_random.uniform(-0.65, -0.40, size=3).astype(np.float32)
        self.object_xy = self.np_random.uniform(-0.08, 0.08, size=3).astype(np.float32)
        self.goal_xy = self.np_random.uniform(0.25, 0.45, size=3).astype(np.float32)
        self.retract_xy = self.np_random.uniform(-0.75, -0.55, size=3).astype(np.float32)
        self.forbidden_xy = np.array(
            [
                self.np_random.uniform(0.10, 0.35),
                self.np_random.uniform(-0.60, -0.35),
                self.np_random.uniform(0.10, 0.35),
            ],
            dtype=np.float32,
        )
        self.safety_budget = float(
            self.np_random.uniform(self.config.safety_budget_low, self.config.safety_budget_high)
        )
        self._update_target()
        return self._obs(), self._info()

    def step(self, action):
        action = np.asarray(action, dtype=np.float32)
        action = np.clip(action, -1.0, 1.0)
        delta = action * self.config.action_scale

        prev_tool = self.tool_xy.copy()
        prev_object = self.object_xy.copy()
        self.tool_xy = np.clip(self.tool_xy + delta, -1.0, 1.0)

        if self._tool_object_distance() <= self.config.contact_radius:
            goal_dir = self.goal_xy - self.object_xy
            goal_norm = np.linalg.norm(goal_dir)
            if goal_norm > 1e-8:
                goal_dir = goal_dir / goal_norm
                action_dir = action / max(np.linalg.norm(action), 1e-8)
                push_strength = max(0.0, float(np.dot(action_dir, goal_dir)))
                push_delta = goal_dir * self.config.action_scale * self.config.contact_push_gain * push_strength
            else:
                push_delta = np.zeros_like(delta)
            self.object_xy = np.clip(self.object_xy + push_delta, -1.0, 1.0)

        self.step_count += 1
        if self._object_goal_distance() <= self.config.goal_radius:
            self.object_delivered = True
        self._update_target()

        force_proxy = self._force_proxy()
        forbidden_cost = float(force_proxy > self.config.max_force)
        workspace_cost = float(np.any(np.abs(self.tool_xy) >= 0.999) or np.any(np.abs(self.object_xy) >= 0.999))
        motion_cost = float(np.linalg.norm(self.tool_xy - prev_tool) + np.linalg.norm(self.object_xy - prev_object))
        step_cost = forbidden_cost + workspace_cost + 0.1 * force_proxy
        self.cumulative_cost += step_cost

        tool_target_distance = float(np.linalg.norm(self.target_xy - self.tool_xy))
        object_goal_distance = self._object_goal_distance()
        reward = -self.config.dense_tool_weight * tool_target_distance
        reward -= self.config.dense_object_weight * object_goal_distance
        reward -= self.config.force_penalty * force_proxy
        reward -= self.config.motion_penalty * motion_cost
        reward -= self.config.violation_penalty * (forbidden_cost + workspace_cost)

        success = self.object_delivered and np.linalg.norm(self.retract_xy - self.tool_xy) <= self.config.goal_radius
        if success:
            reward += self.config.success_bonus

        budget_exhausted = self.cumulative_cost > self.safety_budget
        terminated = bool(success or budget_exhausted)
        truncated = self.step_count >= self.config.max_steps

        info = self._info()
        info.update(
            {
                "success": success,
                "budget_exhausted": budget_exhausted,
                "forbidden_cost": forbidden_cost,
                "workspace_cost": workspace_cost,
                "motion_cost": motion_cost,
                "object_delivered": self.object_delivered,
                "tool_object_distance": self._tool_object_distance(),
                "object_goal_distance": object_goal_distance,
            }
        )
        return self._obs(), float(reward), terminated, truncated, info

    def render(self):
        if self.render_mode != "rgb_array":
            return None

        size = 256
        image = np.full((size, size, 3), 255, dtype=np.uint8)

        def draw_disc(xyz: np.ndarray, radius: float, color: np.ndarray) -> None:
            px = ((xyz[:2] + 1.0) * 0.5 * (size - 1)).astype(int)
            cx, cy = int(px[0]), int(size - 1 - px[1])
            rr = max(2, int(radius * 0.5 * size))
            yy, xx = np.ogrid[:size, :size]
            mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= rr**2
            image[mask] = color

        draw_disc(self.forbidden_xy, self.config.forbidden_radius, np.array([240, 95, 95], dtype=np.uint8))
        draw_disc(self.goal_xy, self.config.goal_radius, np.array([80, 170, 105], dtype=np.uint8))
        draw_disc(self.object_xy, self.config.object_radius, np.array([220, 155, 65], dtype=np.uint8))
        draw_disc(self.tool_xy, self.config.tool_radius, np.array([60, 85, 180], dtype=np.uint8))
        return image

    def _update_target(self) -> None:
        if self.object_delivered:
            self.target_xy = self.retract_xy.copy()
        elif self._tool_object_distance() > self.config.contact_radius:
            self.target_xy = self.object_xy.copy()
        else:
            self.target_xy = self.goal_xy.copy()

    def _tool_object_distance(self) -> float:
        return float(np.linalg.norm(self.object_xy - self.tool_xy))

    def _object_goal_distance(self) -> float:
        return float(np.linalg.norm(self.goal_xy - self.object_xy))

    def _force_proxy(self) -> float:
        tool_distance = float(np.linalg.norm(self.tool_xy - self.forbidden_xy))
        object_distance = float(np.linalg.norm(self.object_xy - self.forbidden_xy))
        tool_penetration = max(0.0, self.config.forbidden_radius + self.config.tool_radius - tool_distance)
        object_penetration = max(0.0, self.config.forbidden_radius + self.config.object_radius - object_distance)
        return (tool_penetration + object_penetration) / max(self.config.tool_radius, 1e-6)

    def _task_phase(self) -> float:
        if self.object_delivered:
            return 2.0
        if self._tool_object_distance() > self.config.contact_radius:
            return 0.0
        return 1.0

    def _obs(self) -> np.ndarray:
        normalized_time = self.step_count / self.config.max_steps
        remaining_budget = self.safety_budget - self.cumulative_cost
        return np.array(
            [
                *self.tool_xy,
                *self.object_xy,
                *self.goal_xy,
                *self.forbidden_xy,
                *self.retract_xy,
                self._tool_object_distance(),
                self._object_goal_distance(),
                self._force_proxy(),
                normalized_time,
                self._task_phase(),
                remaining_budget,
            ],
            dtype=np.float32,
        )

    def _info(self) -> dict:
        return {
            "distance_to_goal": float(np.linalg.norm(self.target_xy - self.tool_xy)),
            "force_proxy": self._force_proxy(),
            "safety_budget": self.safety_budget,
            "cumulative_cost": self.cumulative_cost,
            "task_phase": self._task_phase(),
            "remaining_budget": self.safety_budget - self.cumulative_cost,
        }
