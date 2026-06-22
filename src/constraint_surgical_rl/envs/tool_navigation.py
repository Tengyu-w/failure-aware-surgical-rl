from __future__ import annotations

from dataclasses import dataclass

import gymnasium as gym
import numpy as np
from gymnasium import spaces


@dataclass(frozen=True)
class ToolNavigationConfig:
    workspace_dim: int = 3
    max_steps: int = 120
    action_scale: float = 0.045
    goal_radius: float = 0.055
    tool_radius: float = 0.025
    forbidden_radius: float = 0.14
    max_force: float = 1.0
    dense_goal_weight: float = 1.0
    success_bonus: float = 8.0
    violation_penalty: float = 4.0
    force_penalty: float = 0.7
    motion_penalty: float = 0.04
    start_low: float = -0.75
    start_high: float = -0.35
    target_low: float = 0.35
    target_high: float = 0.75
    safety_budget_low: float = 0.25
    safety_budget_high: float = 0.75


class ConstrainedToolNavigationEnv(gym.Env):
    """3D abstract surgical tool navigation with constraint-conditioned state.

    The environment intentionally stays lightweight so algorithm ideas can be
    tested before moving into SurRoL, ManiSkill, or MuJoCo. The tool tip must
    reach a target while respecting a forbidden volume, workspace bounds, force
    proxy, and a per-episode safety budget.
    """

    metadata = {"render_modes": ["rgb_array"], "render_fps": 20}

    def __init__(self, config: ToolNavigationConfig | None = None, render_mode: str | None = None):
        super().__init__()
        self.config = config or ToolNavigationConfig()
        self.render_mode = render_mode
        self.workspace_dim = self.config.workspace_dim
        if self.workspace_dim != 3:
            raise ValueError("ConstrainedToolNavigationEnv currently supports workspace_dim=3.")

        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(self.workspace_dim,), dtype=np.float32)
        # tool_xyz, target_xyz, forbidden_xyz, distance_to_goal, force_proxy,
        # normalized_time, task_phase, remaining_safety_budget
        coord_low = [-1.0] * (self.workspace_dim * 3)
        coord_high = [1.0] * (self.workspace_dim * 3)
        self.observation_space = spaces.Box(
            low=np.array([*coord_low, 0.0, 0.0, 0.0, 0.0, -500.0], dtype=np.float32),
            high=np.array([*coord_high, 3.5, 8.0, 1.0, 1.0, 5.0], dtype=np.float32),
            dtype=np.float32,
        )

        self.np_random: np.random.Generator
        self.tool_xy = np.zeros(self.workspace_dim, dtype=np.float32)
        self.target_xy = np.zeros(self.workspace_dim, dtype=np.float32)
        self.forbidden_xy = np.zeros(self.workspace_dim, dtype=np.float32)
        self.step_count = 0
        self.safety_budget = 0.0
        self.cumulative_cost = 0.0

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        self.step_count = 0
        self.cumulative_cost = 0.0

        self.tool_xy = self.np_random.uniform(
            self.config.start_low, self.config.start_high, size=self.workspace_dim
        ).astype(np.float32)
        self.target_xy = self.np_random.uniform(
            self.config.target_low, self.config.target_high, size=self.workspace_dim
        ).astype(np.float32)
        self.forbidden_xy = self.np_random.uniform(-0.1, 0.25, size=self.workspace_dim).astype(np.float32)
        self.safety_budget = float(
            self.np_random.uniform(self.config.safety_budget_low, self.config.safety_budget_high)
        )

        return self._obs(), self._info()

    def step(self, action):
        action = np.asarray(action, dtype=np.float32)
        action = np.clip(action, -1.0, 1.0)
        delta = action * self.config.action_scale

        prev_xy = self.tool_xy.copy()
        self.tool_xy = np.clip(self.tool_xy + delta, -1.0, 1.0)
        self.step_count += 1

        distance = self._distance_to_goal()
        force_proxy = self._force_proxy()
        forbidden_cost = float(force_proxy > self.config.max_force)
        workspace_cost = float(np.any(np.abs(self.tool_xy) >= 0.999))
        motion_cost = float(np.linalg.norm(self.tool_xy - prev_xy))
        step_cost = forbidden_cost + workspace_cost + 0.1 * force_proxy
        self.cumulative_cost += step_cost

        reward = -self.config.dense_goal_weight * distance
        reward -= self.config.force_penalty * force_proxy
        reward -= self.config.motion_penalty * motion_cost
        reward -= self.config.violation_penalty * (forbidden_cost + workspace_cost)

        success = distance <= self.config.goal_radius
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
            }
        )
        return self._obs(), float(reward), terminated, truncated, info

    def render(self):
        if self.render_mode != "rgb_array":
            return None

        size = 256
        image = np.full((size, size, 3), 255, dtype=np.uint8)

        def xy_to_px(xyz: np.ndarray) -> tuple[int, int]:
            px = ((xyz[:2] + 1.0) * 0.5 * (size - 1)).astype(int)
            return int(px[0]), int(size - 1 - px[1])

        forbidden_px = xy_to_px(self.forbidden_xy)
        target_px = xy_to_px(self.target_xy)
        tool_px = xy_to_px(self.tool_xy)
        z_depth = float(np.clip((self.tool_xy[2] + 1.0) * 0.5, 0.0, 1.0))
        forbidden_r = int(self.config.forbidden_radius * 0.5 * size)
        target_r = int(self.config.goal_radius * 0.5 * size)
        tool_r = int(self.config.tool_radius * 0.5 * size)

        yy, xx = np.ogrid[:size, :size]
        forbidden_mask = (xx - forbidden_px[0]) ** 2 + (yy - forbidden_px[1]) ** 2 <= forbidden_r**2
        target_mask = (xx - target_px[0]) ** 2 + (yy - target_px[1]) ** 2 <= target_r**2
        tool_mask = (xx - tool_px[0]) ** 2 + (yy - tool_px[1]) ** 2 <= tool_r**2

        image[forbidden_mask] = np.array([240, 95, 95], dtype=np.uint8)
        image[target_mask] = np.array([80, 170, 105], dtype=np.uint8)
        tool_color = np.array([40 + 60 * z_depth, 75 + 75 * z_depth, 200], dtype=np.uint8)
        image[tool_mask] = tool_color
        return image

    def _distance_to_goal(self) -> float:
        return float(np.linalg.norm(self.target_xy - self.tool_xy))

    def _force_proxy(self) -> float:
        distance_to_forbidden = float(np.linalg.norm(self.tool_xy - self.forbidden_xy))
        penetration = max(0.0, self.config.forbidden_radius + self.config.tool_radius - distance_to_forbidden)
        return penetration / max(self.config.tool_radius, 1e-6)

    def _task_phase(self) -> float:
        distance = self._distance_to_goal()
        if distance > 0.55:
            return 0.0
        if distance > 0.18:
            return 0.5
        return 1.0

    def _obs(self) -> np.ndarray:
        normalized_time = self.step_count / self.config.max_steps
        remaining_budget = self.safety_budget - self.cumulative_cost
        obs = np.array(
            [
                *self.tool_xy,
                *self.target_xy,
                *self.forbidden_xy,
                self._distance_to_goal(),
                self._force_proxy(),
                normalized_time,
                self._task_phase(),
                remaining_budget,
            ],
            dtype=np.float32,
        )
        return obs

    def _info(self) -> dict:
        return {
            "distance_to_goal": self._distance_to_goal(),
            "force_proxy": self._force_proxy(),
            "safety_budget": self.safety_budget,
            "cumulative_cost": self.cumulative_cost,
            "task_phase": self._task_phase(),
            "remaining_budget": self.safety_budget - self.cumulative_cost,
        }
