from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from stable_baselines3 import PPO

from constraint_surgical_rl import make_tool_navigation_env
from constraint_surgical_rl.envs.presets import CONFIG_PRESET_NAMES


VARIANTS = (
    "conditioned",
    "conditioned_shielded",
    "conditioned_tangent_shielded",
    "no_phase_budget",
    "no_phase_budget_shielded",
    "no_phase_budget_tangent_shielded",
    "no_budget",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--variant", choices=VARIANTS, default="conditioned_shielded")
    parser.add_argument("--config-preset", choices=CONFIG_PRESET_NAMES, default="prototype")
    parser.add_argument("--episodes", type=int, default=6)
    parser.add_argument("--seed", type=int, default=3000)
    parser.add_argument("--out-dir", type=Path, default=Path("runs") / "rollouts")
    parser.add_argument("--deterministic", action="store_true")
    return parser.parse_args()


def run_rollout(model: PPO, variant: str, config_preset: str, seed: int, deterministic: bool) -> dict:
    env = make_tool_navigation_env(variant=variant, config_preset=config_preset)
    obs, info = env.reset(seed=seed)
    unwrapped = env.unwrapped
    path = [unwrapped.tool_xy.copy()]
    rewards = []
    terminated = False
    truncated = False

    while not (terminated or truncated):
        action, _ = model.predict(obs, deterministic=deterministic)
        obs, reward, terminated, truncated, info = env.step(action)
        path.append(unwrapped.tool_xy.copy())
        rewards.append(reward)

    return {
        "path": np.asarray(path),
        "target": unwrapped.target_xy.copy(),
        "forbidden": unwrapped.forbidden_xy.copy(),
        "config": unwrapped.config,
        "return": float(np.sum(rewards)),
        "success": bool(info.get("success", False)),
        "budget_exhausted": bool(info.get("budget_exhausted", False)),
        "cumulative_cost": float(info.get("cumulative_cost", 0.0)),
        "final_distance": float(info.get("distance_to_goal", np.nan)),
        "shield_interventions": int(info.get("shield_interventions", 0)),
    }


def plot_rollout(rollout: dict, out_path: Path, title: str) -> None:
    config = rollout["config"]
    path = rollout["path"]

    fig = plt.figure(figsize=(5.8, 5.5))
    ax = fig.add_subplot(111, projection="3d")
    ax.set_xlim(-1.02, 1.02)
    ax.set_ylim(-1.02, 1.02)
    ax.set_zlim(-1.02, 1.02)
    ax.set_box_aspect((1, 1, 1))
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    ax.grid(alpha=0.22)

    def plot_sphere(center: np.ndarray, radius: float, color: str, alpha: float) -> None:
        u = np.linspace(0, 2 * np.pi, 28)
        v = np.linspace(0, np.pi, 14)
        xs = center[0] + radius * np.outer(np.cos(u), np.sin(v))
        ys = center[1] + radius * np.outer(np.sin(u), np.sin(v))
        zs = center[2] + radius * np.outer(np.ones_like(u), np.cos(v))
        ax.plot_surface(xs, ys, zs, color=color, alpha=alpha, linewidth=0)

    plot_sphere(rollout["forbidden"], config.forbidden_radius, "#f26d6d", 0.28)
    plot_sphere(rollout["target"], config.goal_radius, "#5fb878", 0.42)

    ax.plot(path[:, 0], path[:, 1], path[:, 2], color="#315f9f", linewidth=2.0, label="tool path")
    ax.scatter(path[0, 0], path[0, 1], path[0, 2], color="#111111", s=42, marker="o", label="start")
    ax.scatter(path[-1, 0], path[-1, 1], path[-1, 2], color="#315f9f", s=42, marker="x", label="final")
    ax.scatter(*rollout["forbidden"], color="#9e3030", s=18, label="forbidden")
    ax.scatter(*rollout["target"], color="#267244", s=18, label="target")

    status = "success" if rollout["success"] else "budget" if rollout["budget_exhausted"] else "timeout"
    ax.set_title(title)
    ax.text2D(
        0.02,
        0.02,
        (
            f"status={status}\n"
            f"return={rollout['return']:.1f}\n"
            f"cost={rollout['cumulative_cost']:.2f}\n"
            f"distance={rollout['final_distance']:.2f}\n"
            f"shield={rollout['shield_interventions']}"
        ),
        transform=ax.transAxes,
        fontsize=9,
        va="bottom",
        bbox={"facecolor": "white", "edgecolor": "#cccccc", "alpha": 0.85},
    )
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    model = PPO.load(args.model)

    for idx in range(args.episodes):
        rollout = run_rollout(
            model,
            variant=args.variant,
            config_preset=args.config_preset,
            seed=args.seed + idx,
            deterministic=args.deterministic,
        )
        out_path = args.out_dir / f"{args.variant}_{args.config_preset}_seed{args.seed + idx}.png"
        title = f"{args.variant} on {args.config_preset}, episode {idx}"
        plot_rollout(rollout, out_path, title)
        print(f"rollout_plot={out_path}")


if __name__ == "__main__":
    main()
