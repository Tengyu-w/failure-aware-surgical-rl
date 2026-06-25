from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch
from stable_baselines3 import PPO

from constraint_surgical_rl import RiskGatedTangentSafetyShieldAction, make_tool_navigation_env


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "reports" / "figures" / "risk_gated_tangent_visuals"
METHODS = ["unshielded", "always_tangent", "risk_gated_tangent"]
METHOD_LABELS = {
    "unshielded": "Unshielded PPO",
    "always_tangent": "Always Tangent",
    "risk_gated_tangent": "Risk-Gated Tangent",
}
COLORS = {
    "unshielded": "#8B8B8B",
    "always_tangent": "#247BA0",
    "risk_gated_tangent": "#F25F5C",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        type=Path,
        default=ROOT / "runs" / "pilot_3d_50k_prototype_conditioned_seed0" / "model.zip",
    )
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args()


def savefig(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()
    print(f"saved {path}")


def plot_architecture(out_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 4.4))
    ax.axis("off")
    nodes = [
        ("Policy\nPPO action", 0.06, 0.55, "#F7F7F7"),
        ("Explainable\nrisk gate", 0.30, 0.55, "#FFF1D6"),
        ("Low risk\nexecute action", 0.57, 0.76, "#E8F5E9"),
        ("High risk\nTangent backup", 0.57, 0.34, "#FFE4E1"),
        ("Environment\nstep + info", 0.82, 0.55, "#EAF2F8"),
    ]
    for text, x, y, color in nodes:
        box = FancyBboxPatch(
            (x, y - 0.12),
            0.16,
            0.24,
            boxstyle="round,pad=0.02,rounding_size=0.02",
            linewidth=1.5,
            edgecolor="#333333",
            facecolor=color,
        )
        ax.add_patch(box)
        ax.text(x + 0.08, y, text, ha="center", va="center", fontsize=11, weight="bold")

    arrows = [
        ((0.22, 0.55), (0.30, 0.55), ""),
        ((0.46, 0.59), (0.57, 0.76), "risk < threshold"),
        ((0.46, 0.51), (0.57, 0.34), "risk >= threshold"),
        ((0.73, 0.76), (0.82, 0.60), ""),
        ((0.73, 0.34), (0.82, 0.50), ""),
    ]
    for start, end, label in arrows:
        arrow = FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=16, linewidth=1.4, color="#333333")
        ax.add_patch(arrow)
        if label:
            ax.text((start[0] + end[0]) / 2, (start[1] + end[1]) / 2 + 0.04, label, ha="center", fontsize=9)

    features = "Risk reasons: near forbidden zone | low budget | stalled progress | high force proxy | proposed unsafe action"
    ax.text(0.5, 0.08, features, ha="center", va="center", fontsize=10, color="#333333")
    ax.set_title("Risk-Gated Tangent Backup: From Always-On Correction to Explainable Supervision", fontsize=14, weight="bold")
    savefig(out_dir / "risk_gate_architecture.png")


def plot_aggregate_results(out_dir: Path) -> None:
    agg = pd.read_csv(ROOT / "outputs" / "risk_gated_tangent" / "aggregate_summary.csv")
    agg["label"] = agg["method"].map(METHOD_LABELS)
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4), sharey=False)
    for ax, preset in zip(axes, ["prototype", "strict"]):
        sub = agg[agg["preset"] == preset].set_index("method").loc[METHODS].reset_index()
        x = np.arange(len(sub))
        ax.bar(x - 0.18, sub["budget_exhaustion_rate"], width=0.36, color="#B00020", label="Budget exhaustion")
        ax.bar(x + 0.18, sub["intervention_rate"], width=0.36, color="#2E86AB", label="Supervisor activation")
        ax.set_xticks(x)
        ax.set_xticklabels([METHOD_LABELS[m] for m in sub["method"]], rotation=18, ha="right")
        ax.set_ylim(0, 1.05)
        ax.set_title(f"{preset}: safety vs intervention")
        ax.grid(axis="y", alpha=0.25)
        for xpos, val in zip(x - 0.18, sub["budget_exhaustion_rate"]):
            ax.text(xpos, val + 0.03, f"{val:.2f}", ha="center", fontsize=8)
        for xpos, val in zip(x + 0.18, sub["intervention_rate"]):
            ax.text(xpos, val + 0.03, f"{val:.2f}", ha="center", fontsize=8)
    axes[0].set_ylabel("Rate")
    axes[1].legend(loc="upper right", frameon=False)
    fig.suptitle("Risk-Gated Tangent Preserves Safety While Reducing Always-On Supervision", fontsize=14, weight="bold")
    savefig(out_dir / "aggregate_budget_intervention.png")


def plot_intervention_efficiency(out_dir: Path) -> None:
    agg = pd.read_csv(ROOT / "outputs" / "risk_gated_tangent" / "aggregate_summary.csv")
    fig, ax = plt.subplots(figsize=(8.8, 5.0))
    for _, row in agg.iterrows():
        method = row["method"]
        ax.scatter(
            row["intervention_rate"],
            row["budget_exhaustion_rate"],
            s=180,
            color=COLORS[method],
            edgecolor="black",
            linewidth=0.8,
        )
        ax.text(
            row["intervention_rate"] + 0.018,
            row["budget_exhaustion_rate"] + 0.018,
            f"{METHOD_LABELS[method]}\n{row['preset']}",
            fontsize=8,
        )
    ax.set_xlabel("Supervisor activation rate (lower is more efficient)")
    ax.set_ylabel("Budget exhaustion rate (lower is safer)")
    ax.set_xlim(-0.05, 1.1)
    ax.set_ylim(-0.05, 1.1)
    ax.grid(alpha=0.25)
    ax.set_title("Safety-Intervention Efficiency Frontier", fontsize=14, weight="bold")
    savefig(out_dir / "safety_intervention_frontier.png")


def plot_threshold_sweep(out_dir: Path) -> None:
    sweep = pd.read_csv(ROOT / "outputs" / "risk_gated_tangent" / "offline_threshold_sweep.csv")
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.plot(sweep["threshold"], sweep["risk_coverage"], marker="o", linewidth=2.2, label="Risk coverage")
    ax.plot(sweep["threshold"], sweep["intervention_rate"], marker="s", linewidth=2.2, label="Intervention rate")
    ax.plot(sweep["threshold"], sweep["missed_risk_rate"], marker="^", linewidth=2.2, label="Missed risk")
    ax.set_xlabel("Risk threshold")
    ax.set_ylabel("Rate")
    ax.set_ylim(0, 1.02)
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)
    ax.set_title("Offline Threshold Sweep: Coverage vs Intervention Trade-Off", fontsize=14, weight="bold")
    savefig(out_dir / "offline_threshold_sweep.png")


def plot_coefficients(out_dir: Path) -> None:
    coef = pd.read_csv(ROOT / "outputs" / "risk_model" / "logistic_coefficients.csv")
    coef = coef.sort_values("abs_coefficient", ascending=True)
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    colors = ["#D55E00" if v > 0 else "#0072B2" for v in coef["coefficient"]]
    ax.barh(coef["feature"], coef["coefficient"], color=colors)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Standardized logistic coefficient")
    ax.set_title("Interpretable Risk Model Signals", fontsize=14, weight="bold")
    ax.grid(axis="x", alpha=0.25)
    savefig(out_dir / "risk_model_coefficients.png")


def make_env(method: str, preset: str, threshold: float):
    if method == "unshielded":
        return make_tool_navigation_env("conditioned", render_mode="rgb_array", config_preset=preset)
    if method == "always_tangent":
        return make_tool_navigation_env("conditioned_tangent_shielded", render_mode="rgb_array", config_preset=preset)
    base = make_tool_navigation_env("conditioned", render_mode="rgb_array", config_preset=preset)
    return RiskGatedTangentSafetyShieldAction(base, threshold=threshold)


def rollout(model: PPO, method: str, preset: str, seed: int, threshold: float) -> dict:
    env = make_env(method, preset, threshold)
    obs, _ = env.reset(seed=seed)
    data = {
        "xy": [env.unwrapped.tool_xy.copy()],
        "risk": [],
        "gate": [],
        "interventions": [],
        "renders": [env.render()],
        "target": env.unwrapped.target_xy.copy(),
        "forbidden": env.unwrapped.forbidden_xy.copy(),
        "forbidden_radius": env.unwrapped.config.forbidden_radius,
        "tool_radius": env.unwrapped.config.tool_radius,
    }
    terminated = truncated = False
    while not (terminated or truncated):
        action, _ = model.predict(obs, deterministic=True)
        obs, _, terminated, truncated, info = env.step(action)
        data["xy"].append(env.unwrapped.tool_xy.copy())
        data["risk"].append(float(info.get("risk_score", np.nan)))
        data["gate"].append(float(info.get("risk_gate_active", 0.0)))
        data["interventions"].append(float(info.get("shield_interventions", 0.0)))
        data["renders"].append(env.render())
    data["success"] = float(info.get("success", False))
    data["budget_exhausted"] = float(info.get("budget_exhausted", False))
    data["steps"] = len(data["xy"]) - 1
    return data


def plot_rollout_trajectories(out_dir: Path, model: PPO, preset: str, seed: int, threshold: float) -> None:
    rollouts = {method: rollout(model, method, preset, seed, threshold) for method in METHODS}
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.3), sharex=True, sharey=True)
    for ax, method in zip(axes, METHODS):
        data = rollouts[method]
        xy = np.asarray(data["xy"])
        forbidden = data["forbidden"]
        target = data["target"]
        radius = data["forbidden_radius"] + data["tool_radius"]
        ax.add_patch(Circle(forbidden[:2], radius, color="#F25F5C", alpha=0.18, label="forbidden+tool radius"))
        ax.plot(xy[:, 0], xy[:, 1], color=COLORS[method], linewidth=2.2)
        ax.scatter(xy[0, 0], xy[0, 1], marker="o", s=50, color="black", label="start")
        ax.scatter(xy[-1, 0], xy[-1, 1], marker="x", s=70, color=COLORS[method], label="final")
        ax.scatter(target[0], target[1], marker="*", s=130, color="#2CA25F", label="target")
        ax.scatter(forbidden[0], forbidden[1], marker="X", s=70, color="#B00020", label="forbidden center")
        ax.set_title(
            f"{METHOD_LABELS[method]}\nsteps={data['steps']} success={data['success']:.0f} budget_exh={data['budget_exhausted']:.0f}",
            fontsize=10,
        )
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlim(-1, 1)
        ax.set_ylim(-1, 1)
        ax.grid(alpha=0.2)
    axes[0].set_ylabel("tool y")
    for ax in axes:
        ax.set_xlabel("tool x")
    axes[-1].legend(loc="lower right", fontsize=7, frameon=True)
    fig.suptitle(f"Simulated Tool Trajectories ({preset}, same PPO policy, seed={seed})", fontsize=14, weight="bold")
    savefig(out_dir / f"trajectory_{preset}.png")

    fig, axes = plt.subplots(3, 4, figsize=(10.5, 7.5))
    for row, method in enumerate(METHODS):
        data = rollouts[method]
        frames = data["renders"]
        indices = np.linspace(0, len(frames) - 1, 4).astype(int)
        for col, idx in enumerate(indices):
            ax = axes[row, col]
            ax.imshow(frames[idx])
            ax.set_xticks([])
            ax.set_yticks([])
            if col == 0:
                ax.set_ylabel(METHOD_LABELS[method], fontsize=10, weight="bold")
            ax.set_title(f"step {idx}", fontsize=9)
    fig.suptitle(f"Rendered Rollout Snapshots ({preset})", fontsize=14, weight="bold")
    savefig(out_dir / f"render_snapshots_{preset}.png")

    fig, ax = plt.subplots(figsize=(9, 4.2))
    for method in METHODS:
        data = rollouts[method]
        risk = np.asarray(data["risk"], dtype=np.float64)
        if np.isfinite(risk).any():
            ax.plot(risk, label=METHOD_LABELS[method], color=COLORS[method], linewidth=2)
    ax.axhline(threshold, color="black", linestyle="--", linewidth=1.2, label=f"threshold={threshold}")
    ax.set_xlabel("timestep")
    ax.set_ylabel("risk score")
    ax.set_ylim(0, 1.05)
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)
    ax.set_title(f"Risk Score Timeline ({preset}, risk-gated run)", fontsize=14, weight="bold")
    savefig(out_dir / f"risk_timeline_{preset}.png")


def main() -> None:
    args = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    plot_architecture(OUT_DIR)
    plot_aggregate_results(OUT_DIR)
    plot_intervention_efficiency(OUT_DIR)
    plot_threshold_sweep(OUT_DIR)
    plot_coefficients(OUT_DIR)

    model = PPO.load(args.model)
    for preset in ["prototype", "strict"]:
        plot_rollout_trajectories(OUT_DIR, model, preset, args.seed, args.threshold)


if __name__ == "__main__":
    main()
