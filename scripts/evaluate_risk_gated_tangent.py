from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from constraint_surgical_rl import RiskGatedTangentSafetyShieldAction, make_tool_navigation_env
from constraint_surgical_rl.envs.presets import CONFIG_PRESET_NAMES


ROOT = Path(__file__).resolve().parents[1]
METHODS = ("unshielded", "always_tangent", "risk_gated_tangent")


class LogisticRiskModel:
    def __init__(self, model_path: Path):
        payload = json.loads(model_path.read_text(encoding="utf-8"))
        self.features = payload["features"]
        self.mean = np.asarray(payload["mean"], dtype=np.float64)
        self.scale = np.asarray(payload["scale"], dtype=np.float64)
        self.coef = np.asarray(payload["coef"], dtype=np.float64)
        self.intercept = float(payload["intercept"])

    def __call__(self, features: dict[str, float]) -> float:
        x = np.asarray([features.get(name, 0.0) for name in self.features], dtype=np.float64)
        z = np.dot((x - self.mean) / np.maximum(self.scale, 1e-8), self.coef) + self.intercept
        return float(1.0 / (1.0 + np.exp(-z)))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare unshielded, always tangent, and risk-gated tangent control.")
    parser.add_argument("--presets", default="prototype")
    parser.add_argument("--seeds", default="0")
    parser.add_argument("--episodes", type=int, default=50)
    parser.add_argument("--policy", choices=("heuristic", "random", "ppo"), default="heuristic")
    parser.add_argument("--model", type=Path, default=None)
    parser.add_argument("--risk-model", type=Path, default=ROOT / "outputs" / "risk_model" / "risk_model.json")
    parser.add_argument(
        "--risk-model-mode",
        choices=("learned", "default_rule"),
        default="learned",
        help="Use the saved learned logistic model or the wrapper's built-in transparent rule gate.",
    )
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "outputs" / "risk_gated_tangent")
    parser.add_argument("--deterministic", action="store_true")
    return parser.parse_args()


def comma_list(value: str, cast):
    return [cast(item.strip()) for item in value.split(",") if item.strip()]


def load_ppo(model_path: Path | None):
    if model_path is None:
        raise ValueError("--policy ppo requires --model")
    try:
        from stable_baselines3 import PPO
    except ImportError as exc:
        raise RuntimeError("stable_baselines3 is required for --policy ppo in this environment.") from exc
    return PPO.load(model_path)


def make_env(method: str, preset: str, risk_model, threshold: float):
    if method == "unshielded":
        return make_tool_navigation_env("conditioned", config_preset=preset)
    if method == "always_tangent":
        return make_tool_navigation_env("conditioned_tangent_shielded", config_preset=preset)
    if method == "risk_gated_tangent":
        base = make_tool_navigation_env("conditioned", config_preset=preset)
        return RiskGatedTangentSafetyShieldAction(base, risk_model=risk_model, threshold=threshold)
    raise ValueError(f"Unknown method: {method}")


def heuristic_action(env) -> np.ndarray:
    unwrapped = env.unwrapped
    to_target = unwrapped.target_xy - unwrapped.tool_xy
    norm = np.linalg.norm(to_target)
    if norm < 1e-8:
        return np.zeros_like(unwrapped.tool_xy, dtype=np.float32)
    action = to_target / norm
    to_forbidden = unwrapped.tool_xy - unwrapped.forbidden_xy
    forbidden_dist = np.linalg.norm(to_forbidden)
    caution_radius = unwrapped.config.forbidden_radius + 0.18
    if forbidden_dist < caution_radius:
        avoid = to_forbidden / max(forbidden_dist, 1e-8)
        action = action + 1.2 * avoid
        action = action / max(np.linalg.norm(action), 1e-8)
    return action.astype(np.float32)


def choose_action(env, policy: str, rng: np.random.Generator, ppo_model, obs, deterministic: bool) -> np.ndarray:
    if policy == "heuristic":
        return heuristic_action(env)
    if policy == "random":
        return rng.uniform(env.action_space.low, env.action_space.high).astype(np.float32)
    action, _ = ppo_model.predict(obs, deterministic=deterministic)
    return np.asarray(action, dtype=np.float32)


def run_episode(
    method: str,
    preset: str,
    experiment_seed: int,
    episode: int,
    env_seed: int,
    policy: str,
    ppo_model,
    risk_model,
    threshold: float,
    deterministic: bool,
):
    env = make_env(method, preset, risk_model, threshold)
    rng = np.random.default_rng(env_seed)
    obs, _ = env.reset(seed=env_seed)
    total_reward = 0.0
    terminated = truncated = False
    info = {}
    steps = 0
    gate_active_steps = 0
    risk_scores = []
    tangent_interventions = 0.0
    while not (terminated or truncated):
        action = choose_action(env, policy, rng, ppo_model, obs, deterministic)
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += float(reward)
        steps += 1
        gate_active_steps += int(info.get("risk_gate_active", 0.0) > 0.0)
        if "risk_score" in info:
            risk_scores.append(float(info["risk_score"]))
        tangent_interventions = float(info.get("shield_interventions", 0.0))

    false_intervention_rate = 0.0
    supervisor_activations = 0.0
    risk_gate_activations = float(info.get("risk_gate_activations", 0.0))
    risk_gated_tangent_interventions = float(info.get("risk_gated_tangent_interventions", 0.0))
    if method == "always_tangent":
        supervisor_activations = float(steps)
    elif method == "risk_gated_tangent":
        supervisor_activations = risk_gate_activations

    if method == "risk_gated_tangent":
        false_intervention_rate = max(supervisor_activations - risk_gated_tangent_interventions, 0.0) / max(steps, 1)
    elif method == "always_tangent":
        false_intervention_rate = max(supervisor_activations - tangent_interventions, 0.0) / max(steps, 1)

    return {
        "method": method,
        "preset": preset,
        "seed": experiment_seed,
        "episode": episode,
        "env_seed": env_seed,
        "policy": policy,
        "return": total_reward,
        "steps": float(steps),
        "success": float(info.get("success", False)),
        "budget_exhausted": float(info.get("budget_exhausted", False)),
        "cumulative_cost": float(info.get("cumulative_cost", 0.0)),
        "remaining_budget": float(info.get("remaining_budget", 0.0)),
        "final_distance": float(info.get("distance_to_goal", np.nan)),
        "final_force_proxy": float(info.get("force_proxy", np.nan)),
        "shield_interventions": tangent_interventions,
        "supervisor_activations": supervisor_activations,
        "supervisor_activation_rate": supervisor_activations / max(steps, 1),
        "actual_tangent_corrections": tangent_interventions,
        "actual_tangent_correction_rate": tangent_interventions / max(steps, 1),
        "risk_gate_activations": risk_gate_activations,
        "risk_gate_activation_rate": gate_active_steps / max(steps, 1),
        "risk_gated_tangent_interventions": risk_gated_tangent_interventions,
        "mean_risk_score": float(np.mean(risk_scores)) if risk_scores else np.nan,
        "max_risk_score": float(np.max(risk_scores)) if risk_scores else np.nan,
        "false_intervention_rate": false_intervention_rate,
    }


def summarize(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str, int, str], list[dict]] = {}
    for row in rows:
        key = (row["method"], row["preset"], row["seed"], row["policy"])
        grouped.setdefault(key, []).append(row)

    summary_rows = []
    for (method, preset, seed, policy), items in grouped.items():
        def mean(key: str) -> float:
            return float(np.nanmean([item[key] for item in items]))

        summary_rows.append(
            {
                "method": method,
                "preset": preset,
                "seed": seed,
                "policy": policy,
                "episodes": len(items),
                "success_rate": mean("success"),
                "budget_exhaustion_rate": mean("budget_exhausted"),
                "mean_cumulative_cost": mean("cumulative_cost"),
                "mean_final_distance": mean("final_distance"),
                "mean_interventions": mean("supervisor_activations"),
                "intervention_rate": mean("supervisor_activation_rate"),
                "mean_tangent_corrections": mean("actual_tangent_corrections"),
                "tangent_correction_rate": mean("actual_tangent_correction_rate"),
                "mean_gate_activations": mean("risk_gate_activations"),
                "gate_activation_rate": mean("risk_gate_activation_rate"),
                "false_intervention_rate": mean("false_intervention_rate"),
                "mean_risk_score": mean("mean_risk_score"),
                "max_risk_score": mean("max_risk_score"),
            }
        )
    return summary_rows


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    presets = comma_list(args.presets, str)
    seeds = comma_list(args.seeds, int)
    ppo_model = load_ppo(args.model) if args.policy == "ppo" else None
    risk_model = None
    if args.risk_model_mode == "learned":
        risk_model = LogisticRiskModel(args.risk_model) if args.risk_model.exists() else None

    rows = []
    for preset in presets:
        if preset not in CONFIG_PRESET_NAMES:
            raise ValueError(f"Unknown preset {preset!r}; choices={CONFIG_PRESET_NAMES}")
        for seed in seeds:
            for method in METHODS:
                for episode in range(args.episodes):
                    rows.append(
                        run_episode(
                            method=method,
                            preset=preset,
                            experiment_seed=seed,
                            episode=episode,
                            env_seed=seed * 10000 + episode,
                            policy=args.policy,
                            ppo_model=ppo_model,
                            risk_model=risk_model,
                            threshold=args.threshold,
                            deterministic=args.deterministic,
                        )
                    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.out_dir / "episodes.csv", rows)
    summary_rows = summarize(rows)
    write_csv(args.out_dir / "online_summary.csv", summary_rows)
    write_csv(args.out_dir / "summary.csv", summary_rows)
    print(f"episodes_csv={args.out_dir / 'episodes.csv'}")
    print(f"summary_csv={args.out_dir / 'online_summary.csv'}")
    for row in summary_rows:
        print(
            "{method} preset={preset} seed={seed} success={success_rate:.3f} "
            "budget_exhausted={budget_exhaustion_rate:.3f} interventions={mean_interventions:.3f} "
            "gate_rate={gate_activation_rate:.3f}".format(**row)
        )


if __name__ == "__main__":
    main()
