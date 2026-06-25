from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from train_surrol_ppo_failure_aware import goal_distance, make_env  # noqa: E402
from surrol_temporal_stagnation import TemporalFeatureState, TemporalStagnationHead  # noqa: E402


class VisualActionRiskHead:
    def __init__(self, path: Path):
        values = np.load(path)
        self.feature_mean = values["feature_mean"]
        self.feature_std = values["feature_std"]
        self.pca_mean = values["pca_mean"]
        self.components = values["pca_components"]
        self.latent_mean = values["latent_mean"]
        self.latent_std = values["latent_std"]
        self.weights = values["logistic_weights"]
        self.bias = float(values["logistic_bias"][0])
        self.threshold = float(values["risk_threshold"][0])

    def score(self, observation: np.ndarray) -> float:
        vector = np.asarray(observation, dtype=np.float64).ravel()
        if vector.shape != self.feature_mean.shape:
            raise ValueError(f"Risk-head observation shape mismatch: {vector.shape} vs {self.feature_mean.shape}")
        standardized = (vector - self.feature_mean) / self.feature_std
        latent = (standardized - self.pca_mean) @ self.components.T
        normalized = (latent - self.latent_mean) / self.latent_std
        logit = float(normalized @ self.weights + self.bias)
        return float(1.0 / (1.0 + np.exp(-np.clip(logit, -40.0, 40.0))))


class VisualRecoveryMemory:
    def __init__(self, path: Path):
        values = np.load(path)
        self.feature_mean = values["feature_mean"]
        self.feature_std = values["feature_std"]
        self.pca_mean = values["pca_mean"]
        self.components = values["pca_components"]
        self.latent_scale = values["latent_scale"]
        self.memory_features = values["memory_features"]
        self.memory_actions = values["memory_actions"]
        self.neighbors = int(values["neighbors"][0])
        self.action_low = values["action_low"]
        self.action_high = values["action_high"]
        self.max_neighbor_distance = float(values["max_neighbor_distance"][0])

    def predict(self, observation: np.ndarray) -> tuple[np.ndarray, float]:
        vector = np.asarray(observation, dtype=np.float64).ravel()
        if vector.shape != self.feature_mean.shape:
            raise ValueError(f"Recovery observation shape mismatch: {vector.shape} vs {self.feature_mean.shape}")
        standardized = (vector - self.feature_mean) / self.feature_std
        latent = ((standardized - self.pca_mean) @ self.components.T) / self.latent_scale
        squared_distances = np.sum((self.memory_features - latent) ** 2, axis=1)
        nearest_distance = float(np.sqrt(np.min(squared_distances)))
        k = min(max(1, self.neighbors), len(self.memory_features))
        indices = np.argpartition(squared_distances, k - 1)[:k]
        weights = 1.0 / np.maximum(np.sqrt(np.maximum(squared_distances[indices], 0.0)), 1e-6)
        weights /= weights.sum()
        action = weights @ self.memory_actions[indices]
        return np.clip(action, self.action_low, self.action_high).astype(np.float32), nearest_distance


def requires_high_risk_review(risk: float, review_threshold: float | None) -> bool:
    return review_threshold is not None and float(risk) >= float(review_threshold)


def recovery_budget_reason(
    total_recoveries: int,
    consecutive_recoveries: int,
    max_total: int | None,
    max_consecutive: int | None,
) -> str | None:
    if max_total is not None and total_recoveries >= max_total:
        return "human_review_recovery_budget"
    if max_consecutive is not None and consecutive_recoveries >= max_consecutive:
        return "human_review_recovery_stagnation"
    return None


def observable_deltas(
    observation: np.ndarray,
    previous_observation: np.ndarray | None,
    proprio_dim: int,
) -> tuple[float, float]:
    current = np.asarray(observation, dtype=np.float64).ravel()
    if previous_observation is None:
        return 0.0, 0.0
    previous = np.asarray(previous_observation, dtype=np.float64).ravel()
    if current.shape != previous.shape:
        raise ValueError(f"Observation delta shape mismatch: {current.shape} vs {previous.shape}")
    split = min(max(0, int(proprio_dim)), len(current))
    proprio_delta = float(np.linalg.norm(current[:split] - previous[:split]))
    visual = current[split:] - previous[split:]
    visual_delta = float(np.linalg.norm(visual) / np.sqrt(max(1, visual.size)))
    return proprio_delta, visual_delta


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--risk-head", type=Path, required=True)
    parser.add_argument(
        "--routing-mode",
        choices=["observe", "defer", "selective_memory", "selective_memory_guarded", "selective_oracle"],
        default="observe",
    )
    parser.add_argument("--recovery-memory", type=Path, default=None)
    parser.add_argument("--risk-threshold", type=float, default=None)
    parser.add_argument("--review-risk-threshold", type=float, default=None)
    parser.add_argument("--max-recovery-overrides", type=int, default=None)
    parser.add_argument("--max-consecutive-recoveries", type=int, default=None)
    parser.add_argument("--stagnation-head", type=Path, default=None)
    parser.add_argument("--surrol-root", type=Path, default=Path("external/SurRoL_clean_SR-VPPV"))
    parser.add_argument("--task", default="NeedleReachRL-v0")
    parser.add_argument("--seed", type=int, default=50900)
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--max-episode-steps", type=int, default=75)
    parser.add_argument("--vision-stride", type=int, default=4)
    parser.add_argument("--proprio-dim", type=int, default=7)
    parser.add_argument("--image-grid-size", type=int, default=8)
    parser.add_argument("--image-feature-mode", default="stats_rgb", choices=["stats_gray", "stats_rgb"])
    parser.add_argument(
        "--vision-corruption",
        default="none",
        choices=["none", "gaussian_noise", "brightness_shift", "occlusion", "blackout", "mixed"],
    )
    parser.add_argument("--vision-corruption-prob", type=float, default=0.0)
    parser.add_argument("--vision-corruption-severity", type=float, default=0.25)
    parser.add_argument("--visual-adapter", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args()


def env_args(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        surrol_root=args.surrol_root,
        task=args.task,
        seed=args.seed,
        max_episode_steps=args.max_episode_steps,
        failure_mode="none",
        failure_prob=0.0,
        observation_mode="render_proprio_vision",
        pseudo_vision_noise=0.003,
        vision_corruption=args.vision_corruption,
        vision_corruption_prob=args.vision_corruption_prob,
        vision_corruption_severity=args.vision_corruption_severity,
        vision_stride=args.vision_stride,
        proprio_dim=args.proprio_dim,
        image_grid_size=args.image_grid_size,
        image_feature_mode=args.image_feature_mode,
        visual_adapter=getattr(args, "visual_adapter", None),
        danger_zone="none",
        danger_radius=0.052,
        danger_penalty=2.0,
        success_bonus=5.0,
        progress_reward_scale=10.0,
        progress_clip=0.03,
        distance_reward_scale=0.0,
        near_target_action_penalty=0.0,
        near_target_threshold=0.12,
    )


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    from stable_baselines3 import PPO

    risk_head = VisualActionRiskHead(args.risk_head)
    recovery_memory = None
    stagnation_head = TemporalStagnationHead(args.stagnation_head) if args.stagnation_head is not None else None
    if args.routing_mode in {"selective_memory", "selective_memory_guarded"}:
        if args.recovery_memory is None:
            raise ValueError("--recovery-memory is required for selective_memory routing")
        recovery_memory = VisualRecoveryMemory(args.recovery_memory)
    threshold = risk_head.threshold if args.risk_threshold is None else args.risk_threshold
    config = env_args(args)
    env = make_env(config)
    model = PPO.load(
        args.model,
        env=env,
        custom_objects={"observation_space": env.observation_space, "action_space": env.action_space},
    )
    step_rows = []
    episode_rows = []
    for episode in range(args.episodes):
        eval_seed = args.seed + episode
        env.seed(eval_seed)
        obs = env.reset()
        initial_distance = goal_distance(env.last_raw_obs)
        min_distance = initial_distance
        final_distance = initial_distance
        success = 0.0
        overrides = 0
        consecutive_recoveries = 0
        temporal_state = TemporalFeatureState(
            window=stagnation_head.window if stagnation_head is not None else 8,
            max_steps=50,
        )
        previous_decision_observation = None
        deferred = False
        risks = []
        for step in range(args.max_episode_steps):
            risk = risk_head.score(obs)
            proprio_delta, visual_delta = observable_deltas(obs, previous_decision_observation, args.proprio_dim)
            policy_action = np.asarray(model.predict(obs, deterministic=True)[0], dtype=np.float32)
            oracle_action = None
            oracle_gap = float("nan")
            if args.routing_mode in {"observe", "defer", "selective_oracle"}:
                oracle_action = np.asarray(env.env.get_oracle_action(env.last_raw_obs), dtype=np.float32)
                oracle_gap = float(np.linalg.norm(policy_action - oracle_action))
            high_risk = risk >= threshold
            if not high_risk:
                consecutive_recoveries = 0
            route = "auto_execute"
            action = policy_action
            memory_distance = float("nan")
            stagnation_score = float("nan")
            if high_risk and requires_high_risk_review(risk, args.review_risk_threshold):
                route = "human_review_high_risk"
                deferred = True
                step_rows.append(
                    {
                        "episode": episode,
                        "seed": eval_seed,
                        "step": step,
                        "predicted_risk": risk,
                        "high_risk": high_risk,
                        "oracle_action_gap": oracle_gap,
                        "memory_distance": memory_distance,
                        "stagnation_score": stagnation_score,
                        "proprio_delta": proprio_delta,
                        "visual_delta": visual_delta,
                        "route": route,
                        "goal_distance_before": goal_distance(env.last_raw_obs),
                        "goal_distance_after": goal_distance(env.last_raw_obs),
                    }
                )
                risks.append(risk)
                break
            budget_route = None
            if high_risk and args.routing_mode in {"selective_memory", "selective_memory_guarded"}:
                budget_route = recovery_budget_reason(
                    overrides,
                    consecutive_recoveries,
                    args.max_recovery_overrides,
                    args.max_consecutive_recoveries,
                )
            if budget_route is not None:
                route = budget_route
                deferred = True
                step_rows.append(
                    {
                        "episode": episode,
                        "seed": eval_seed,
                        "step": step,
                        "predicted_risk": risk,
                        "high_risk": high_risk,
                        "oracle_action_gap": oracle_gap,
                        "memory_distance": memory_distance,
                        "stagnation_score": stagnation_score,
                        "proprio_delta": proprio_delta,
                        "visual_delta": visual_delta,
                        "route": route,
                        "goal_distance_before": goal_distance(env.last_raw_obs),
                        "goal_distance_after": goal_distance(env.last_raw_obs),
                    }
                )
                risks.append(risk)
                break
            if high_risk and args.routing_mode == "defer":
                route = "human_review"
                deferred = True
                step_rows.append(
                    {
                        "episode": episode,
                        "seed": eval_seed,
                        "step": step,
                        "predicted_risk": risk,
                        "high_risk": high_risk,
                        "oracle_action_gap": oracle_gap,
                        "memory_distance": memory_distance,
                        "stagnation_score": stagnation_score,
                        "proprio_delta": proprio_delta,
                        "visual_delta": visual_delta,
                        "route": route,
                        "goal_distance_before": goal_distance(env.last_raw_obs),
                        "goal_distance_after": goal_distance(env.last_raw_obs),
                    }
                )
                risks.append(risk)
                break
            if high_risk and args.routing_mode == "selective_oracle":
                route = "auto_recovery_oracle_upper_bound"
                action = oracle_action
                overrides += 1
            elif high_risk and args.routing_mode in {"selective_memory", "selective_memory_guarded"}:
                recovery_action, memory_distance = recovery_memory.predict(obs)
                if (
                    args.routing_mode == "selective_memory_guarded"
                    and memory_distance > recovery_memory.max_neighbor_distance
                ):
                    route = "human_review_ood"
                    deferred = True
                    step_rows.append(
                        {
                            "episode": episode,
                            "seed": eval_seed,
                            "step": step,
                            "predicted_risk": risk,
                            "high_risk": high_risk,
                            "oracle_action_gap": oracle_gap,
                            "memory_distance": memory_distance,
                            "stagnation_score": stagnation_score,
                            "proprio_delta": proprio_delta,
                            "visual_delta": visual_delta,
                            "route": route,
                            "goal_distance_before": goal_distance(env.last_raw_obs),
                            "goal_distance_after": goal_distance(env.last_raw_obs),
                        }
                    )
                    risks.append(risk)
                    break
                if stagnation_head is not None and step >= stagnation_head.min_step:
                    temporal_features = temporal_state.features(step, risk, memory_distance, high_risk)
                    stagnation_score = stagnation_head.score(temporal_features)
                    if stagnation_score >= stagnation_head.threshold:
                        route = "human_review_learned_stagnation"
                        deferred = True
                        step_rows.append(
                            {
                                "episode": episode,
                                "seed": eval_seed,
                                "step": step,
                                "predicted_risk": risk,
                                "high_risk": high_risk,
                                "oracle_action_gap": oracle_gap,
                                "memory_distance": memory_distance,
                                "stagnation_score": stagnation_score,
                                "proprio_delta": proprio_delta,
                                "visual_delta": visual_delta,
                                "route": route,
                                "goal_distance_before": goal_distance(env.last_raw_obs),
                                "goal_distance_after": goal_distance(env.last_raw_obs),
                            }
                        )
                        risks.append(risk)
                        break
                route = "auto_recovery_visual_memory"
                action = recovery_action
                overrides += 1
                consecutive_recoveries += 1
            distance_before = goal_distance(env.last_raw_obs)
            temporal_state.update(risk, high_risk, route == "auto_recovery_visual_memory")
            previous_decision_observation = np.asarray(obs, dtype=np.float32).copy()
            obs, _, done, info = env.step(action)
            final_distance = goal_distance(env.last_raw_obs)
            min_distance = min(min_distance, final_distance)
            success = float(info.get("is_success", 0.0))
            risks.append(risk)
            step_rows.append(
                {
                    "episode": episode,
                    "seed": eval_seed,
                    "step": step,
                    "predicted_risk": risk,
                    "high_risk": high_risk,
                    "oracle_action_gap": oracle_gap,
                    "memory_distance": memory_distance,
                    "stagnation_score": stagnation_score,
                    "proprio_delta": proprio_delta,
                    "visual_delta": visual_delta,
                    "route": route,
                    "goal_distance_before": distance_before,
                    "goal_distance_after": final_distance,
                }
            )
            if done:
                break
        if deferred:
            final_route = "human_review"
        elif success >= 1.0:
            final_route = "auto_execute" if overrides == 0 else "auto_recovery"
        elif overrides > 0:
            final_route = "auto_recovery_failed"
        else:
            final_route = "human_review"
        episode_rows.append(
            {
                "episode": episode,
                "seed": eval_seed,
                "routing_mode": args.routing_mode,
                "success": success,
                "deferred": deferred,
                "steps": step + 1,
                "initial_distance": initial_distance,
                "min_distance": min_distance,
                "final_distance": final_distance,
                "overrides": overrides,
                "override_rate": overrides / max(1, step + 1),
                "mean_risk": float(np.mean(risks)),
                "max_risk": float(np.max(risks)),
                "final_route": final_route,
            }
        )
    env.close()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.out_dir / "risk_routing_steps.csv", step_rows)
    write_csv(args.out_dir / "risk_routing_episodes.csv", episode_rows)
    summary = {
        "routing_mode": args.routing_mode,
        "risk_threshold": threshold,
        "review_risk_threshold": args.review_risk_threshold,
        "max_recovery_overrides": args.max_recovery_overrides,
        "max_consecutive_recoveries": args.max_consecutive_recoveries,
        "stagnation_head": None if args.stagnation_head is None else str(args.stagnation_head),
        "vision_corruption": args.vision_corruption,
        "vision_corruption_prob": args.vision_corruption_prob,
        "vision_corruption_severity": args.vision_corruption_severity,
        "visual_adapter": None if args.visual_adapter is None else str(args.visual_adapter),
        "episodes": len(episode_rows),
        "success_rate": float(np.mean([row["success"] for row in episode_rows])),
        "defer_rate": float(np.mean([row["deferred"] for row in episode_rows])),
        "mean_override_rate": float(np.mean([row["override_rate"] for row in episode_rows])),
        "note": (
            "selective_memory uses observation-only retrieval online and does not query oracle actions. "
            "selective_memory_guarded defers out-of-memory observations. "
            "selective_oracle remains a simulation upper bound."
        ),
    }
    (args.out_dir / "risk_routing_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"episodes={args.out_dir / 'risk_routing_episodes.csv'}")
    print(f"success_rate={summary['success_rate']:.4f}")
    print(f"defer_rate={summary['defer_rate']:.4f}")


if __name__ == "__main__":
    main()
