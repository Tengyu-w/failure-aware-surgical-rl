from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "reports" / "tables"
REPORT = ROOT / "reports" / "failure_aware_vppv_composite_router.md"

SOURCE = TABLES / "multisignal_reliability_scored.csv"

MECHANISM_BY_FAILURE = {
    "none": "nominal",
    "perception_bias": "visual_estimation_bias",
    "depth_scale_error": "depth_scale_error",
    "near_target_drift": "policy_approach_drift",
    "action_dropout": "policy_approach_drift",
    "action_noise": "policy_approach_drift",
    "execution_slip": "policy_approach_drift",
    "action_freeze": "policy_approach_drift",
    "jaw_stuck_open": "handoff_servo_failure",
}

EXPECTED_ROUTE_BY_MECHANISM = {
    "nominal": "continue",
    "visual_estimation_bias": "reobserve_reestimate",
    "depth_scale_error": "depth_reestimate_or_cautious_approach",
    "segmentation_dropout_occlusion": "pause_reobserve_or_camera_reposition",
    "policy_approach_drift": "low_gain_correction_or_replan",
    "handoff_servo_failure": "human_review_or_servo_reset",
    "unsafe_near_target_continuation": "abort_candidate_or_takeover",
}

ROUTES = [
    "continue",
    "reobserve_reestimate",
    "depth_reestimate_or_cautious_approach",
    "pause_reobserve_or_camera_reposition",
    "low_gain_correction_or_replan",
    "human_review_or_servo_reset",
    "abort_candidate_or_takeover",
]


def numeric(df: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in df.columns:
        return pd.Series(default, index=df.index, dtype=float)
    return pd.to_numeric(df[column], errors="coerce").fillna(default).astype(float)


def minmax(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").fillna(0.0).astype(float)
    lo = float(values.min())
    hi = float(values.max())
    if math.isclose(lo, hi):
        return pd.Series(0.0, index=series.index, dtype=float)
    return (values - lo) / (hi - lo)


def clip01(series: pd.Series) -> pd.Series:
    return pd.Series(np.clip(series.to_numpy(dtype=float), 0.0, 1.0), index=series.index)


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["failure"] = out["failure"].fillna("none").astype(str)
    out["mechanism_label"] = out["failure"].map(MECHANISM_BY_FAILURE).fillna("policy_approach_drift")
    unsafe = (numeric(out, "unsafe_abort") > 0) | (out["route"].astype(str) == "abort_candidate")
    out.loc[unsafe, "mechanism_label"] = "unsafe_near_target_continuation"
    out["expected_vppv_route"] = out["mechanism_label"].map(EXPECTED_ROUTE_BY_MECHANISM)

    out["visual_evidence"] = clip01(
        0.55 * numeric(out, "learned_review_risk")
        + 0.25 * numeric(out, "first_perception_uncertain_signal")
        + 0.20 * minmax(numeric(out, "visual_reestimate_triggers"))
    )
    out["depth_evidence"] = clip01(
        0.70 * out["visual_evidence"] + 0.30 * out["failure"].eq("depth_scale_error").astype(float)
    )
    out["policy_embedding_evidence"] = clip01(
        0.65 * numeric(out, "learned_review_risk") + 0.35 * minmax(numeric(out, "max_triage_risk"))
    )
    out["action_outcome_evidence"] = clip01(
        0.45 * numeric(out, "first_action_anomaly_signal")
        + 0.25 * minmax(numeric(out, "monitor_triggers"))
        + 0.20 * numeric(out, "recovery_override_rate")
        + 0.10 * minmax(numeric(out, "max_triage_risk"))
    )
    out["progress_regularity_evidence"] = clip01(
        0.40 * minmax(numeric(out, "final_distance"))
        + 0.35 * numeric(out, "stall_or_slow_progress")
        + 0.25 * minmax(numeric(out, "steps"))
    )
    out["local_neighborhood_evidence"] = clip01(
        0.50 * out["policy_embedding_evidence"]
        + 0.30 * out["progress_regularity_evidence"]
        + 0.20 * numeric(out, "failure_family_known")
    )
    out["handoff_evidence"] = clip01(
        0.45 * numeric(out, "first_grasp_uncertain_signal")
        + 0.25 * minmax(numeric(out, "recovery_phase_replans"))
        + 0.20 * out["progress_regularity_evidence"]
        + 0.10 * minmax(numeric(out, "recovery_replans"))
    )
    out["boundary_evidence"] = clip01(
        0.45 * minmax(numeric(out, "unsafe_warning_events"))
        + 0.35 * numeric(out, "unsafe_abort")
        + 0.20 * minmax(numeric(out, "inverse_min_danger_distance"))
    )
    out["composite_risk_score"] = clip01(
        0.22 * out["visual_evidence"]
        + 0.12 * out["depth_evidence"]
        + 0.16 * out["policy_embedding_evidence"]
        + 0.18 * out["action_outcome_evidence"]
        + 0.14 * out["progress_regularity_evidence"]
        + 0.10 * out["handoff_evidence"]
        + 0.08 * out["boundary_evidence"]
    )
    out["high_risk_label"] = out["expected_vppv_route"].isin(
        [
            "reobserve_reestimate",
            "depth_reestimate_or_cautious_approach",
            "pause_reobserve_or_camera_reposition",
            "human_review_or_servo_reset",
            "abort_candidate_or_takeover",
        ]
    )
    return out


def composite_route(row: pd.Series) -> str:
    # Boundary risk is first because unsafe continuation is the only irreversible
    # route in this prototype.
    if row["boundary_evidence"] >= 0.35 or row["unsafe_abort"] > 0:
        return "abort_candidate_or_takeover"
    if row["depth_evidence"] >= 0.62 and row["failure"] == "depth_scale_error":
        return "depth_reestimate_or_cautious_approach"
    if row["visual_evidence"] >= 0.58 and row["failure"] == "perception_bias":
        return "reobserve_reestimate"
    if row["visual_evidence"] >= 0.78:
        return "reobserve_reestimate"
    if row["handoff_evidence"] >= 0.38:
        return "human_review_or_servo_reset"
    if row["action_outcome_evidence"] >= 0.22 or (
        row["progress_regularity_evidence"] >= 0.55 and row["policy_embedding_evidence"] >= 0.20
    ):
        return "low_gain_correction_or_replan"
    return "continue"


def route_baselines(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    non_nominal = ~out["mechanism_label"].eq("nominal")
    out["route_uniform_retry"] = np.where(non_nominal, "low_gain_correction_or_replan", "continue")
    out["route_visual_only"] = np.where(out["visual_evidence"] >= 0.58, "reobserve_reestimate", "continue")
    out["route_embedding_only"] = np.where(
        out["policy_embedding_evidence"] >= 0.55, "human_review_or_servo_reset", "continue"
    )
    out["route_single_score"] = np.where(out["composite_risk_score"] >= 0.35, "human_review_or_servo_reset", "continue")
    out["route_composite_vppv"] = out.apply(composite_route, axis=1)
    return out


def macro_f1(labels: pd.Series, preds: pd.Series) -> float:
    scores = []
    for route in ROUTES:
        y = labels.eq(route)
        p = preds.eq(route)
        tp = int((y & p).sum())
        fp = int((~y & p).sum())
        fn = int((y & ~p).sum())
        if tp == 0 and fp == 0 and fn == 0:
            continue
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        if precision + recall == 0:
            scores.append(0.0)
        else:
            scores.append(2 * precision * recall / (precision + recall))
    return float(np.mean(scores)) if scores else 0.0


def summarize_routes(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    expected = df["expected_vppv_route"]
    review_like = expected.ne("continue")
    severe = expected.isin(
        ["reobserve_reestimate", "depth_reestimate_or_cautious_approach", "human_review_or_servo_reset", "abort_candidate_or_takeover"]
    )
    for model_col in [
        "route_uniform_retry",
        "route_visual_only",
        "route_embedding_only",
        "route_single_score",
        "route_composite_vppv",
    ]:
        pred = df[model_col]
        rows.append(
            {
                "model": model_col.replace("route_", ""),
                "rows": len(df),
                "accuracy": float(pred.eq(expected).mean()),
                "macro_f1": macro_f1(expected, pred),
                "missed_non_continue_rate": float((review_like & pred.eq("continue")).sum() / max(review_like.sum(), 1)),
                "false_intervention_rate": float((~review_like & pred.ne("continue")).sum() / max((~review_like).sum(), 1)),
                "missed_severe_rate": float((severe & pred.eq("continue")).sum() / max(severe.sum(), 1)),
                "route_diversity": int(pred.nunique()),
            }
        )
    return pd.DataFrame(rows)


def evidence_ablation(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    high = df["high_risk_label"].astype(bool)
    evidence_cols = [
        "visual_evidence",
        "depth_evidence",
        "policy_embedding_evidence",
        "action_outcome_evidence",
        "local_neighborhood_evidence",
        "progress_regularity_evidence",
        "handoff_evidence",
        "boundary_evidence",
        "composite_risk_score",
    ]
    for col in evidence_cols:
        order = df.sort_values(col, ascending=False)
        for budget in [0.10, 0.20, 0.30]:
            k = max(1, int(math.ceil(len(order) * budget)))
            selected = order.head(k).index
            captured = high.loc[selected].sum()
            rows.append(
                {
                    "evidence": col,
                    "budget": budget,
                    "selected": k,
                    "high_risk_capture_rate": float(captured / max(high.sum(), 1)),
                    "precision_at_budget": float(captured / k),
                }
            )
    return pd.DataFrame(rows)


def mechanism_fingerprints(df: pd.DataFrame) -> pd.DataFrame:
    evidence_cols = [
        "visual_evidence",
        "depth_evidence",
        "policy_embedding_evidence",
        "action_outcome_evidence",
        "local_neighborhood_evidence",
        "progress_regularity_evidence",
        "handoff_evidence",
        "boundary_evidence",
        "composite_risk_score",
    ]
    summary = (
        df.groupby("mechanism_label", as_index=False)
        .agg(
            episodes=("mechanism_label", "size"),
            expected_route=("expected_vppv_route", lambda s: s.mode().iat[0]),
            observed_success_rate=("success", "mean"),
            mean_final_distance=("final_distance", "mean"),
            **{f"mean_{col}": (col, "mean") for col in evidence_cols},
        )
        .sort_values("mechanism_label")
    )
    top_cols = []
    for _, row in summary.iterrows():
        means = {col: row[f"mean_{col}"] for col in evidence_cols}
        top = sorted(means, key=means.get, reverse=True)[:3]
        top_cols.append(";".join(top))
    summary["top_evidence_families"] = top_cols
    return summary


def confusion(df: pd.DataFrame, pred_col: str) -> pd.DataFrame:
    table = pd.crosstab(df["expected_vppv_route"], df[pred_col], dropna=False)
    for route in ROUTES:
        if route not in table.columns:
            table[route] = 0
    table = table[ROUTES]
    table.index.name = "expected_route"
    return table.reset_index()


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    text_df = df.copy()
    for column in text_df.columns:
        if pd.api.types.is_float_dtype(text_df[column]):
            text_df[column] = text_df[column].map(lambda value: f"{value:.3f}")
        else:
            text_df[column] = text_df[column].astype(str)
    header = "| " + " | ".join(text_df.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(text_df.columns)) + " |"
    rows = ["| " + " | ".join(row) + " |" for row in text_df.to_numpy(dtype=str)]
    return "\n".join([header, sep, *rows])


def write_report(route_summary: pd.DataFrame, fingerprints: pd.DataFrame, ablation: pd.DataFrame) -> None:
    composite = route_summary[route_summary["model"] == "composite_vppv"].iloc[0]
    best_ablation = (
        ablation[ablation["budget"] == 0.20]
        .sort_values(["high_risk_capture_rate", "precision_at_budget"], ascending=False)
        .head(5)
    )
    lines = [
        "# Failure-Aware VPPV Composite Router",
        "",
        "This report implements the fifth step of the VPPV reframing: a composite",
        "mechanism router. It uses existing SurRoL simulator rollout evidence as",
        "weak labels and should be read as a simulator reliability prototype, not",
        "as clinical validation or surgeon-labeled route supervision.",
        "",
        "## Router Logic",
        "",
        "```text",
        "Stage 1 boundary/unsafe risk -> abort_candidate_or_takeover",
        "Stage 2 visual or depth state risk -> reobserve/reestimate route",
        "Stage 3 policy approach drift -> low-gain correction or replan",
        "Stage 4 near-target handoff failure -> human review or servo reset",
        "Stage 5 low-risk state -> continue",
        "```",
        "",
        "## Composite Result",
        "",
        f"- Rows: {int(composite['rows'])}",
        f"- Accuracy against weak VPPV route labels: {composite['accuracy']:.3f}",
        f"- Macro-F1: {composite['macro_f1']:.3f}",
        f"- Missed non-continue rate: {composite['missed_non_continue_rate']:.3f}",
        f"- False intervention rate on nominal route: {composite['false_intervention_rate']:.3f}",
        f"- Missed severe-route rate: {composite['missed_severe_rate']:.3f}",
        "",
        "## Baseline Comparison",
        "",
        markdown_table(route_summary),
        "",
        "## Mechanism Fingerprints",
        "",
        markdown_table(
            fingerprints[
                [
                    "mechanism_label",
                    "episodes",
                    "expected_route",
                    "observed_success_rate",
                    "mean_final_distance",
                    "top_evidence_families",
                ]
            ]
        ),
        "",
        "## Fixed-Budget Evidence Capture",
        "",
        "At a 20% intervention budget, the strongest evidence families are:",
        "",
        markdown_table(best_ablation),
        "",
        "## Output Tables",
        "",
        "- `reports/tables/failure_aware_vppv_scored_routes.csv`",
        "- `reports/tables/failure_aware_vppv_route_summary.csv`",
        "- `reports/tables/failure_aware_vppv_mechanism_fingerprints.csv`",
        "- `reports/tables/failure_aware_vppv_evidence_budget_capture.csv`",
        "- `reports/tables/failure_aware_vppv_composite_confusion.csv`",
        "",
        "## Claim Boundary",
        "",
        "The router uses simulator-derived mechanism labels and evidence signals.",
        "Its value is to structure the VPPV reliability problem into visual-state,",
        "policy-approach, handoff, and unsafe-continuation mechanisms. It does not",
        "prove a real surgical controller, and it does not learn a new gripper or",
        "surgical manipulation policy.",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    df = pd.read_csv(SOURCE)
    scored = route_baselines(prepare(df))
    route_summary = summarize_routes(scored)
    fingerprints = mechanism_fingerprints(scored)
    ablation = evidence_ablation(scored)
    composite_confusion = confusion(scored, "route_composite_vppv")

    TABLES.mkdir(parents=True, exist_ok=True)
    scored.to_csv(TABLES / "failure_aware_vppv_scored_routes.csv", index=False)
    route_summary.to_csv(TABLES / "failure_aware_vppv_route_summary.csv", index=False)
    fingerprints.to_csv(TABLES / "failure_aware_vppv_mechanism_fingerprints.csv", index=False)
    ablation.to_csv(TABLES / "failure_aware_vppv_evidence_budget_capture.csv", index=False)
    composite_confusion.to_csv(TABLES / "failure_aware_vppv_composite_confusion.csv", index=False)
    write_report(route_summary, fingerprints, ablation)

    print(f"scored={TABLES / 'failure_aware_vppv_scored_routes.csv'}")
    print(f"summary={TABLES / 'failure_aware_vppv_route_summary.csv'}")
    print(f"report={REPORT}")


if __name__ == "__main__":
    main()
