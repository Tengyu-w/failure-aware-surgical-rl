from __future__ import annotations

from constraint_surgical_rl.envs.tool_navigation import ToolNavigationConfig


CONFIG_PRESETS = {
    "easy": ToolNavigationConfig(
        max_steps=180,
        goal_radius=0.09,
        forbidden_radius=0.10,
        start_low=-0.55,
        start_high=-0.20,
        target_low=0.20,
        target_high=0.55,
        safety_budget_low=2.0,
        safety_budget_high=3.0,
    ),
    "default": ToolNavigationConfig(),
    "prototype": ToolNavigationConfig(
        max_steps=160,
        goal_radius=0.07,
        start_low=-0.65,
        start_high=-0.25,
        target_low=0.25,
        target_high=0.65,
        safety_budget_low=1.0,
        safety_budget_high=2.0,
    ),
    "strict": ToolNavigationConfig(
        max_steps=120,
        goal_radius=0.055,
        forbidden_radius=0.16,
        safety_budget_low=0.25,
        safety_budget_high=0.75,
    ),
    "needle_reach": ToolNavigationConfig(
        max_steps=150,
        action_scale=0.04,
        goal_radius=0.045,
        forbidden_radius=0.13,
        start_low=-0.70,
        start_high=-0.30,
        target_low=0.30,
        target_high=0.70,
        safety_budget_low=0.75,
        safety_budget_high=1.25,
        motion_penalty=0.06,
    ),
    "needle_insert": ToolNavigationConfig(
        max_steps=190,
        action_scale=0.035,
        goal_radius=0.035,
        forbidden_radius=0.15,
        start_low=-0.65,
        start_high=-0.25,
        target_low=0.35,
        target_high=0.70,
        safety_budget_low=0.60,
        safety_budget_high=1.10,
        motion_penalty=0.08,
    ),
    "tight_corridor": ToolNavigationConfig(
        max_steps=170,
        action_scale=0.04,
        goal_radius=0.055,
        forbidden_radius=0.20,
        start_low=-0.70,
        start_high=-0.35,
        target_low=0.35,
        target_high=0.70,
        safety_budget_low=0.50,
        safety_budget_high=1.00,
    ),
    "tissue_retraction_proxy": ToolNavigationConfig(
        max_steps=180,
        action_scale=0.035,
        goal_radius=0.065,
        forbidden_radius=0.18,
        start_low=-0.60,
        start_high=-0.20,
        target_low=0.20,
        target_high=0.60,
        safety_budget_low=0.85,
        safety_budget_high=1.40,
        force_penalty=1.10,
        motion_penalty=0.09,
    ),
    "gauze_manipulation_proxy": ToolNavigationConfig(
        max_steps=200,
        action_scale=0.03,
        goal_radius=0.075,
        forbidden_radius=0.12,
        start_low=-0.75,
        start_high=-0.25,
        target_low=0.25,
        target_high=0.75,
        safety_budget_low=1.10,
        safety_budget_high=1.80,
        motion_penalty=0.12,
    ),
    "peg_transfer_proxy": ToolNavigationConfig(
        max_steps=210,
        action_scale=0.032,
        goal_radius=0.050,
        forbidden_radius=0.17,
        start_low=-0.72,
        start_high=-0.28,
        target_low=0.32,
        target_high=0.72,
        safety_budget_low=0.70,
        safety_budget_high=1.20,
        force_penalty=1.05,
        motion_penalty=0.10,
    ),
    "needle_regrasp_proxy": ToolNavigationConfig(
        max_steps=220,
        action_scale=0.028,
        goal_radius=0.040,
        forbidden_radius=0.14,
        start_low=-0.68,
        start_high=-0.18,
        target_low=0.28,
        target_high=0.78,
        safety_budget_low=0.65,
        safety_budget_high=1.15,
        force_penalty=1.20,
        motion_penalty=0.11,
    ),
}

CONFIG_PRESET_NAMES = tuple(CONFIG_PRESETS.keys())


def get_config_preset(name: str) -> ToolNavigationConfig:
    try:
        return CONFIG_PRESETS[name]
    except KeyError as exc:
        choices = ", ".join(sorted(CONFIG_PRESETS))
        raise ValueError(f"Unknown config preset: {name}. Choices: {choices}") from exc
