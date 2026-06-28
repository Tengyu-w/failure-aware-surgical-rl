from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "reports" / "tables"
FIG_DIR = ROOT / "reports" / "figures" / "failure_aware_vppv"
REPORT = ROOT / "reports" / "failure_aware_vppv_severity_holdout.md"
SOURCE = TABLES / "surrol_severity_sweep_paired.csv"

ROUTES = [
    "continue",
    "reobserve_reestimate",
    "depth_reestimate_or_cautious_approach",
    "low_gain_correction_or_replan",
]

MECHANISM_ROUTE = {
    "perception_bias": "reobserve_reestimate",
    "depth_scale_error": "depth_reestimate_or_cautious_approach",
    "near_target_drift": "low_gain_correction_or_replan",
}

MECHANISM_NAME = {
    "perception_bias": "visual_estimation_bias",
    "depth_scale_error": "depth_scale_error",
    "near_target_drift": "policy_approach_drift",
}

FAILURE_ORDER = ["perception_bias", "depth_scale_error", "near_target_drift"]
SEVERITY_ORDER = ["low", "medium", "high"]


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
    return float(sum(scores) / len(scores)) if scores else 0.0


def expected_route(row: pd.Series) -> str:
    if float(row["perturbed_success"]) >= 0.8:
        return "continue"
    return MECHANISM_ROUTE[str(row["failure"])]


def learn_intervention_boundary(train: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (task, failure), group in train.groupby(["task", "failure"]):
        risky = group[group["expected_route"].ne("continue")].sort_values("severity_rank")
        threshold = int(risky["severity_rank"].min()) if not risky.empty else 99
        rows.append(
            {
                "task": task,
                "failure": failure,
                "learned_min_intervention_rank": threshold,
                "learned_min_intervention_severity": "none" if threshold == 99 else SEVERITY_ORDER[threshold],
            }
        )
    return pd.DataFrame(rows)


def apply_boundary_router(df: pd.DataFrame, boundaries: pd.DataFrame) -> pd.Series:
    merged = df.merge(boundaries, on=["task", "failure"], how="left")
    route = pd.Series("continue", index=df.index, dtype=object)
    active = merged["severity_rank"] >= merged["learned_min_intervention_rank"].fillna(99)
    for failure, mechanism_route in MECHANISM_ROUTE.items():
        route.loc[active.to_numpy() & df["failure"].eq(failure).to_numpy()] = mechanism_route
    return route


def apply_family_only(df: pd.DataFrame) -> pd.Series:
    return df["failure"].map(MECHANISM_ROUTE).fillna("continue")


def apply_uniform_retry(df: pd.DataFrame) -> pd.Series:
    route = pd.Series("low_gain_correction_or_replan", index=df.index, dtype=object)
    route.loc[df["perturbed_success"].astype(float) >= 0.8] = "continue"
    return route


def evaluate(df: pd.DataFrame, pred: pd.Series, model: str, split: str) -> dict:
    labels = df["expected_route"]
    high = labels.ne("continue")
    return {
        "model": model,
        "split": split,
        "rows": len(df),
        "seeds_total": int(df["seeds"].sum()),
        "accuracy": float(pred.eq(labels).mean()),
        "macro_f1": macro_f1(labels, pred),
        "missed_intervention_rate": float((high & pred.eq("continue")).sum() / max(int(high.sum()), 1)),
        "false_intervention_rate": float((~high & pred.ne("continue")).sum() / max(int((~high).sum()), 1)),
        "route_diversity": int(pred.nunique()),
    }


def confusion(df: pd.DataFrame, pred: pd.Series, model: str, split: str) -> pd.DataFrame:
    table = pd.crosstab(df["expected_route"], pred, dropna=False)
    for route in ROUTES:
        if route not in table.columns:
            table[route] = 0
    table = table[ROUTES].reset_index()
    table.insert(0, "model", model)
    table.insert(1, "split", split)
    table.rename(columns={"expected_route": "expected"}, inplace=True)
    return table


def make_plot(df: pd.DataFrame, high_eval: pd.DataFrame) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 3, figsize=(15, 7), sharey="row", constrained_layout=True)
    for row, task in enumerate(["NeedlePick", "GauzeRetrieve"]):
        task_df = df[df["task"].eq(task)]
        for col, failure in enumerate(FAILURE_ORDER):
            ax = axes[row, col]
            group = task_df[task_df["failure"].eq(failure)].sort_values("severity_rank")
            ax.plot(group["severity"], group["perturbed_success"], marker="o", label="perturbed", color="#4f7cac")
            ax.plot(group["severity"], group["monitor_success"], marker="o", label="monitor", color="#2f8f5f")
            high_row = group[group["severity"].eq("high")]
            if not high_row.empty:
                ax.axvspan(1.5, 2.5, color="#e7b8a0", alpha=0.18)
            ax.set_title(f"{task}: {MECHANISM_NAME[failure]}")
            ax.set_ylim(-0.05, 1.05)
            ax.grid(alpha=0.25)
            if col == 0:
                ax.set_ylabel("success rate")
            if row == 1:
                ax.set_xlabel("severity")
            if row == 0 and col == 2:
                ax.legend(frameon=False, loc="lower left")
    fig.suptitle("Failure-Aware VPPV severity holdout: low/medium boundary, high held out", fontweight="bold")
    fig.savefig(FIG_DIR / "failure_aware_vppv_severity_holdout.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 3.6), constrained_layout=True)
    plot_df = high_eval[high_eval["split"].eq("high_holdout")].copy()
    ax.barh(plot_df["model"], plot_df["macro_f1"], color=["#4f7cac", "#c78b55", "#2f8f5f"][: len(plot_df)])
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("macro-F1")
    ax.set_title("High-severity held-out route classification")
    ax.grid(axis="x", alpha=0.25)
    for i, value in enumerate(plot_df["macro_f1"]):
        ax.text(float(value) + 0.02, i, f"{value:.3f}", va="center")
    fig.savefig(FIG_DIR / "failure_aware_vppv_severity_holdout_routes.png", dpi=180)
    plt.close(fig)


def write_report(
    detailed: pd.DataFrame,
    boundaries: pd.DataFrame,
    summary: pd.DataFrame,
    high_details: pd.DataFrame,
) -> None:
    high_summary = summary[summary["split"].eq("high_holdout")].copy()
    key_cols = [
        "task",
        "failure",
        "severity",
        "seeds",
        "perturbed_success",
        "monitor_success",
        "expected_route",
        "boundary_router_route",
        "family_only_route",
    ]
    lines = [
        "# Failure-Aware VPPV Severity-Held-Out Evaluation",
        "",
        "This report uses the existing SurRoL severity sweep as a lightweight",
        "boundary test. Low and medium severity rows are used to learn, for each",
        "task/failure pair, the first severity level where intervention becomes",
        "necessary. High severity is then held out and evaluated with frozen",
        "boundaries.",
        "",
        "## High-Severity Held-Out Results",
        "",
        markdown_table(high_summary),
        "",
        "## Learned Low/Medium Intervention Boundaries",
        "",
        markdown_table(boundaries),
        "",
        "## High-Severity Route Details",
        "",
        markdown_table(high_details[key_cols]),
        "",
        "## Interpretation",
        "",
        "- Depth-scale and visual/perception bias should not be treated as ordinary",
        "  execution drift. In the severity sweep, medium/high state-estimation",
        "  errors usually remain failed after monitor correction, so the safer route",
        "  is re-estimation or review.",
        "- Near-target drift is different: medium/high drift is recovered by the",
        "  monitor in both tasks, matching the route `low_gain_correction_or_replan`.",
        "- Low NeedlePick drift is a boundary case: it is already risky, but the",
        "  existing monitor does not trigger enough. That is useful calibration",
        "  evidence rather than a success claim.",
        "",
        "## Scope Boundary",
        "",
        "This is not an independent image-corruption benchmark. It is a severity",
        "sweep over simulator-injected mechanism proxies with 5 seeds per",
        "task/failure/severity. It strengthens the routing argument by checking",
        "whether the mechanism boundary found at low/medium severity remains",
        "valid at held-out high severity.",
        "",
        "## Output Tables And Figures",
        "",
        "- `reports/tables/failure_aware_vppv_severity_holdout_detailed.csv`",
        "- `reports/tables/failure_aware_vppv_severity_holdout_boundaries.csv`",
        "- `reports/tables/failure_aware_vppv_severity_holdout_summary.csv`",
        "- `reports/tables/failure_aware_vppv_severity_holdout_confusion.csv`",
        "- `reports/figures/failure_aware_vppv/failure_aware_vppv_severity_holdout.png`",
        "- `reports/figures/failure_aware_vppv/failure_aware_vppv_severity_holdout_routes.png`",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    df = pd.read_csv(SOURCE)
    df = df[df["failure"].isin(MECHANISM_ROUTE)].copy()
    df["expected_route"] = df.apply(expected_route, axis=1)
    df["mechanism_label"] = df["failure"].map(MECHANISM_NAME)

    train = df[df["severity_rank"].lt(2)].copy()
    high = df[df["severity_rank"].eq(2)].copy()
    boundaries = learn_intervention_boundary(train)

    detailed = df.copy()
    detailed["boundary_router_route"] = apply_boundary_router(detailed, boundaries).to_numpy()
    detailed["family_only_route"] = apply_family_only(detailed).to_numpy()
    detailed["uniform_retry_route"] = apply_uniform_retry(detailed).to_numpy()

    summary_rows = []
    confusion_rows = []
    for split_name, split_df in [("low_medium_calibration", train), ("high_holdout", high)]:
        predictions = {
            "boundary_router": apply_boundary_router(split_df, boundaries),
            "family_only": apply_family_only(split_df),
            "uniform_retry": apply_uniform_retry(split_df),
        }
        for model, pred in predictions.items():
            summary_rows.append(evaluate(split_df, pred, model, split_name))
            confusion_rows.append(confusion(split_df, pred, model, split_name))
    summary = pd.DataFrame(summary_rows)
    confusion_df = pd.concat(confusion_rows, ignore_index=True)

    TABLES.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    detailed.to_csv(TABLES / "failure_aware_vppv_severity_holdout_detailed.csv", index=False)
    boundaries.to_csv(TABLES / "failure_aware_vppv_severity_holdout_boundaries.csv", index=False)
    summary.to_csv(TABLES / "failure_aware_vppv_severity_holdout_summary.csv", index=False)
    confusion_df.to_csv(TABLES / "failure_aware_vppv_severity_holdout_confusion.csv", index=False)
    make_plot(df, summary)
    high_details = detailed[detailed["severity_rank"].eq(2)].copy()
    write_report(detailed, boundaries, summary, high_details)
    print(f"report={REPORT}")
    print(f"summary={TABLES / 'failure_aware_vppv_severity_holdout_summary.csv'}")
    print(f"figure={FIG_DIR / 'failure_aware_vppv_severity_holdout.png'}")


if __name__ == "__main__":
    main()
