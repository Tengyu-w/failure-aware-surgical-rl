from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "reports" / "tables"
FIGURES = ROOT / "reports" / "figures" / "failure_aware_vppv"
REPORT = ROOT / "reports" / "failure_aware_vppv_step_evidence.md"
SOURCE = TABLES / "surrol_risk_triage_scored_steps.csv"

CORE_FAILURES = ["none", "perception_bias", "depth_scale_error", "near_target_drift"]

MECHANISM_BY_FAILURE = {
    "none": "nominal",
    "perception_bias": "visual_estimation_bias",
    "depth_scale_error": "depth_scale_error",
    "near_target_drift": "policy_approach_drift",
}

ROUTE_BY_MECHANISM = {
    "nominal": "continue",
    "visual_estimation_bias": "reobserve_reestimate",
    "depth_scale_error": "depth_reestimate_or_cautious_approach",
    "policy_approach_drift": "low_gain_correction_or_replan",
}

ROUTE_ORDER = [
    "continue",
    "reobserve_reestimate",
    "depth_reestimate_or_cautious_approach",
    "low_gain_correction_or_replan",
]


def numeric(df: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in df.columns:
        return pd.Series(default, index=df.index, dtype=float)
    return pd.to_numeric(df[column], errors="coerce").fillna(default).astype(float)


def clip01(series: pd.Series | np.ndarray) -> pd.Series:
    if isinstance(series, pd.Series):
        return pd.Series(np.clip(series.to_numpy(dtype=float), 0.0, 1.0), index=series.index)
    return pd.Series(np.clip(np.asarray(series, dtype=float), 0.0, 1.0))


def minmax(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").fillna(0.0).astype(float)
    lo = float(values.min())
    hi = float(values.max())
    if math.isclose(lo, hi):
        return pd.Series(0.0, index=series.index, dtype=float)
    return (values - lo) / (hi - lo)


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_float_dtype(out[col]):
            out[col] = out[col].map(lambda x: f"{x:.3f}")
        else:
            out[col] = out[col].astype(str)
    header = "| " + " | ".join(out.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(out.columns)) + " |"
    rows = ["| " + " | ".join(row) + " |" for row in out.to_numpy(dtype=str)]
    return "\n".join([header, sep, *rows])


def load_step_dataset() -> pd.DataFrame:
    df = pd.read_csv(SOURCE)
    df = df[df["failure"].isin(CORE_FAILURES)].copy()

    # Keep true nominal references and actual fault/recovery runs. Drop clean
    # references that are stored under a fault name.
    df = df[
        ((df["failure"] == "none") & (df["controller"] == "clean"))
        | ((df["failure"] != "none") & (df["controller"].isin(["perturbed", "monitor_corrected"])))
    ].copy()

    df["mechanism_label"] = df["failure"].map(MECHANISM_BY_FAILURE)
    df["episode_id"] = (
        df["task"].astype(str)
        + "::"
        + df["failure"].astype(str)
        + "::"
        + df["controller"].astype(str)
        + "::"
        + df["seed"].astype(str)
        + "::"
        + df["episode"].astype(str)
    )

    perception_error = numeric(df, "perception_error_norm")
    perception_error_scaled = clip01(perception_error / 0.05)
    depth_error_scaled = clip01(perception_error / 0.20)
    action_anomaly = numeric(df, "action_anomaly_score")
    monitor_trigger = numeric(df, "monitor_trigger")
    recovery_override = numeric(df, "recovery_override")
    stall = numeric(df, "stall_score")
    no_improve = numeric(df, "no_improve_score")
    far = numeric(df, "far_score")
    triage = clip01(numeric(df, "triage_risk_score") / 4.75)

    df["visual_state_evidence"] = clip01(0.65 * numeric(df, "perception_uncertain_score") + 0.35 * perception_error_scaled)
    df["depth_scale_evidence"] = clip01(depth_error_scaled)
    df["policy_embedding_proxy_evidence"] = clip01(0.55 * action_anomaly + 0.30 * triage + 0.15 * minmax(numeric(df, "action_deviation")))
    df["action_outcome_mismatch_evidence"] = clip01(
        0.60 * action_anomaly + 0.20 * monitor_trigger + 0.20 * recovery_override
    )
    df["progress_regularity_evidence"] = clip01(0.45 * stall + 0.35 * no_improve + 0.20 * far)
    df["local_neighborhood_proxy_evidence"] = clip01(
        0.40 * df["policy_embedding_proxy_evidence"]
        + 0.35 * df["progress_regularity_evidence"]
        + 0.25 * (df["mechanism_label"].ne("nominal").astype(float))
    )

    df["mechanism_active"] = False
    df.loc[df["mechanism_label"].isin(["visual_estimation_bias", "depth_scale_error"]), "mechanism_active"] = (
        df["visual_state_evidence"] >= 0.45
    )
    df.loc[df["mechanism_label"] == "policy_approach_drift", "mechanism_active"] = (
        (df["action_outcome_mismatch_evidence"] >= 0.35)
        | (df["policy_embedding_proxy_evidence"] >= 0.45)
    )

    df["expected_step_route"] = "continue"
    active = df["mechanism_active"]
    df.loc[active, "expected_step_route"] = df.loc[active, "mechanism_label"].map(ROUTE_BY_MECHANISM)

    df["composite_step_score"] = clip01(
        0.24 * df["visual_state_evidence"]
        + 0.18 * df["depth_scale_evidence"]
        + 0.20 * df["policy_embedding_proxy_evidence"]
        + 0.20 * df["action_outcome_mismatch_evidence"]
        + 0.10 * df["progress_regularity_evidence"]
        + 0.08 * df["local_neighborhood_proxy_evidence"]
    )
    df["composite_step_route"] = df.apply(composite_route, axis=1)
    df["high_risk_step"] = df["expected_step_route"].ne("continue")
    return df


def composite_route(row: pd.Series) -> str:
    if row["depth_scale_evidence"] >= 0.70:
        return "depth_reestimate_or_cautious_approach"
    if row["visual_state_evidence"] >= 0.60:
        return "reobserve_reestimate"
    if row["action_outcome_mismatch_evidence"] >= 0.40 or row["policy_embedding_proxy_evidence"] >= 0.52:
        return "low_gain_correction_or_replan"
    return "continue"


def macro_f1(labels: pd.Series, preds: pd.Series) -> float:
    scores = []
    for route in ROUTE_ORDER:
        y = labels.eq(route)
        p = preds.eq(route)
        tp = int((y & p).sum())
        fp = int((~y & p).sum())
        fn = int((y & ~p).sum())
        if tp == 0 and fp == 0 and fn == 0:
            continue
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        scores.append(0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall))
    return float(np.mean(scores)) if scores else 0.0


def summarize_route_models(df: pd.DataFrame) -> pd.DataFrame:
    baseline = df.copy()
    baseline["route_visual_only"] = np.where(
        baseline["visual_state_evidence"] >= 0.60, "reobserve_reestimate", "continue"
    )
    baseline["route_depth_only"] = np.where(
        baseline["depth_scale_evidence"] >= 0.70, "depth_reestimate_or_cautious_approach", "continue"
    )
    baseline["route_policy_only"] = np.where(
        (baseline["action_outcome_mismatch_evidence"] >= 0.40)
        | (baseline["policy_embedding_proxy_evidence"] >= 0.52),
        "low_gain_correction_or_replan",
        "continue",
    )
    baseline["route_single_score"] = np.where(
        baseline["composite_step_score"] >= 0.50, "low_gain_correction_or_replan", "continue"
    )

    rows = []
    labels = baseline["expected_step_route"]
    high = labels.ne("continue")
    for col in [
        "route_visual_only",
        "route_depth_only",
        "route_policy_only",
        "route_single_score",
        "composite_step_route",
    ]:
        pred = baseline[col]
        rows.append(
            {
                "model": col.replace("route_", ""),
                "step_rows": len(baseline),
                "accuracy": float(pred.eq(labels).mean()),
                "macro_f1": macro_f1(labels, pred),
                "missed_high_risk_step_rate": float((high & pred.eq("continue")).sum() / max(high.sum(), 1)),
                "false_alarm_on_nominal_step_rate": float((~high & pred.ne("continue")).sum() / max((~high).sum(), 1)),
                "route_diversity": int(pred.nunique()),
            }
        )
    return pd.DataFrame(rows)


def evidence_ablation(df: pd.DataFrame) -> pd.DataFrame:
    evidence_cols = [
        "visual_state_evidence",
        "depth_scale_evidence",
        "policy_embedding_proxy_evidence",
        "action_outcome_mismatch_evidence",
        "progress_regularity_evidence",
        "local_neighborhood_proxy_evidence",
        "composite_step_score",
    ]
    high = df["high_risk_step"].astype(bool)
    rows = []
    for mechanism, group in df.groupby("mechanism_label"):
        group_high = group["high_risk_step"].astype(bool)
        for col in evidence_cols:
            for budget in [0.05, 0.10, 0.20]:
                order = group.sort_values(col, ascending=False)
                k = max(1, int(math.ceil(len(order) * budget)))
                selected = order.head(k).index
                captured = int(group_high.loc[selected].sum())
                rows.append(
                    {
                        "mechanism": mechanism,
                        "evidence": col,
                        "budget": budget,
                        "selected_steps": k,
                        "capture_rate": float(captured / max(group_high.sum(), 1)),
                        "precision_at_budget": float(captured / k),
                    }
                )
    for col in evidence_cols:
        for budget in [0.05, 0.10, 0.20]:
            order = df.sort_values(col, ascending=False)
            k = max(1, int(math.ceil(len(order) * budget)))
            selected = order.head(k).index
            captured = int(high.loc[selected].sum())
            rows.append(
                {
                    "mechanism": "all",
                    "evidence": col,
                    "budget": budget,
                    "selected_steps": k,
                    "capture_rate": float(captured / max(high.sum(), 1)),
                    "precision_at_budget": float(captured / k),
                }
            )
    return pd.DataFrame(rows)


def early_warning(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    route_cols = {
        "visual_only": "visual_state_evidence",
        "depth_only": "depth_scale_evidence",
        "policy_only": "policy_embedding_proxy_evidence",
        "action_outcome_only": "action_outcome_mismatch_evidence",
    }
    thresholds = {
        "visual_only": 0.60,
        "depth_only": 0.70,
        "policy_only": 0.52,
        "action_outcome_only": 0.40,
    }
    for episode_id, seq in df.groupby("episode_id", sort=False):
        seq = seq.sort_values("step")
        mechanism = str(seq["mechanism_label"].iloc[0])
        terminal_step = int(seq["step"].max())
        success_steps = seq[seq["success"].astype(float) >= 1.0]
        if not success_steps.empty:
            terminal_step = int(success_steps["step"].iloc[0])
        active_steps = seq[seq["mechanism_active"]]
        onset_step = float(active_steps["step"].iloc[0]) if not active_steps.empty else np.nan
        alert_specs = {
            **{name: (seq[col] >= thresholds[name]) for name, col in route_cols.items()},
            "composite": seq["composite_step_route"].ne("continue"),
        }
        for name, mask in alert_specs.items():
            alerts = seq[mask]
            first_alert = float(alerts["step"].iloc[0]) if not alerts.empty else np.nan
            if mechanism == "nominal":
                rows.append(
                    {
                        "episode_id": episode_id,
                        "task": seq["task"].iloc[0],
                        "mechanism": mechanism,
                        "model": name,
                        "terminal_step": terminal_step,
                        "onset_step": onset_step,
                        "first_alert_step": first_alert,
                        "alerted": not np.isnan(first_alert),
                        "lead_time_to_terminal": np.nan,
                        "alert_after_onset_lag": np.nan,
                        "false_alert": not np.isnan(first_alert),
                    }
                )
                continue
            alerted = not np.isnan(first_alert)
            lead = terminal_step - first_alert if alerted else np.nan
            lag = first_alert - onset_step if alerted and not np.isnan(onset_step) else np.nan
            rows.append(
                {
                    "episode_id": episode_id,
                    "task": seq["task"].iloc[0],
                    "mechanism": mechanism,
                    "model": name,
                    "terminal_step": terminal_step,
                    "onset_step": onset_step,
                    "first_alert_step": first_alert,
                    "alerted": alerted,
                    "lead_time_to_terminal": lead,
                    "alert_after_onset_lag": lag,
                    "false_alert": False,
                }
            )
    ep = pd.DataFrame(rows)
    summary = (
        ep.groupby(["mechanism", "model"], as_index=False)
        .agg(
            episodes=("episode_id", "nunique"),
            alert_rate=("alerted", "mean"),
            false_alert_rate=("false_alert", "mean"),
            median_lead_time=("lead_time_to_terminal", "median"),
            median_lag_after_onset=("alert_after_onset_lag", "median"),
        )
        .sort_values(["mechanism", "model"])
    )
    return ep, summary


def plot_representative(df: pd.DataFrame) -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    plot_path = FIGURES / "failure_aware_vppv_step_evidence.png"
    examples = [
        ("nominal", "none"),
        ("visual_estimation_bias", "perception_bias"),
        ("depth_scale_error", "depth_scale_error"),
        ("policy_approach_drift", "near_target_drift"),
    ]
    fig, axes = plt.subplots(len(examples), 3, figsize=(13, 9), sharex=False)
    for row_idx, (mechanism, failure) in enumerate(examples):
        subset = df[(df["mechanism_label"] == mechanism) & (df["failure"] == failure)]
        if failure == "none":
            subset = subset[subset["controller"] == "clean"]
        else:
            subset = subset[subset["controller"] == "perturbed"]
        if subset.empty:
            continue
        episode_id = subset["episode_id"].iloc[0]
        seq = subset[subset["episode_id"] == episode_id].sort_values("step")
        axes[row_idx, 0].plot(seq["step"], seq["distance"], color="#2f5d8c")
        axes[row_idx, 0].set_ylabel(mechanism)
        axes[row_idx, 0].set_title("distance")
        axes[row_idx, 1].plot(seq["step"], seq["visual_state_evidence"], label="visual", color="#a23b72")
        axes[row_idx, 1].plot(seq["step"], seq["depth_scale_evidence"], label="depth", color="#f18f01")
        axes[row_idx, 1].plot(seq["step"], seq["action_outcome_mismatch_evidence"], label="action-outcome", color="#048a81")
        axes[row_idx, 1].set_ylim(-0.03, 1.03)
        axes[row_idx, 1].set_title("evidence")
        alert_steps = seq[seq["composite_step_route"].ne("continue")]
        axes[row_idx, 2].plot(seq["step"], seq["composite_step_score"], color="#3b3b3b")
        axes[row_idx, 2].scatter(
            alert_steps["step"],
            alert_steps["composite_step_score"],
            color="#c1121f",
            s=14,
            label="route != continue",
        )
        axes[row_idx, 2].set_ylim(-0.03, 1.03)
        axes[row_idx, 2].set_title("composite route score")
    axes[0, 1].legend(loc="upper right", fontsize=8)
    axes[0, 2].legend(loc="upper right", fontsize=8)
    for ax in axes[-1, :]:
        ax.set_xlabel("step")
    fig.tight_layout()
    fig.savefig(plot_path, dpi=180)
    plt.close(fig)
    return plot_path


def write_report(
    route_summary: pd.DataFrame,
    ablation: pd.DataFrame,
    early_summary: pd.DataFrame,
    figure_path: Path,
) -> None:
    composite = route_summary[route_summary["model"] == "composite_step_route"].iloc[0]
    best_all = (
        ablation[(ablation["mechanism"] == "all") & (ablation["budget"] == 0.10)]
        .sort_values(["capture_rate", "precision_at_budget"], ascending=False)
        .head(5)
    )
    lines = [
        "# Failure-Aware VPPV Step Evidence",
        "",
        "This report completes the next evidence step after the composite episode",
        "router. It builds a VPPV-style step-level dataset focused on the three",
        "core mechanisms: visual state bias, depth-scale error, and high-level",
        "approach-policy drift. Jaw mechanics and object-drop examples are not the",
        "main target here.",
        "",
        "## Step-Level Composite Router",
        "",
        f"- Step rows: {int(composite['step_rows'])}",
        f"- Step-route consistency with weak mechanism rules: {composite['accuracy']:.3f}",
        f"- Step-route macro-F1: {composite['macro_f1']:.3f}",
        f"- Missed high-risk step rate: {composite['missed_high_risk_step_rate']:.3f}",
        f"- False alarm on nominal step rate: {composite['false_alarm_on_nominal_step_rate']:.3f}",
        "",
        "This is a weak-label consistency result, not an independently labeled",
        "surgeon-review benchmark. Its purpose is to check whether the evidence families",
        "separate the intended VPPV mechanisms and drive different routes.",
        "",
        "## Single-Evidence And Composite Comparison",
        "",
        markdown_table(route_summary),
        "",
        "## Fixed-Budget Step Capture",
        "",
        "Top evidence families at a 10% step-intervention budget:",
        "",
        markdown_table(best_all),
        "",
        "## Early Warning",
        "",
        markdown_table(early_summary),
        "",
        "## Mechanism Evidence Figure",
        "",
        f"![failure-aware VPPV step evidence]({figure_path.relative_to(ROOT / 'reports').as_posix()})",
        "",
        "## Output Tables",
        "",
        "- `reports/tables/failure_aware_vppv_step_dataset.csv`",
        "- `reports/tables/failure_aware_vppv_step_route_summary.csv`",
        "- `reports/tables/failure_aware_vppv_step_evidence_ablation.csv`",
        "- `reports/tables/failure_aware_vppv_step_early_warning.csv`",
        "- `reports/tables/failure_aware_vppv_step_early_warning_summary.csv`",
        "",
        "## Claim Boundary",
        "",
        "The dataset is built from SurRoL simulator traces and weak mechanism labels",
        "from controlled perturbations. It supports a VPPV-style reliability",
        "prototype, not real surgical deployment or surgeon-labeled validation.",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    df = load_step_dataset()
    route_summary = summarize_route_models(df)
    ablation = evidence_ablation(df)
    early_rows, early_summary = early_warning(df)
    figure_path = plot_representative(df)

    df.to_csv(TABLES / "failure_aware_vppv_step_dataset.csv", index=False)
    route_summary.to_csv(TABLES / "failure_aware_vppv_step_route_summary.csv", index=False)
    ablation.to_csv(TABLES / "failure_aware_vppv_step_evidence_ablation.csv", index=False)
    early_rows.to_csv(TABLES / "failure_aware_vppv_step_early_warning.csv", index=False)
    early_summary.to_csv(TABLES / "failure_aware_vppv_step_early_warning_summary.csv", index=False)
    write_report(route_summary, ablation, early_summary, figure_path)
    print(f"dataset={TABLES / 'failure_aware_vppv_step_dataset.csv'}")
    print(f"route_summary={TABLES / 'failure_aware_vppv_step_route_summary.csv'}")
    print(f"early_warning={TABLES / 'failure_aware_vppv_step_early_warning_summary.csv'}")
    print(f"figure={figure_path}")
    print(f"report={REPORT}")


if __name__ == "__main__":
    main()
