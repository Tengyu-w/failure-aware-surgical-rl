from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
TABLES = ROOT / "reports" / "tables"
FIG_DIR = ROOT / "reports" / "figures" / "failure_aware_vppv"
REPORT = ROOT / "reports" / "failure_aware_vppv_true_mixed_rollouts.md"

CONTROLLER_ORDER = ["clean", "perturbed", "priority_routed"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=Path, default=RUNS / "surrol_true_mixed_faults_smoke.csv")
    parser.add_argument("--steps", type=Path, default=RUNS / "surrol_true_mixed_faults_smoke_steps.csv")
    parser.add_argument("--report", type=Path, default=REPORT)
    return parser.parse_args()


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_float_dtype(out[col]):
            out[col] = out[col].map(lambda x: "" if pd.isna(x) else f"{x:.3f}")
        else:
            out[col] = out[col].map(lambda x: "" if pd.isna(x) else str(x))
    header = "| " + " | ".join(out.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(out.columns)) + " |"
    rows = ["| " + " | ".join(row) + " |" for row in out.to_numpy(dtype=str)]
    return "\n".join([header, sep, *rows])


def summarize_episodes(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby(
            [
                "task",
                "failure_combo",
                "components",
                "expected_priority_route",
                "priority_recovery_policy",
                "controller",
            ],
            as_index=False,
        )
        .agg(
            episodes=("success", "size"),
            seeds=("seed", "nunique"),
            success_mean=("success", "mean"),
            final_distance_mean=("final_distance", "mean"),
            min_distance_mean=("min_distance", "mean"),
            monitor_triggers_mean=("monitor_triggers", "mean"),
            visual_reestimate_triggers_mean=("visual_reestimate_triggers", "mean"),
            recovery_override_rate_mean=("recovery_override_rate", "mean"),
            steps_mean=("steps", "mean"),
        )
        .sort_values(["task", "failure_combo", "controller"])
    )
    grouped["controller"] = pd.Categorical(grouped["controller"], CONTROLLER_ORDER, ordered=True)
    return grouped.sort_values(["task", "failure_combo", "controller"]).reset_index(drop=True)


def paired_summary(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    keys = ["task", "failure_combo", "components", "expected_priority_route", "priority_recovery_policy"]
    for key_values, group in summary.groupby(keys, observed=False):
        lookup = {str(row["controller"]): row for _, row in group.iterrows()}
        clean = lookup.get("clean")
        perturbed = lookup.get("perturbed")
        routed = lookup.get("priority_routed")
        if perturbed is None or routed is None:
            continue
        rows.append(
            {
                **dict(zip(keys, key_values)),
                "episodes": int(routed["episodes"]),
                "seeds": int(routed["seeds"]),
                "clean_success": float(clean["success_mean"]) if clean is not None else np.nan,
                "perturbed_success": float(perturbed["success_mean"]),
                "priority_routed_success": float(routed["success_mean"]),
                "perturbed_final_distance": float(perturbed["final_distance_mean"]),
                "priority_routed_final_distance": float(routed["final_distance_mean"]),
                "success_gain_vs_perturbed": float(routed["success_mean"] - perturbed["success_mean"]),
                "distance_gain_vs_perturbed": float(perturbed["final_distance_mean"] - routed["final_distance_mean"]),
                "monitor_triggers_mean": float(routed["monitor_triggers_mean"]),
                "visual_reestimate_triggers_mean": float(routed["visual_reestimate_triggers_mean"]),
                "recovery_override_rate_mean": float(routed["recovery_override_rate_mean"]),
            }
        )
    return pd.DataFrame(rows).sort_values(["task", "failure_combo"]).reset_index(drop=True)


def step_route_summary(steps: pd.DataFrame) -> pd.DataFrame:
    rows = []
    routed = steps[steps["controller"].eq("priority_routed")].copy()
    for (task, combo), group in routed.groupby(["task", "failure_combo"]):
        rows.append(
            {
                "task": task,
                "failure_combo": combo,
                "steps": len(group),
                "expected_priority_route": group["expected_priority_route"].mode().iloc[0],
                "recovery_policy": group["priority_recovery_policy"].mode().iloc[0],
                "monitor_trigger_rate": float(group["monitor_trigger"].mean()),
                "risk_event_rate": float(group["risk_event"].mean()),
                "visual_reestimate_trigger_rate": float(group["visual_reestimate_trigger"].mean()),
                "recovery_override_rate": float(group["recovery_override"].mean()),
                "mean_perception_error_norm": float(group["perception_error_norm"].mean()),
                "mean_action_deviation": float(group["action_deviation"].mean()),
            }
        )
    return pd.DataFrame(rows).sort_values(["task", "failure_combo"]).reset_index(drop=True)


def make_figures(paired: pd.DataFrame, steps: pd.DataFrame) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    for metric, ylabel, filename in [
        ("success", "success rate", "failure_aware_vppv_true_mixed_success.png"),
        ("final_distance", "final distance", "failure_aware_vppv_true_mixed_distance.png"),
    ]:
        fig, axes = plt.subplots(1, 2, figsize=(14, 4.8), sharey=False, constrained_layout=True)
        for ax, task in zip(axes, sorted(paired["task"].unique())):
            task_df = paired[paired["task"].eq(task)].copy()
            labels = task_df["failure_combo"].str.replace("+", "\n+", regex=False)
            x = np.arange(len(task_df))
            width = 0.26
            if metric == "success":
                clean = task_df["clean_success"]
                perturbed = task_df["perturbed_success"]
                routed = task_df["priority_routed_success"]
                ax.set_ylim(-0.05, 1.05)
            else:
                clean = np.full(len(task_df), np.nan)
                perturbed = task_df["perturbed_final_distance"]
                routed = task_df["priority_routed_final_distance"]
            ax.bar(x - width, clean, width, label="clean", color="#8aa4b8")
            ax.bar(x, perturbed, width, label="perturbed", color="#c78b55")
            ax.bar(x + width, routed, width, label="priority routed", color="#2f8f5f")
            ax.set_title(task)
            ax.set_ylabel(ylabel)
            ax.set_xticks(x)
            ax.set_xticklabels(labels, rotation=25, ha="right", fontsize=8)
            ax.grid(axis="y", alpha=0.25)
        axes[-1].legend(frameon=False, loc="best")
        fig.suptitle(f"True mixed-fault SurRoL rollout: {ylabel}", fontweight="bold")
        fig.savefig(FIG_DIR / filename, dpi=180)
        plt.close(fig)

    routed_steps = steps[steps["controller"].eq("priority_routed")].copy()
    if routed_steps.empty:
        return
    fig, axes = plt.subplots(4, 2, figsize=(14, 10), sharey=True, constrained_layout=True)
    combos = sorted(routed_steps["failure_combo"].unique())
    tasks = sorted(routed_steps["task"].unique())
    for row, combo in enumerate(combos):
        for col, task in enumerate(tasks):
            ax = axes[row, col]
            group = routed_steps[routed_steps["task"].eq(task) & routed_steps["failure_combo"].eq(combo)]
            if group.empty:
                ax.axis("off")
                continue
            for _, episode in group.groupby(["seed", "episode"]):
                ax.plot(episode["step"], episode["distance"], alpha=0.75)
            ax.set_title(f"{task}: {combo}", fontsize=9)
            ax.grid(alpha=0.25)
            if col == 0:
                ax.set_ylabel("distance")
            if row == len(combos) - 1:
                ax.set_xlabel("step")
    fig.suptitle("Priority-routed true mixed-fault distance traces", fontweight="bold")
    fig.savefig(FIG_DIR / "failure_aware_vppv_true_mixed_distance_traces.png", dpi=180)
    plt.close(fig)


def write_report(report: Path, paired: pd.DataFrame, summary: pd.DataFrame, step_summary: pd.DataFrame) -> None:
    seeds_per_cell = int(summary["seeds"].max()) if not summary.empty else 0
    overall = (
        summary.groupby("controller", as_index=False, observed=False)
        .agg(
            episodes=("episodes", "sum"),
            success_mean=("success_mean", "mean"),
            final_distance_mean=("final_distance_mean", "mean"),
            monitor_triggers_mean=("monitor_triggers_mean", "mean"),
            recovery_override_rate_mean=("recovery_override_rate_mean", "mean"),
        )
    )
    overall["controller"] = pd.Categorical(overall["controller"], CONTROLLER_ORDER, ordered=True)
    overall = overall.sort_values("controller")

    lines = [
        "# Failure-Aware VPPV True Mixed-Fault SurRoL Rollouts",
        "",
        "This report runs actual SurRoL/PyBullet oracle rollouts with multiple",
        "failure proxies injected in the same episode. It closes the gap left by",
        "the offline mixed-priority audit: the previous audit composed evidence",
        "traces; this run executes mixed faults through the simulator dynamics.",
        f"The current run is smoke-scale: {seeds_per_cell} seeds per task/fault/controller cell.",
        "",
        "## Overall Controller Comparison",
        "",
        markdown_table(overall),
        "",
        "## Paired Mixed-Fault Results",
        "",
        markdown_table(paired),
        "",
        "## Priority-Routed Step Signals",
        "",
        markdown_table(step_summary),
        "",
        "## Interpretation",
        "",
        "- `perturbed` applies the mixed observation/action faults without a routing",
        "  response.",
        "- `priority_routed` selects the recovery policy from the mechanism priority",
        "  order: depth before visual, visual before policy drift.",
        "- All tested mixed combinations contain visual or depth state unreliability,",
        "  so the priority route uses `review_reestimate` before allowing",
        "  near-target drift correction to matter.",
        "- This remains scripted-oracle simulation evidence. It is not a learned",
        "  surgical policy or hardware validation.",
        "",
        "## Output Tables And Figures",
        "",
        "- `reports/tables/failure_aware_vppv_true_mixed_rollout_summary.csv`",
        "- `reports/tables/failure_aware_vppv_true_mixed_rollout_paired.csv`",
        "- `reports/tables/failure_aware_vppv_true_mixed_rollout_steps.csv`",
        "- `reports/figures/failure_aware_vppv/failure_aware_vppv_true_mixed_success.png`",
        "- `reports/figures/failure_aware_vppv/failure_aware_vppv_true_mixed_distance.png`",
        "- `reports/figures/failure_aware_vppv/failure_aware_vppv_true_mixed_distance_traces.png`",
        "",
    ]
    report.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    episodes = pd.read_csv(args.episodes)
    steps = pd.read_csv(args.steps)
    TABLES.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    summary = summarize_episodes(episodes)
    paired = paired_summary(summary)
    step_summary = step_route_summary(steps)

    summary.to_csv(TABLES / "failure_aware_vppv_true_mixed_rollout_summary.csv", index=False)
    paired.to_csv(TABLES / "failure_aware_vppv_true_mixed_rollout_paired.csv", index=False)
    step_summary.to_csv(TABLES / "failure_aware_vppv_true_mixed_rollout_steps.csv", index=False)
    make_figures(paired, steps)
    write_report(args.report, paired, summary, step_summary)
    print(f"report={args.report}")
    print(f"summary={TABLES / 'failure_aware_vppv_true_mixed_rollout_summary.csv'}")
    print(f"paired={TABLES / 'failure_aware_vppv_true_mixed_rollout_paired.csv'}")


if __name__ == "__main__":
    main()
