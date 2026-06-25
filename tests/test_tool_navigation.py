from constraint_surgical_rl import (
    ConstrainedToolManipulationEnv,
    ConstrainedToolNavigationEnv,
    RiskGatedTangentSafetyShieldAction,
    make_tool_manipulation_env,
    make_tool_navigation_env,
)
from constraint_surgical_rl.envs.presets import CONFIG_PRESET_NAMES, get_config_preset
from scripts.evaluate_failure_recovery import classify_failure, corrupt_target_observation
from scripts.evaluate_heuristic import heuristic_action
from scripts.evaluate_manipulation_failure_recovery import run_episode as run_manipulation_failure_episode


def test_tool_navigation_smoke_step():
    env = ConstrainedToolNavigationEnv()
    obs, info = env.reset(seed=3)
    assert obs.shape == env.observation_space.shape
    assert env.action_space.shape == (3,)
    assert "remaining_budget" in info

    obs, reward, terminated, truncated, info = env.step(env.action_space.sample())
    assert obs.shape == env.observation_space.shape
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert "force_proxy" in info


def test_tool_navigation_variants_have_expected_shapes():
    conditioned = make_tool_navigation_env("conditioned", config_preset="prototype")
    conditioned_shielded = make_tool_navigation_env("conditioned_shielded", config_preset="prototype")
    conditioned_tangent_shielded = make_tool_navigation_env("conditioned_tangent_shielded", config_preset="prototype")
    conditioned_risk_gated_tangent = make_tool_navigation_env(
        "conditioned_risk_gated_tangent_shielded", config_preset="prototype"
    )
    no_phase_budget = make_tool_navigation_env("no_phase_budget", config_preset="prototype")
    no_phase_budget_shielded = make_tool_navigation_env("no_phase_budget_shielded", config_preset="prototype")
    no_phase_budget_tangent_shielded = make_tool_navigation_env(
        "no_phase_budget_tangent_shielded", config_preset="prototype"
    )
    no_phase_budget_risk_gated_tangent = make_tool_navigation_env(
        "no_phase_budget_risk_gated_tangent_shielded", config_preset="prototype"
    )
    no_budget = make_tool_navigation_env("no_budget", config_preset="prototype")

    assert conditioned.observation_space.shape == (14,)
    assert conditioned_shielded.observation_space.shape == (14,)
    assert conditioned_tangent_shielded.observation_space.shape == (14,)
    assert conditioned_risk_gated_tangent.observation_space.shape == (14,)
    assert no_phase_budget.observation_space.shape == (12,)
    assert no_phase_budget_shielded.observation_space.shape == (12,)
    assert no_phase_budget_tangent_shielded.observation_space.shape == (12,)
    assert no_phase_budget_risk_gated_tangent.observation_space.shape == (12,)
    assert no_budget.observation_space.shape == (13,)


def test_shielded_variant_reports_interventions():
    env = make_tool_navigation_env("conditioned_shielded")
    obs, _ = env.reset(seed=4)
    obs, reward, terminated, truncated, info = env.step(env.action_space.sample())

    assert obs.shape == env.observation_space.shape
    assert isinstance(reward, float)
    assert "shield_interventions" in info
    assert "mean_action_deviation" in info


def test_tangent_shielded_variant_reports_interventions():
    env = make_tool_navigation_env("conditioned_tangent_shielded")
    obs, _ = env.reset(seed=5)
    obs, reward, terminated, truncated, info = env.step(env.action_space.sample())

    assert obs.shape == env.observation_space.shape
    assert isinstance(reward, float)
    assert "shield_interventions" in info
    assert "mean_action_deviation" in info


def test_tangent_shield_reports_positive_deviation_when_it_intervenes():
    env = make_tool_navigation_env("conditioned_tangent_shielded", config_preset="prototype")
    env.reset(seed=7)
    unwrapped = env.unwrapped
    unwrapped.tool_xy = unwrapped.forbidden_xy.copy()

    _, _, _, _, info = env.step(env.action_space.sample())

    assert info["shield_interventions"] > 0
    assert info["mean_action_deviation"] > 0.0


def test_risk_gated_tangent_reports_risk_info():
    env = make_tool_navigation_env("conditioned_risk_gated_tangent_shielded", config_preset="prototype")
    assert isinstance(env, RiskGatedTangentSafetyShieldAction)
    obs, _ = env.reset(seed=13)

    obs, reward, terminated, truncated, info = env.step(env.action_space.sample())

    assert obs.shape == env.observation_space.shape
    assert isinstance(reward, float)
    assert "risk_score" in info
    assert "risk_reasons" in info
    assert "risk_gate_active" in info
    assert "risk_gate_activations" in info


def test_risk_gated_tangent_activates_near_forbidden_region():
    env = make_tool_navigation_env("conditioned_risk_gated_tangent_shielded", config_preset="prototype")
    env.reset(seed=14)
    env.unwrapped.tool_xy = env.unwrapped.forbidden_xy.copy()

    _, _, _, _, info = env.step(env.action_space.sample())

    assert info["risk_score"] >= env.threshold
    assert info["risk_gate_active"] == 1.0
    assert info["risk_gate_activations"] > 0
    assert info["shield_interventions"] > 0


def test_config_presets_include_curriculum_levels():
    assert "easy" in CONFIG_PRESET_NAMES
    assert "prototype" in CONFIG_PRESET_NAMES
    assert "strict" in CONFIG_PRESET_NAMES
    assert "peg_transfer_proxy" in CONFIG_PRESET_NAMES
    assert "needle_regrasp_proxy" in CONFIG_PRESET_NAMES
    assert get_config_preset("easy").safety_budget_high > get_config_preset("strict").safety_budget_high


def test_heuristic_action_matches_3d_action_space():
    env = make_tool_navigation_env("conditioned", config_preset="prototype")
    env.reset(seed=6)

    action = heuristic_action(env)

    assert action.shape == env.action_space.shape


def test_corrupt_target_observation_only_changes_target_indices():
    env = make_tool_navigation_env("conditioned", config_preset="prototype")
    obs, _ = env.reset(seed=8)
    offset = env.action_space.sample() * 0.1

    corrupted = corrupt_target_observation(obs, offset)

    assert corrupted.shape == obs.shape
    assert (corrupted[:3] == obs[:3]).all()
    assert not (corrupted[3:6] == obs[3:6]).all()
    assert (corrupted[6:] == obs[6:]).all()


def test_navigation_failure_classifier_labels_active_modes():
    env = make_tool_navigation_env("conditioned", config_preset="prototype")
    assert classify_failure(False, None, 0, False) == "none"
    assert classify_failure(True, None, 0, False) == "target_drift"
    assert classify_failure(False, env.action_space.sample(), 0, False) == "state_target_bias"
    assert classify_failure(False, None, 3, False) == "state_dropout"
    assert classify_failure(False, None, 0, True) == "execution_slip"


def test_tool_manipulation_smoke_step():
    env = ConstrainedToolManipulationEnv()
    obs, info = env.reset(seed=9)
    assert obs.shape == env.observation_space.shape
    assert env.action_space.shape == (3,)
    assert "task_phase" in info

    obs, reward, terminated, truncated, info = env.step(env.action_space.sample())

    assert obs.shape == env.observation_space.shape
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert "object_goal_distance" in info


def test_tool_manipulation_variants_have_expected_shapes():
    conditioned = make_tool_manipulation_env("conditioned")
    conditioned_shielded = make_tool_manipulation_env("conditioned_shielded")
    conditioned_tangent_shielded = make_tool_manipulation_env("conditioned_tangent_shielded")
    conditioned_risk_gated_tangent = make_tool_manipulation_env("conditioned_risk_gated_tangent_shielded")
    no_phase_budget = make_tool_manipulation_env("no_phase_budget")
    no_budget = make_tool_manipulation_env("no_budget")

    assert conditioned.observation_space.shape == (21,)
    assert conditioned_shielded.observation_space.shape == (21,)
    assert conditioned_tangent_shielded.observation_space.shape == (21,)
    assert conditioned_risk_gated_tangent.observation_space.shape == (21,)
    assert no_phase_budget.observation_space.shape == (19,)
    assert no_budget.observation_space.shape == (20,)


def test_manipulation_contact_loss_monitor_recovers():
    base = run_manipulation_failure_episode(
        variant="conditioned_tangent_shielded",
        failure_mode="contact_loss",
        controller="base_controller",
        seed=12,
        failure_step=5,
        bias_magnitude=0.45,
        slip_scale=0.2,
        contact_loss_delay=2,
        recovery_steps=18,
    )
    monitor = run_manipulation_failure_episode(
        variant="conditioned_tangent_shielded",
        failure_mode="contact_loss",
        controller="monitor_recovery",
        seed=12,
        failure_step=5,
        bias_magnitude=0.45,
        slip_scale=0.2,
        contact_loss_delay=2,
        recovery_steps=18,
    )

    assert base["failure_detected"] == 1.0
    assert base["success"] == 0.0
    assert base["predicted_failure_type"] == "contact_loss"
    assert base["failure_class_correct"] == 1.0
    assert monitor["success"] == 1.0
    assert monitor["recovery_triggered"] == 1.0
    assert monitor["predicted_failure_type"] == "contact_loss"
