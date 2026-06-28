from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "reports" / "tables"
FIG_DIR = ROOT / "reports" / "figures" / "failure_aware_vppv"
REPORT = ROOT / "reports" / "failure_aware_vppv_supervisor_brief.md"
FIGURE = FIG_DIR / "failure_aware_vppv_supervisor_pack.png"

STEP_DATA = TABLES / "failure_aware_vppv_step_dataset.csv"
STEP_ROUTE_SUMMARY = TABLES / "failure_aware_vppv_step_route_summary.csv"
CROSS_TASK_SUMMARY = TABLES / "failure_aware_vppv_cross_task_summary.csv"
EARLY_WARNING_SUMMARY = TABLES / "failure_aware_vppv_step_early_warning_summary.csv"
SEVERITY_HOLDOUT_SUMMARY = TABLES / "failure_aware_vppv_severity_holdout_summary.csv"
MIXED_PRIORITY_SUMMARY = TABLES / "failure_aware_vppv_mixed_priority_summary.csv"
TRUE_MIXED_ROLLOUT_PAIRED = TABLES / "failure_aware_vppv_true_mixed_rollout_paired.csv"

FRAME_PATHS = [
    ROOT / "reports" / "media" / "surrol_render_evidence" / "needlepick" / "frames" / "needlepick_step_000.png",
    ROOT / "reports" / "media" / "surrol_render_evidence" / "needlepick" / "frames" / "needlepick_step_020.png",
    ROOT / "reports" / "media" / "surrol_render_evidence" / "needlepick" / "frames" / "needlepick_step_040.png",
]

MECHANISM_ORDER = [
    ("visual_estimation_bias", "reobserve_reestimate", "Visual estimation bias"),
    ("depth_scale_error", "depth_reestimate_or_cautious_approach", "Depth-scale error"),
    ("policy_approach_drift", "low_gain_correction_or_replan", "Policy approach drift"),
]

EVIDENCE_COLUMNS = [
    ("visual_state_evidence", "visual", "#2f6f9f"),
    ("depth_scale_evidence", "depth", "#9b4d1d"),
    ("policy_embedding_proxy_evidence", "policy proxy", "#5b5f97"),
    ("action_outcome_mismatch_evidence", "action-outcome", "#2f8f5f"),
]


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


def select_episode(df: pd.DataFrame, mechanism: str) -> pd.DataFrame:
    subset = df[(df["mechanism_label"] == mechanism) & (df["task"] == "NeedlePick")].copy()
    if subset.empty:
        subset = df[df["mechanism_label"] == mechanism].copy()
    counts = subset.groupby("episode_id").size().sort_values(ascending=False)
    episode_id = counts.index[0]
    return subset[subset["episode_id"] == episode_id].sort_values("step")


def make_supervisor_pack() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    steps = pd.read_csv(STEP_DATA)
    route_summary = pd.read_csv(STEP_ROUTE_SUMMARY)
    cross_task = pd.read_csv(CROSS_TASK_SUMMARY)

    fig = plt.figure(figsize=(16, 11), constrained_layout=True)
    grid = fig.add_gridspec(4, 4, height_ratios=[1.05, 1.0, 1.0, 1.0])

    fig.suptitle(
        "Failure-Aware VPPV: mechanism evidence, route decisions, and cross-task transfer",
        fontsize=18,
        fontweight="bold",
    )

    frame_axes = [fig.add_subplot(grid[0, i]) for i in range(3)]
    for ax, frame_path, label in zip(frame_axes, FRAME_PATHS, ["start", "approach", "near target"]):
        img = Image.open(frame_path)
        ax.imshow(img)
        ax.set_title(f"SurRoL NeedlePick {label}", fontsize=11)
        ax.axis("off")

    text_ax = fig.add_subplot(grid[0, 3])
    text_ax.axis("off")
    text_ax.text(
        0.0,
        0.95,
        "What is being supervised?",
        fontsize=12,
        fontweight="bold",
        transform=text_ax.transAxes,
    )
    text_ax.text(
        0.0,
        0.78,
        "Not low-level jaw mechanics.\n"
        "The router watches the VPPV loop:\n"
        "visual-state estimate -> approach policy ->\n"
        "near-target servoing handoff.\n\n"
        "When the evidence points to a mechanism,\n"
        "the route changes from continue to\n"
        "re-estimate, cautious depth handling,\n"
        "or low-gain correction/replan.",
        fontsize=10,
        linespacing=1.35,
        transform=text_ax.transAxes,
        va="top",
    )

    for row, (mechanism, route, title) in enumerate(MECHANISM_ORDER, start=1):
        ep = select_episode(steps, mechanism)
        ax = fig.add_subplot(grid[row, :3])
        x = ep["step"].to_numpy()
        for column, label, color in EVIDENCE_COLUMNS:
            ax.plot(x, ep[column].to_numpy(), label=label, linewidth=1.8, color=color)
        active = ep["high_risk_step"].astype(bool).to_numpy()
        if active.any():
            ax.fill_between(x, 0, 1.05, where=active, color="#e7b8a0", alpha=0.22, step="mid")
        routed = ep["composite_step_route"].eq(route)
        if routed.any():
            ax.scatter(
                ep.loc[routed, "step"],
                np.full(int(routed.sum()), 1.04),
                s=16,
                marker="|",
                color="#b3261e",
                label="route active",
            )
        ax.set_ylim(-0.02, 1.10)
        ax.set_ylabel("evidence")
        ax.set_title(f"{title} -> {route}", loc="left", fontsize=12, fontweight="bold")
        ax.grid(alpha=0.25)
        if row == len(MECHANISM_ORDER):
            ax.set_xlabel("step")
        else:
            ax.set_xticklabels([])
        if row == 1:
            ax.legend(ncol=5, loc="upper right", fontsize=8)

    bar_ax = fig.add_subplot(grid[1:3, 3])
    plot_df = route_summary[route_summary["model"].isin(["visual_only", "depth_only", "policy_only", "composite_step_route"])]
    colors = ["#7c98b3", "#c78b55", "#8b7aa8", "#2f8f5f"]
    bar_ax.barh(plot_df["model"], plot_df["macro_f1"], color=colors[: len(plot_df)])
    bar_ax.set_xlim(0, 1.05)
    bar_ax.set_xlabel("macro-F1")
    bar_ax.set_title("Single evidence vs composite", fontsize=12, fontweight="bold")
    bar_ax.grid(axis="x", alpha=0.25)
    for y, value in enumerate(plot_df["macro_f1"]):
        bar_ax.text(float(value) + 0.02, y, f"{value:.3f}", va="center", fontsize=9)

    transfer_ax = fig.add_subplot(grid[3, 3])
    test_rows = cross_task[cross_task["split"].str.contains("test_on")].copy()
    labels = test_rows["split"].str.replace("test_on_", "", regex=False)
    transfer_ax.bar(labels, test_rows["macro_f1"], color=["#4f7cac", "#2f8f5f"])
    transfer_ax.set_ylim(0.94, 1.01)
    transfer_ax.set_ylabel("macro-F1")
    transfer_ax.set_title("Frozen-threshold transfer", fontsize=12, fontweight="bold")
    transfer_ax.grid(axis="y", alpha=0.25)
    for i, value in enumerate(test_rows["macro_f1"]):
        transfer_ax.text(i, float(value) + 0.002, f"{value:.3f}", ha="center", fontsize=9)

    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, dpi=180)
    plt.close(fig)


def write_brief() -> None:
    route_summary = pd.read_csv(STEP_ROUTE_SUMMARY)
    cross_task = pd.read_csv(CROSS_TASK_SUMMARY)
    early = pd.read_csv(EARLY_WARNING_SUMMARY)
    severity_holdout = pd.read_csv(SEVERITY_HOLDOUT_SUMMARY) if SEVERITY_HOLDOUT_SUMMARY.exists() else pd.DataFrame()
    mixed_priority = pd.read_csv(MIXED_PRIORITY_SUMMARY) if MIXED_PRIORITY_SUMMARY.exists() else pd.DataFrame()
    true_mixed = pd.read_csv(TRUE_MIXED_ROLLOUT_PAIRED) if TRUE_MIXED_ROLLOUT_PAIRED.exists() else pd.DataFrame()

    selected_routes = route_summary[
        route_summary["model"].isin(["visual_only", "depth_only", "policy_only", "composite_step_route"])
    ][
        [
            "model",
            "accuracy",
            "macro_f1",
            "missed_high_risk_step_rate",
            "false_alarm_on_nominal_step_rate",
            "route_diversity",
        ]
    ]
    test_rows = cross_task[cross_task["split"].str.contains("test_on")][
        [
            "split",
            "rows",
            "threshold_visual",
            "threshold_depth",
            "threshold_policy",
            "threshold_action",
            "macro_f1",
            "missed_high_risk_step_rate",
            "false_alarm_on_continue_rate",
        ]
    ]
    early_selected = early[
        early["model"].eq("composite") & early["mechanism"].isin(
            ["visual_estimation_bias", "depth_scale_error", "policy_approach_drift", "nominal"]
        )
    ][["mechanism", "episodes", "alert_rate", "false_alert_rate", "median_lead_time"]]
    severity_selected = pd.DataFrame()
    if not severity_holdout.empty:
        severity_selected = severity_holdout[severity_holdout["split"].eq("high_holdout")][
            [
                "model",
                "rows",
                "seeds_total",
                "macro_f1",
                "missed_intervention_rate",
                "false_intervention_rate",
                "route_diversity",
            ]
        ]
    mixed_selected = pd.DataFrame()
    if not mixed_priority.empty:
        mixed_selected = mixed_priority[
            [
                "model",
                "rows",
                "scenarios",
                "macro_f1",
                "missed_intervention_rate",
                "wrong_priority_rate",
                "route_diversity",
            ]
        ]
    true_mixed_selected = pd.DataFrame()
    true_mixed_seed_count = 0
    true_mixed_episodes = 0
    true_mixed_perturbed_success = 0
    true_mixed_routed_success = 0
    if not true_mixed.empty:
        true_mixed_selected = true_mixed[
            [
                "task",
                "failure_combo",
                "episodes",
                "seeds",
                "perturbed_success",
                "priority_routed_success",
                "perturbed_final_distance",
                "priority_routed_final_distance",
            ]
        ]
        true_mixed_seed_count = int(true_mixed["seeds"].max())
        true_mixed_episodes = int(true_mixed["episodes"].sum())
        true_mixed_perturbed_success = int(
            round((true_mixed["perturbed_success"] * true_mixed["episodes"]).sum())
        )
        true_mixed_routed_success = int(
            round((true_mixed["priority_routed_success"] * true_mixed["episodes"]).sum())
        )

    text = f"""# Failure-Aware VPPV Supervisor Brief

## One-Sentence Claim

This project does not try to relearn surgical jaw/gripper mechanics. It adds a
mechanism-aware runtime supervisor around the VPPV-style
perception-policy-servoing loop, so visual-state bias, depth-scale error, and
high-level approach drift are routed to different recovery actions instead of
being treated as one generic failure.

## Pain Point In The Teacher's VPPV Setting

In the local notes and SurRoL/VPPV reading, the learned part is best treated as
a high-level state-to-approach policy supported by visual state estimation and
later servoing/control. The important reliability question is therefore not
whether the jaw can open or close. The question is whether the system can detect
that the state estimate or approach decision has become unreliable before the
tool keeps moving toward the wrong state.

## Mechanism-Specific Routing

| Failure source | Evidence that should rise | Route |
| --- | --- | --- |
| Visual-state estimation bias | visual residual, perception uncertainty, local state mismatch | `reobserve_reestimate` |
| Depth-scale error | depth evidence before visual residual is trusted | `depth_reestimate_or_cautious_approach` |
| Policy approach drift | action-outcome mismatch and policy-proxy instability | `low_gain_correction_or_replan` |
| Nominal execution | no high-risk evidence | `continue` |

## Main Evidence

![Failure-aware VPPV supervisor pack](figures/failure_aware_vppv/failure_aware_vppv_supervisor_pack.png)

### Step-Level Router Ablation

{markdown_table(selected_routes)}

### Cross-Task Frozen-Threshold Check

{markdown_table(test_rows)}

### Severity-Held-Out Check

{markdown_table(severity_selected)}

### Mixed-Perturbation Priority Check

{markdown_table(mixed_selected)}

### True Mixed-Fault SurRoL Rollouts

{markdown_table(true_mixed_selected)}

### Early Warning Summary

{markdown_table(early_selected)}

## Interpretation

The useful result is not just that a score becomes high after a fault. Single
evidence families are incomplete: visual-only, depth-only, and policy-only
routes miss different high-risk steps. The composite router uses mechanism
order: depth is checked before visual residuals, and policy drift is routed
through action-outcome/policy-proxy evidence. This is why the method is closer
to the ECG project's error-mechanism analysis than to a retry-after-failure
controller.

The cross-task check is a stronger internal test than within-task consistency:
thresholds are calibrated on one SurRoL task and frozen when evaluating the
other. Current results show macro-F1 of 1.000 from NeedlePick to GauzeRetrieve
and 0.996 from GauzeRetrieve to NeedlePick, with no missed high-risk steps
under the simulator-derived weak labels.

The severity-held-out check uses low/medium severity conditions to learn
intervention boundaries, then evaluates high severity without recalibrating.
This is a small 30-seed aggregate check, but it shows why uniform retry is the
wrong framing: high-severity visual/depth state errors require re-estimation or
review, while near-target drift can route to low-gain correction or replan.

The mixed-perturbation priority check is an offline compositional stress test,
not a new mixed-fault rollout. Its role is to test route ordering when evidence
families co-activate. It shows that a max-score or generic retry rule can pick
the wrong mechanism, while the priority router preserves `depth -> visual ->
policy` routing.

The true mixed-fault rollout then executes the mixed proxies in SurRoL/PyBullet.
In the current {true_mixed_seed_count}-seed smoke-scale run, perturbed mixed
cases are {true_mixed_perturbed_success}/{true_mixed_episodes} success and
priority-routed cases are {true_mixed_routed_success}/{true_mixed_episodes}
success, which is stronger evidence than the offline composition audit but
still scripted-oracle simulation evidence.

## Scope Boundary

This is simulation evidence. The labels are derived from injected faults and
routing rules, not independent surgeon annotation. The current claim is
therefore: mechanism-aware reliability supervision is plausible and measurable
around VPPV-style surgical simulation, not that the system is clinically
validated or ready for hardware autonomy.

## Next Validation Step

The next strongest experiment is to scale the true mixed-fault run to more
seeds and add learned-policy or image-corruption conditions, then compare the
same priority router against a non-oracle VPPV policy path.
"""
    REPORT.write_text(text + "\n", encoding="utf-8")


def main() -> None:
    make_supervisor_pack()
    write_brief()
    print(f"brief={REPORT}")
    print(f"figure={FIGURE}")


if __name__ == "__main__":
    main()
