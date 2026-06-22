from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MEMORY_PRED = ROOT / "reports" / "tables" / "surrol_reliability_memory_predictions.csv"
MEMORY_EMB = ROOT / "reports" / "tables" / "surrol_reliability_memory_embeddings.csv"
LEARNED_RISK = ROOT / "reports" / "tables" / "surrol_learned_risk_head_scored.csv"


def minmax(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").fillna(0.0)
    lo = float(values.min())
    hi = float(values.max())
    if hi - lo < 1e-12:
        return pd.Series(np.zeros(len(values)), index=values.index)
    return (values - lo) / (hi - lo)


def load_memory() -> pd.DataFrame:
    pred = pd.read_csv(MEMORY_PRED)
    emb = pd.read_csv(MEMORY_EMB)
    candidate_keys = ["suite", "task", "failure", "controller", "seed", "episode", "route", "family"]
    keys = [col for col in candidate_keys if col in pred.columns and col in emb.columns]
    cols = keys + [
        "success",
        "final_distance",
        "steps",
        "max_triage_risk",
        "monitor_triggers",
        "recovery_phase_replans",
        "recovery_override_rate",
        "unsafe_warning_events",
        "min_danger_distance",
        "unsafe_abort",
        "source",
    ]
    available = [col for col in cols if col in emb.columns]
    out = pred.merge(emb[available], on=keys, how="left", suffixes=("", "_emb"))
    return out


def load_learned_risk() -> pd.DataFrame:
    if not LEARNED_RISK.exists():
        return pd.DataFrame()
    df = pd.read_csv(LEARNED_RISK)
    score_candidates = [
        "learned_review_risk",
        "review_probability",
        "risk_probability",
        "predicted_probability",
        "score",
    ]
    score_col = next((col for col in score_candidates if col in df.columns), None)
    if score_col is None:
        numeric_cols = [
            col
            for col in df.columns
            if col not in {"suite", "task", "failure", "controller", "route", "family"}
            and pd.api.types.is_numeric_dtype(df[col])
        ]
        score_col = numeric_cols[-1] if numeric_cols else None
    if score_col is None:
        return pd.DataFrame()
    keys = ["suite", "task", "failure", "controller", "seed", "episode"]
    available_keys = [col for col in keys if col in df.columns]
    return df[available_keys + [score_col]].rename(columns={score_col: "learned_review_score"})


def assign_level(row: pd.Series) -> str:
    if row["abort_evidence"] >= 0.70:
        return "abort_candidate"
    if row["review_evidence"] >= 0.62:
        return "human_review"
    if row["recovery_evidence"] >= 0.45:
        return "auto_recovery"
    return "auto_execute"


def assign_reason(row: pd.Series) -> str:
    if row["risk_level"] == "abort_candidate":
        return "unsafe_abort_or_close_to_forbidden_zone"
    if row["risk_level"] == "human_review":
        return "visual_state_or_memory_uncertainty_requires_review"
    if row["risk_level"] == "auto_recovery":
        return "recoverable_execution_drift_or_monitor_trigger"
    return "nominal_or_low_risk_execution"


def main() -> None:
    table_dir = ROOT / "reports" / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    df = load_memory()
    learned = load_learned_risk()
    if not learned.empty:
        merge_keys = [
            col
            for col in ["suite", "task", "failure", "controller", "seed", "episode"]
            if col in learned.columns and col in df.columns
        ]
        if merge_keys:
            df = df.merge(learned, on=merge_keys, how="left")
    if "learned_review_score" not in df.columns:
        df["learned_review_score"] = 0.0
    df["learned_review_score"] = pd.to_numeric(df["learned_review_score"], errors="coerce").fillna(0.0)

    df["family_distance_norm"] = minmax(df["family_distance"])
    df["route_distance_norm"] = minmax(df["route_distance"])
    df["danger_closeness"] = 1.0 - minmax(df["min_danger_distance"].fillna(df["min_danger_distance"].max()))
    df["unsafe_abort"] = pd.to_numeric(df.get("unsafe_abort", 0.0), errors="coerce").fillna(0.0)
    df["unsafe_warning_events"] = pd.to_numeric(df.get("unsafe_warning_events", 0.0), errors="coerce").fillna(0.0)
    df["monitor_triggers"] = pd.to_numeric(df.get("monitor_triggers", 0.0), errors="coerce").fillna(0.0)

    pred_route = df["pred_route"].astype(str)
    pred_family = df["pred_family"].astype(str)
    df["abort_evidence"] = np.maximum.reduce(
        [
            (pred_route == "abort_candidate").astype(float),
            (pred_family == "unsafe_abort").astype(float),
            (df["unsafe_warning_events"] > 0).astype(float) * 0.45,
            df["danger_closeness"].astype(float) * 0.70,
        ]
    )
    df["review_evidence"] = np.maximum.reduce(
        [
            (pred_route == "human_review").astype(float),
            (pred_family == "visual_state_error").astype(float),
            df["learned_review_score"].astype(float),
            df["family_distance_norm"].astype(float) * 0.60,
            df["route_distance_norm"].astype(float) * 0.50,
        ]
    )
    df["recovery_evidence"] = np.maximum.reduce(
        [
            (pred_route == "auto_recovery").astype(float),
            (pred_family == "execution_drift").astype(float) * 0.80,
            (df["monitor_triggers"] > 0).astype(float) * 0.55,
        ]
    )
    df["risk_level"] = df.apply(assign_level, axis=1)
    df["risk_reason"] = df.apply(assign_reason, axis=1)

    summary = (
        df.groupby(["risk_level"], as_index=False)
        .agg(
            episodes=("risk_level", "size"),
            success_mean=("success", "mean"),
            unsafe_abort_rate=("unsafe_abort", "mean"),
            final_distance_mean=("final_distance", "mean"),
            max_abort_evidence=("abort_evidence", "max"),
            max_review_evidence=("review_evidence", "max"),
            max_recovery_evidence=("recovery_evidence", "max"),
        )
        .sort_values("risk_level")
    )
    cross = pd.crosstab(df["route"], df["risk_level"]).reset_index()

    scored_out = table_dir / "surrol_risk_level_scored.csv"
    summary_out = table_dir / "surrol_risk_level_summary.csv"
    cross_out = table_dir / "surrol_risk_level_by_original_route.csv"
    df.to_csv(scored_out, index=False)
    summary.to_csv(summary_out, index=False)
    cross.to_csv(cross_out, index=False)

    report = ROOT / "reports" / "surrol_risk_level_calibration_round25_zh.md"
    lines = [
        "# SurRoL Risk-Level Calibration",
        "",
        "## 一句话结论",
        "",
        (
            "这一步把原来的 recovery/abort 二分思路改成四档风险路由：auto_execute、auto_recovery、"
            "human_review、abort_candidate。它更接近 ECG 项目里的分级处理逻辑：低风险自动执行，"
            "可恢复漂移自动恢复，视觉/状态不确定交给复查，接近 forbidden zone 或 unsafe abort 的片段进入候选中止。"
        ),
        "",
        "## Risk-Level Summary",
        "",
        "| Risk level | Episodes | Success | Unsafe abort | Final distance |",
        "|---|---:|---:|---:|---:|",
    ]
    for _, row in summary.iterrows():
        lines.append(
            f"| {row['risk_level']} | {int(row['episodes'])} | {row['success_mean']:.3f} | "
            f"{row['unsafe_abort_rate']:.3f} | {row['final_distance_mean']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Leakage Control",
            "",
            (
                "Risk-level assignment does not use the ground-truth route or family labels. Those labels are kept only for post-hoc "
                "evaluation tables. The routing evidence comes from predicted memory labels, embedding distances, learned risk score, "
                "monitor triggers, unsafe-warning counts, and proximity to the forbidden-zone proxy."
            ),
            "",
            "## Interpretation",
            "",
            "- auto_execute is the low-risk route for nominal or clean-looking execution.",
            "- auto_recovery is used when the memory says the episode resembles recoverable execution drift.",
            "- human_review is used for visual-state error or high memory uncertainty, matching the review/re-estimation branch.",
            "- abort_candidate is intentionally conservative: it prioritizes not missing unsafe-abort-like states, even at the cost of false alarms.",
            "",
            "## Limitations",
            "",
            "- The current score is a transparent calibration rule over logs, not a validated clinical safety model.",
            "- Unsafe-zone labels still come from a geometric forbidden-zone proxy, not tissue force or deformation.",
            "- Learned risk scores are merged when available, but the present routing still relies heavily on synthetic labels and simulator state features.",
            "",
            "## Outputs",
            "",
            "- `reports/tables/surrol_risk_level_scored.csv`",
            "- `reports/tables/surrol_risk_level_summary.csv`",
            "- `reports/tables/surrol_risk_level_by_original_route.csv`",
        ]
    )
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"scored={scored_out}")
    print(f"summary={summary_out}")
    print(f"cross={cross_out}")
    print(f"report={report}")


if __name__ == "__main__":
    main()
