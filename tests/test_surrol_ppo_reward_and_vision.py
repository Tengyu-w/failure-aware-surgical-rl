from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "train_surrol_ppo_failure_aware.py"
SPEC = importlib.util.spec_from_file_location("surrol_ppo_train", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

DAGGER_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "train_surrol_visual_dagger.py"
DAGGER_SPEC = importlib.util.spec_from_file_location("surrol_visual_dagger", DAGGER_SCRIPT)
DAGGER_MODULE = importlib.util.module_from_spec(DAGGER_SPEC)
assert DAGGER_SPEC.loader is not None
DAGGER_SPEC.loader.exec_module(DAGGER_MODULE)

RECOVERY_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "train_surrol_visual_recovery_memory.py"
RECOVERY_SPEC = importlib.util.spec_from_file_location("surrol_visual_recovery", RECOVERY_SCRIPT)
RECOVERY_MODULE = importlib.util.module_from_spec(RECOVERY_SPEC)
assert RECOVERY_SPEC.loader is not None
RECOVERY_SPEC.loader.exec_module(RECOVERY_MODULE)

ROUTING_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "evaluate_surrol_visual_risk_routing.py"
ROUTING_SPEC = importlib.util.spec_from_file_location("surrol_visual_routing", ROUTING_SCRIPT)
ROUTING_MODULE = importlib.util.module_from_spec(ROUTING_SPEC)
assert ROUTING_SPEC.loader is not None
ROUTING_SPEC.loader.exec_module(ROUTING_MODULE)

ADAPTER_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "train_surrol_visual_denoising_adapter.py"
ADAPTER_SPEC = importlib.util.spec_from_file_location("surrol_visual_adapter_train", ADAPTER_SCRIPT)
ADAPTER_MODULE = importlib.util.module_from_spec(ADAPTER_SPEC)
assert ADAPTER_SPEC.loader is not None
ADAPTER_SPEC.loader.exec_module(ADAPTER_MODULE)

RISK_HEAD_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "train_surrol_visual_action_risk_head.py"
RISK_HEAD_SPEC = importlib.util.spec_from_file_location("surrol_visual_risk_head_train", RISK_HEAD_SCRIPT)
RISK_HEAD_MODULE = importlib.util.module_from_spec(RISK_HEAD_SPEC)
assert RISK_HEAD_SPEC.loader is not None
RISK_HEAD_SPEC.loader.exec_module(RISK_HEAD_MODULE)

ONLINE_RECOVERY_SCRIPT = (
    Path(__file__).resolve().parents[1] / "scripts" / "train_surrol_online_adapter_recovery_memory.py"
)
ONLINE_RECOVERY_SPEC = importlib.util.spec_from_file_location(
    "surrol_online_adapter_recovery", ONLINE_RECOVERY_SCRIPT
)
ONLINE_RECOVERY_MODULE = importlib.util.module_from_spec(ONLINE_RECOVERY_SPEC)
assert ONLINE_RECOVERY_SPEC.loader is not None
ONLINE_RECOVERY_SPEC.loader.exec_module(ONLINE_RECOVERY_MODULE)


def _obs(achieved, desired):
    return {
        "observation": np.zeros(3, dtype=np.float32),
        "achieved_goal": np.asarray(achieved, dtype=np.float32),
        "desired_goal": np.asarray(desired, dtype=np.float32),
    }


def test_progress_delta_rewards_closer_motion_and_clips_outliers():
    previous = _obs([0.0, 0.0, 0.0], [1.0, 0.0, 0.0])
    current = _obs([0.2, 0.0, 0.0], [1.0, 0.0, 0.0])

    delta, goal_changed = MODULE.progress_delta(previous, current, clip=0.03)

    assert delta == 0.03
    assert not goal_changed


def test_progress_delta_ignores_multistage_goal_switch():
    previous = _obs([0.0, 0.0, 0.0], [1.0, 0.0, 0.0])
    current = _obs([0.2, 0.0, 0.0], [2.0, 0.0, 0.0])

    delta, goal_changed = MODULE.progress_delta(previous, current, clip=0.03)

    assert delta == 0.0
    assert goal_changed


def test_visual_occlusion_is_bounded_and_reported():
    image = np.full((32, 48, 3), 255, dtype=np.uint8)
    corrupted, magnitude, applied = MODULE.corrupt_rendered_image(
        image,
        np.random.default_rng(7),
        corruption="occlusion",
        probability=1.0,
        severity=0.5,
    )

    assert corrupted.dtype == image.dtype
    assert corrupted.min() == 0
    assert corrupted.max() == 255
    assert magnitude > 0.0
    assert applied == "occlusion"


def test_visual_blackout_removes_all_pixels():
    image = np.full((8, 8, 3), 255, dtype=np.uint8)
    corrupted, magnitude, applied = MODULE.corrupt_rendered_image(
        image,
        np.random.default_rng(3),
        corruption="blackout",
        probability=1.0,
        severity=1.0,
    )

    assert not corrupted.any()
    assert magnitude == 1.0
    assert applied == "blackout"


def test_render_stride_reuses_frames_and_tracks_age():
    class FakeEnv:
        def __init__(self):
            self.render_calls = 0

        def render(self, mode="rgb_array"):
            self.render_calls += 1
            return np.full((4, 4, 3), self.render_calls, dtype=np.uint8)

    wrapper = MODULE.FailureAwareSurrolWrapper.__new__(MODULE.FailureAwareSurrolWrapper)
    wrapper.env = FakeEnv()
    wrapper.args = SimpleNamespace(vision_stride=3)
    wrapper.steps = 0
    wrapper._cached_rendered_image = None
    wrapper._last_render_step = -1

    frame0 = wrapper._render_for_obs()
    wrapper.steps = 1
    frame1 = wrapper._render_for_obs()
    wrapper.steps = 2
    frame2 = wrapper._render_for_obs()
    wrapper.steps = 3
    frame3 = wrapper._render_for_obs()

    assert wrapper.env.render_calls == 2
    assert np.array_equal(frame0, frame1)
    assert np.array_equal(frame1, frame2)
    assert not np.array_equal(frame2, frame3)
    assert wrapper.visual_frame_updated
    assert wrapper.visual_frame_age == 0


def test_visual_features_are_stable_while_cached_frame_is_reused():
    wrapper = MODULE.FailureAwareSurrolWrapper.__new__(MODULE.FailureAwareSurrolWrapper)
    wrapper.args = SimpleNamespace(
        observation_mode="render_proprio_vision",
        vision_corruption="gaussian_noise",
        vision_corruption_prob=1.0,
        vision_corruption_severity=0.5,
        pseudo_vision_noise=0.01,
        image_grid_size=4,
        image_feature_mode="stats_gray",
        proprio_dim=3,
    )
    wrapper.rng = np.random.default_rng(5)
    wrapper.visual_frame_updated = True
    wrapper._cached_visual_features = None
    image = np.full((16, 16, 3), 127, dtype=np.uint8)
    obs = _obs([0.0, 0.0, 0.0], [1.0, 1.0, 1.0])
    obs["observation"] = np.zeros(3, dtype=np.float32)

    first = wrapper._flatten(obs, image)
    wrapper.visual_frame_updated = False
    second = wrapper._flatten(obs, image)

    assert np.array_equal(first, second)


def test_render_proprio_vision_excludes_privileged_goals():
    image = np.full((16, 16, 3), 127, dtype=np.uint8)
    obs_a = _obs([0.0, 0.0, 0.0], [1.0, 2.0, 3.0])
    obs_b = _obs([9.0, 8.0, 7.0], [-1.0, -2.0, -3.0])
    obs_a["observation"] = np.arange(7, dtype=np.float32)
    obs_b["observation"] = np.arange(7, dtype=np.float32)

    flat_a = MODULE.flatten_obs(
        obs_a,
        "render_proprio_vision",
        np.random.default_rng(1),
        0.0,
        image,
        proprio_dim=7,
        image_grid_size=4,
        image_feature_mode="stats_gray",
    )
    flat_b = MODULE.flatten_obs(
        obs_b,
        "render_proprio_vision",
        np.random.default_rng(1),
        0.0,
        image,
        proprio_dim=7,
        image_grid_size=4,
        image_feature_mode="stats_gray",
    )

    assert flat_a.shape == (32,)
    assert np.array_equal(flat_a, flat_b)


def test_rgb_grid_expands_spatial_image_features():
    image = np.zeros((16, 16, 3), dtype=np.uint8)
    gray = MODULE.image_features(image, np.random.default_rng(2), 0.0, grid_size=4, feature_mode="stats_gray")
    rgb = MODULE.image_features(image, np.random.default_rng(2), 0.0, grid_size=8, feature_mode="stats_rgb")

    assert gray.shape == (25,)
    assert rgb.shape == (201,)


def test_global_seed_controls_numpy_task_sampling():
    MODULE.seed_global_randomness(1234)
    first = np.random.rand(4)
    MODULE.seed_global_randomness(1234)
    second = np.random.rand(4)

    assert np.array_equal(first, second)


def test_dagger_beta_selects_expected_action_source():
    policy = np.array([1.0, 0.0], dtype=np.float32)
    oracle = np.array([0.0, 1.0], dtype=np.float32)

    selected_oracle, oracle_source = DAGGER_MODULE.choose_execution_action(
        policy, oracle, beta=1.0, rng=np.random.default_rng(1)
    )
    selected_policy, policy_source = DAGGER_MODULE.choose_execution_action(
        policy, oracle, beta=0.0, rng=np.random.default_rng(1)
    )

    assert np.array_equal(selected_oracle, oracle)
    assert oracle_source == "oracle"
    assert np.array_equal(selected_policy, policy)
    assert policy_source == "policy"


def test_precision_shaping_rewards_closer_states_and_damps_near_target_actions():
    action = np.array([1.0, 0.5, 0.0, 0.0, 0.0], dtype=np.float32)
    far_reward, far_cost = MODULE.precision_shaping(0.20, action, 5.0, 0.3, 0.12)
    near_reward, near_cost = MODULE.precision_shaping(0.03, action, 5.0, 0.3, 0.12)

    assert near_reward > far_reward
    assert far_cost == 0.0
    assert near_cost > 0.0


def test_recovery_knn_retrieves_nearby_action_and_bounds_neighbor_count():
    memory_features = np.array([[0.0, 0.0], [1.0, 1.0]], dtype=np.float32)
    memory_actions = np.array([[0.2, 0.0], [-0.2, 0.1]], dtype=np.float32)

    prediction = RECOVERY_MODULE.predict_knn(
        np.array([[0.01, 0.01]], dtype=np.float32),
        memory_features,
        memory_actions,
        neighbors=99,
    )

    assert prediction.shape == (1, 2)
    assert prediction[0, 0] > 0.19
    assert prediction[0, 1] < 0.01


def test_recovery_nearest_distance_flags_out_of_memory_query():
    memory = np.array([[0.0, 0.0], [1.0, 1.0]], dtype=np.float32)

    distances = RECOVERY_MODULE.nearest_distances(
        np.array([[0.1, 0.1], [5.0, 5.0]], dtype=np.float32), memory
    )

    assert distances.shape == (2,)
    assert distances[0] < 0.2
    assert distances[1] > 5.0


def test_recovery_leave_one_out_distance_does_not_match_self():
    memory = np.array([[0.0], [2.0], [5.0]], dtype=np.float32)

    distances = RECOVERY_MODULE.leave_one_out_nearest_distances(memory)

    assert np.allclose(distances, [2.0, 2.0, 3.0])


def test_high_risk_review_ceiling_is_optional_and_inclusive():
    assert not ROUTING_MODULE.requires_high_risk_review(0.9, None)
    assert not ROUTING_MODULE.requires_high_risk_review(0.59, 0.6)
    assert ROUTING_MODULE.requires_high_risk_review(0.6, 0.6)


def test_recovery_budget_reports_total_before_consecutive_limit():
    assert ROUTING_MODULE.recovery_budget_reason(4, 2, None, None) is None
    assert ROUTING_MODULE.recovery_budget_reason(15, 3, 15, 8) == "human_review_recovery_budget"
    assert ROUTING_MODULE.recovery_budget_reason(5, 8, 15, 8) == "human_review_recovery_stagnation"


def test_temporal_features_track_recovery_history_without_goal_state():
    state = ROUTING_MODULE.TemporalFeatureState(window=4, max_steps=50)
    before = state.features(step=10, risk=0.5, memory_distance=1.2, high_risk=True)
    state.update(risk=0.5, high_risk=True, recovered=True)
    after = state.features(step=11, risk=0.55, memory_distance=1.1, high_risk=True)

    assert before.shape == (10,)
    assert before[3] == 0.0
    assert after[3] > 0.0
    assert after[4] > 0.0


def test_observable_deltas_separate_proprio_and_normalized_visual_change():
    previous = np.zeros(7, dtype=np.float32)
    current = np.array([3.0, 4.0, 0.0, 2.0, 2.0, 2.0, 2.0], dtype=np.float32)

    proprio_delta, visual_delta = ROUTING_MODULE.observable_deltas(current, previous, proprio_dim=3)

    assert proprio_delta == 5.0
    assert visual_delta == 2.0


def test_linear_visual_adapter_applies_blended_residual():
    features = np.array([1.0, 2.0], dtype=np.float32)
    adapted = MODULE.apply_linear_visual_adapter(
        features,
        input_mean=np.zeros(2),
        input_std=np.ones(2),
        residual_weights=np.eye(2),
        residual_bias=np.zeros(2),
        blend=0.5,
    )

    assert np.allclose(adapted, [1.5, 3.0])


def test_visual_adapter_seed_split_keeps_test_independent():
    train, validation, test = ADAPTER_MODULE.seed_split_masks(np.arange(8))

    assert np.array_equal(np.flatnonzero(train), [0, 1, 4, 5])
    assert np.array_equal(np.flatnonzero(validation), [2, 6])
    assert np.array_equal(np.flatnonzero(test), [3, 7])


def test_visual_risk_head_seed_split_keeps_threshold_selection_off_test():
    train, validation, test = RISK_HEAD_MODULE.seed_split_masks(np.arange(8))

    assert np.array_equal(np.flatnonzero(train), [0, 1, 4, 5])
    assert np.array_equal(np.flatnonzero(validation), [2, 6])
    assert np.array_equal(np.flatnonzero(test), [3, 7])


def test_online_recovery_seed_split_matches_adapter_protocol():
    train, validation, test = ONLINE_RECOVERY_MODULE.split_masks(np.arange(8))

    assert np.array_equal(np.flatnonzero(train), [0, 1, 4, 5])
    assert np.array_equal(np.flatnonzero(validation), [2, 6])
    assert np.array_equal(np.flatnonzero(test), [3, 7])
