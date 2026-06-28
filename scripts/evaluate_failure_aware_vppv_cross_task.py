from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "reports" / "tables"
REPORT = ROOT / "reports" / "failure_aware_vppv_cross_task_generalization.md"
SOURCE = TABLES / "failure_aware_vppv_step_dataset.csv"

TASKS = ["NeedlePick", "GauzeRetrieve"]
ROUTES = [
    "continue",
    "reobserve_reestimate",
    "depth_reestimate_or_cautious_approach",
    "low_gain_correction_or_replan",
]

EVIDENCE_TO_MECHANISM = {
    "visual_state_evidence": "visual_estimation_bias",
    "depth_scale_evidence": "depth_scale_error",
    "policy_embedding_proxy_evidence": "policy_approach_drift",
    "action_outcome_mismatch_evidence": "policy_approach_drift",
    "composite_step_score": "all",
}


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
        scores.append(0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall))
    return float(np.mean(scores)) if scores else 0.0


def apply_router(df: pd.DataFrame, thresholds: dict[str, float]) -> pd.Series:
    route = pd.Series("continue", index=df.index, dtype=object)
    depth = df["depth_scale_evidence"] >= thresholds["depth"]
    visual = (df["visual_state_evidence"] >= thresholds["visual"]) & ~depth
    policy = (
        (df["policy_embedding_proxy_evidence"] >= thresholds["policy"])
        | (df["action_outcome_mismatch_evidence"] >= thresholds["action"])
    ) & ~depth & ~visual
    route.loc[depth] = "depth_reestimate_or_cautious_approach"
    route.loc[visual] = "reobserve_reestimate"
    route.loc[policy] = "low_gain_correction_or_replan"
    return route


def evaluate(df: pd.DataFrame, pred: pd.Series, split_name: str, thresholds: dict[str, float]) -> dict:
    labels = df["expected_step_route"]
    high = labels.ne("continue")
    return {
        "split": split_name,
        "rows": len(df),
        "threshold_visual": thresholds["visual"],
        "threshold_depth": thresholds["depth"],
        "threshold_policy": thresholds["policy"],
        "threshold_action": thresholds["action"],
        "accuracy": float(pred.eq(labels).mean()),
        "macro_f1": macro_f1(labels, pred),
        "missed_high_risk_step_rate": float((high & pred.eq("continue")).sum() / max(high.sum(), 1)),
        "false_alarm_on_continue_rate": float((~high & pred.ne("continue")).sum() / max((~high).sum(), 1)),
        "route_diversity": int(pred.nunique()),
    }


def calibrate_thresholds(df: pd.DataFrame) -> tuple[dict[str, float], pd.DataFrame]:
    grid = {
        "visual": [0.45, 0.50, 0.55, 0.60, 0.65, 0.70],
        "depth": [0.45, 0.55, 0.65, 0.70, 0.80, 0.90],
        "policy": [0.35, 0.40, 0.45, 0.50, 0.52, 0.55, 0.60],
        "action": [0.25, 0.30, 0.35, 0.40, 0.45],
    }
    rows = []
    best = None
    best_score = -1.0
    for values in itertools.product(grid["visual"], grid["depth"], grid["policy"], grid["action"]):
        thresholds = dict(zip(["visual", "depth", "policy", "action"], values))
        pred = apply_router(df, thresholds)
        metrics = evaluate(df, pred, "calibration", thresholds)
        rows.append(metrics)
        score = metrics["macro_f1"] - 0.25 * metrics["false_alarm_on_continue_rate"]
        if score > best_score:
            best_score = score
            best = thresholds
    assert best is not None
    return best, pd.DataFrame(rows)


def candidate_mask_for_evidence(task_df: pd.DataFrame, evidence: str) -> pd.Series:
    """Mechanism-aware candidate gates used only for budget analysis.

    The raw visual score is intentionally not a standalone mechanism label:
    depth-scale corruption can also create large visual-state residuals.  The
    gated budget view asks whether the evidence is useful after higher-priority
    depth evidence has been screened out, which matches the composite router.
    """
    mask = pd.Series(True, index=task_df.index)
    if evidence == "visual_state_evidence":
        mask &= task_df["depth_scale_evidence"].astype(float) < 0.45
    elif evidence in {"policy_embedding_proxy_evidence", "action_outcome_mismatch_evidence"}:
        mask &= task_df["depth_scale_evidence"].astype(float) < 0.45
        mask &= task_df["visual_state_evidence"].astype(float) < 0.45
    return mask


def rank_budget_capture(
    task_df: pd.DataFrame,
    positives: pd.Series,
    evidence: str,
    budget: float,
    ranking_policy: str,
) -> dict:
    if ranking_policy == "mechanism_gated_rank":
        candidates = task_df[candidate_mask_for_evidence(task_df, evidence)].copy()
    else:
        candidates = task_df.copy()
    scores = candidates[evidence].astype(float)
    order = candidates.assign(score=scores).sort_values("score", ascending=False)
    k = max(1, int(np.ceil(len(task_df) * budget)))
    k = min(k, len(order))
    selected = order.head(k).index
    captured = int(positives.loc[selected].sum())
    return {
        "ranking_policy": ranking_policy,
        "selected_steps": k,
        "capture_rate": float(captured / max(int(positives.sum()), 1)),
        "precision_at_budget": float(captured / max(k, 1)),
    }


def evidence_transfer(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for task, task_df in df.groupby("task"):
        for evidence, target_mechanism in EVIDENCE_TO_MECHANISM.items():
            if target_mechanism == "all":
                positives = task_df["high_risk_step"].astype(bool)
            else:
                positives = (task_df["mechanism_label"] == target_mechanism) & task_df["high_risk_step"].astype(bool)
            for budget in [0.05, 0.10, 0.20]:
                for ranking_policy in ["global_rank", "mechanism_gated_rank"]:
                    metrics = rank_budget_capture(task_df, positives, evidence, budget, ranking_policy)
                    rows.append(
                        {
                            "task": task,
                            "evidence": evidence,
                            "target_mechanism": target_mechanism,
                            "budget": budget,
                            **metrics,
                        }
                    )
    return pd.DataFrame(rows)


def route_confusion(df: pd.DataFrame, pred: pd.Series, label: str) -> pd.DataFrame:
    table = pd.crosstab(df["expected_step_route"], pred, dropna=False)
    for route in ROUTES:
        if route not in table.columns:
            table[route] = 0
    table = table[ROUTES].reset_index()
    table.insert(0, "comparison", label)
    table.rename(columns={"expected_step_route": "expected_route"}, inplace=True)
    return table


def write_report(summary: pd.DataFrame, transfer: pd.DataFrame) -> None:
    test_rows = summary[summary["split"].str.contains("test_on")]
    best_transfer = (
        transfer[
            (transfer["budget"] == 0.10)
            & (transfer["target_mechanism"].ne("all"))
            & (transfer["ranking_policy"] == "mechanism_gated_rank")
        ]
        .sort_values(["task", "capture_rate", "precision_at_budget"], ascending=[True, False, False])
        .groupby("task", as_index=False)
        .head(6)
    )
    global_visual = transfer[
        (transfer["budget"] == 0.10)
        & (transfer["evidence"] == "visual_state_evidence")
        & (transfer["ranking_policy"] == "global_rank")
    ][["task", "evidence", "target_mechanism", "ranking_policy", "capture_rate", "precision_at_budget"]]
    lines = [
        "# Failure-Aware VPPV Cross-Task Generalization",
        "",
        "This report tests whether the step-level evidence router transfers across",
        "SurRoL tasks. Thresholds are calibrated on one task and frozen when testing",
        "on the other task. This is stronger than within-task weak-label consistency,",
        "but still uses simulator-derived mechanism labels.",
        "",
        "## Cross-Task Router Results",
        "",
        markdown_table(test_rows),
        "",
        "## Mechanism-Gated Evidence Transfer At 10% Budget",
        "",
        markdown_table(best_transfer),
        "",
        "## Visual Evidence Confounding Check",
        "",
        markdown_table(global_visual),
        "",
        "## Interpretation",
        "",
        "- Visual evidence is useful only after the depth gate. As a global ranker,",
        "  it is confounded because depth-scale corruption also creates large",
        "  visual-state residuals.",
        "- Depth evidence is the first-stage gate. This is why the router does not",
        "  treat every visual residual as the same recovery mechanism.",
        "- Policy approach drift transfers through action-outcome and policy-proxy",
        "  evidence, but the signal strength differs by task.",
        "- This still is not an independent expert-label benchmark. It tests whether",
        "  the same mechanism evidence can be calibrated on one surgical task and",
        "  remain useful on another.",
        "",
        "## Output Tables",
        "",
        "- `reports/tables/failure_aware_vppv_cross_task_summary.csv`",
        "- `reports/tables/failure_aware_vppv_cross_task_threshold_sweep.csv`",
        "- `reports/tables/failure_aware_vppv_cross_task_evidence_transfer.csv`",
        "- `reports/tables/failure_aware_vppv_cross_task_confusion.csv`",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    df = pd.read_csv(SOURCE)
    df = df[df["task"].isin(TASKS)].copy()
    summary_rows = []
    sweep_rows = []
    confusions = []
    for train_task, test_task in [("NeedlePick", "GauzeRetrieve"), ("GauzeRetrieve", "NeedlePick")]:
        train = df[df["task"] == train_task].copy()
        test = df[df["task"] == test_task].copy()
        thresholds, sweep = calibrate_thresholds(train)
        sweep.insert(0, "train_task", train_task)
        sweep_rows.append(sweep)
        train_pred = apply_router(train, thresholds)
        test_pred = apply_router(test, thresholds)
        summary_rows.append(evaluate(train, train_pred, f"calibrate_on_{train_task}", thresholds))
        summary_rows[-1]["train_task"] = train_task
        summary_rows[-1]["test_task"] = train_task
        summary_rows.append(evaluate(test, test_pred, f"test_on_{test_task}", thresholds))
        summary_rows[-1]["train_task"] = train_task
        summary_rows[-1]["test_task"] = test_task
        confusions.append(route_confusion(test, test_pred, f"{train_task}_to_{test_task}"))

    summary = pd.DataFrame(summary_rows)
    sweep_all = pd.concat(sweep_rows, ignore_index=True)
    transfer = evidence_transfer(df)
    confusion = pd.concat(confusions, ignore_index=True)

    summary.to_csv(TABLES / "failure_aware_vppv_cross_task_summary.csv", index=False)
    sweep_all.to_csv(TABLES / "failure_aware_vppv_cross_task_threshold_sweep.csv", index=False)
    transfer.to_csv(TABLES / "failure_aware_vppv_cross_task_evidence_transfer.csv", index=False)
    confusion.to_csv(TABLES / "failure_aware_vppv_cross_task_confusion.csv", index=False)
    write_report(summary, transfer)
    print(f"summary={TABLES / 'failure_aware_vppv_cross_task_summary.csv'}")
    print(f"transfer={TABLES / 'failure_aware_vppv_cross_task_evidence_transfer.csv'}")
    print(f"report={REPORT}")


if __name__ == "__main__":
    main()
