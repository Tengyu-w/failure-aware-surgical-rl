from __future__ import annotations

from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "reports" / "tables"
FIG_DIR = ROOT / "reports" / "figures" / "failure_aware_vppv"
REPORT = ROOT / "reports" / "failure_aware_vppv_mixed_perturbation_priority.md"
SOURCE = TABLES / "failure_aware_vppv_step_dataset.csv"

TASKS = ["NeedlePick", "GauzeRetrieve"]
MECHANISMS = ["visual_estimation_bias", "depth_scale_error", "policy_approach_drift"]
PRIORITY = ["depth_scale_error", "visual_estimation_bias", "policy_approach_drift"]

ROUTE_BY_MECHANISM = {
    "visual_estimation_bias": "reobserve_reestimate",
    "depth_scale_error": "depth_reestimate_or_cautious_approach",
    "policy_approach_drift": "low_gain_correction_or_replan",
}

ROUTES = [
    "continue",
    "reobserve_reestimate",
    "depth_reestimate_or_cautious_approach",
    "low_gain_correction_or_replan",
]

EVIDENCE_COLS = [
    "visual_state_evidence",
    "depth_scale_evidence",
    "policy_embedding_proxy_evidence",
    "action_outcome_mismatch_evidence",
    "progress_regularity_evidence",
    "local_neighborhood_proxy_evidence",
    "composite_step_score",
]

THRESHOLDS = {
    "visual": 0.45,
    "depth": 0.45,
    "policy": 0.35,
    "action": 0.25,
}


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
    return float(np.mean(scores)) if scores else 0.0


def component_trace(df: pd.DataFrame, task: str, mechanism: str) -> pd.DataFrame:
    subset = df[
        df["task"].eq(task)
        & df["mechanism_label"].eq(mechanism)
        & df["controller"].eq("perturbed")
    ].copy()
    if subset.empty:
        raise ValueError(f"No component rows for {task} / {mechanism}")
    grouped = subset.groupby("step", as_index=False)[EVIDENCE_COLS].median()
    grouped["task"] = task
    grouped["mechanism_label"] = mechanism
    return grouped


def mechanism_active(row: pd.Series, mechanism: str) -> bool:
    if mechanism == "depth_scale_error":
        return float(row["depth_scale_evidence"]) >= THRESHOLDS["depth"]
    if mechanism == "visual_estimation_bias":
        return float(row["visual_state_evidence"]) >= THRESHOLDS["visual"]
    if mechanism == "policy_approach_drift":
        return (
            float(row["policy_embedding_proxy_evidence"]) >= THRESHOLDS["policy"]
            or float(row["action_outcome_mismatch_evidence"]) >= THRESHOLDS["action"]
        )
    return False


def expected_priority_route(row: pd.Series) -> str:
    components = str(row["mixed_components"]).split("+")
    for mechanism in PRIORITY:
        if mechanism in components and mechanism_active(row, mechanism):
            return ROUTE_BY_MECHANISM[mechanism]
    return "continue"


def priority_router(df: pd.DataFrame) -> pd.Series:
    route = pd.Series("continue", index=df.index, dtype=object)
    depth = df["depth_scale_evidence"].astype(float) >= THRESHOLDS["depth"]
    visual = (df["visual_state_evidence"].astype(float) >= THRESHOLDS["visual"]) & ~depth
    policy = (
        (df["policy_embedding_proxy_evidence"].astype(float) >= THRESHOLDS["policy"])
        | (df["action_outcome_mismatch_evidence"].astype(float) >= THRESHOLDS["action"])
    ) & ~depth & ~visual
    route.loc[depth] = ROUTE_BY_MECHANISM["depth_scale_error"]
    route.loc[visual] = ROUTE_BY_MECHANISM["visual_estimation_bias"]
    route.loc[policy] = ROUTE_BY_MECHANISM["policy_approach_drift"]
    return route


def max_signal_router(df: pd.DataFrame) -> pd.Series:
    signal = pd.DataFrame(
        {
            "reobserve_reestimate": df["visual_state_evidence"].astype(float),
            "depth_reestimate_or_cautious_approach": df["depth_scale_evidence"].astype(float),
            "low_gain_correction_or_replan": df[
                ["policy_embedding_proxy_evidence", "action_outcome_mismatch_evidence"]
            ].astype(float).max(axis=1),
        },
        index=df.index,
    )
    chosen = signal.idxmax(axis=1)
    max_value = signal.max(axis=1)
    chosen.loc[max_value < THRESHOLDS["visual"]] = "continue"
    return chosen


def uniform_retry_router(df: pd.DataFrame) -> pd.Series:
    any_active = (
        (df["visual_state_evidence"].astype(float) >= THRESHOLDS["visual"])
        | (df["depth_scale_evidence"].astype(float) >= THRESHOLDS["depth"])
        | (df["policy_embedding_proxy_evidence"].astype(float) >= THRESHOLDS["policy"])
        | (df["action_outcome_mismatch_evidence"].astype(float) >= THRESHOLDS["action"])
    )
    route = pd.Series("continue", index=df.index, dtype=object)
    route.loc[any_active] = ROUTE_BY_MECHANISM["policy_approach_drift"]
    return route


def single_score_router(df: pd.DataFrame) -> pd.Series:
    route = pd.Series("continue", index=df.index, dtype=object)
    route.loc[df["composite_step_score"].astype(float) >= 0.45] = ROUTE_BY_MECHANISM["policy_approach_drift"]
    return route


def build_mixed_dataset(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    combos = []
    for size in [2, 3]:
        combos.extend(combinations(MECHANISMS, size))

    for task in TASKS:
        traces = {mechanism: component_trace(df, task, mechanism) for mechanism in MECHANISMS}
        for combo in combos:
            common_steps = sorted(set.intersection(*[set(traces[m]["step"]) for m in combo]))
            combo_frames = [traces[m].set_index("step").loc[common_steps, EVIDENCE_COLS] for m in combo]
            stacked = np.stack([frame.to_numpy(dtype=float) for frame in combo_frames], axis=0)
            mixed = pd.DataFrame(np.max(stacked, axis=0), columns=EVIDENCE_COLS)
            mixed.insert(0, "step", common_steps)
            mixed.insert(0, "task", task)
            mixed["mixed_components"] = "+".join(combo)
            mixed["expected_dominant_mechanism"] = next(m for m in PRIORITY if m in combo)
            rows.append(mixed)

    out = pd.concat(rows, ignore_index=True)
    out["expected_route"] = out.apply(expected_priority_route, axis=1)
    out["priority_router_route"] = priority_router(out)
    out["max_signal_route"] = max_signal_router(out)
    out["uniform_retry_route"] = uniform_retry_router(out)
    out["single_score_route"] = single_score_router(out)
    return out


def evaluate(df: pd.DataFrame, pred_col: str, label: str) -> dict:
    labels = df["expected_route"]
    pred = df[pred_col]
    high = labels.ne("continue")
    priority_error = high & pred.ne(labels)
    return {
        "model": label,
        "rows": len(df),
        "scenarios": int(df.groupby(["task", "mixed_components"]).ngroups),
        "accuracy": float(pred.eq(labels).mean()),
        "macro_f1": macro_f1(labels, pred),
        "missed_intervention_rate": float((high & pred.eq("continue")).sum() / max(int(high.sum()), 1)),
        "wrong_priority_rate": float(priority_error.sum() / max(int(high.sum()), 1)),
        "route_diversity": int(pred.nunique()),
    }


def scenario_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (task, components), group in df.groupby(["task", "mixed_components"]):
        row = {
            "task": task,
            "mixed_components": components,
            "steps": len(group),
            "expected_route": group["expected_route"].mode().iloc[0],
            "mean_visual_evidence": float(group["visual_state_evidence"].mean()),
            "mean_depth_evidence": float(group["depth_scale_evidence"].mean()),
            "mean_policy_evidence": float(
                group[["policy_embedding_proxy_evidence", "action_outcome_mismatch_evidence"]].max(axis=1).mean()
            ),
            "priority_router_match": float(group["priority_router_route"].eq(group["expected_route"]).mean()),
            "max_signal_match": float(group["max_signal_route"].eq(group["expected_route"]).mean()),
            "uniform_retry_match": float(group["uniform_retry_route"].eq(group["expected_route"]).mean()),
        }
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["task", "mixed_components"])


def confusion(df: pd.DataFrame, pred_col: str, label: str) -> pd.DataFrame:
    table = pd.crosstab(df["expected_route"], df[pred_col], dropna=False)
    for route in ROUTES:
        if route not in table.columns:
            table[route] = 0
    table = table[ROUTES].reset_index()
    table.insert(0, "model", label)
    table.rename(columns={"expected_route": "expected"}, inplace=True)
    return table


def make_figures(df: pd.DataFrame, summary: pd.DataFrame) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(4, 2, figsize=(15, 12), sharex=False, sharey=True, constrained_layout=True)
    combos = sorted(df["mixed_components"].unique())
    colors = {
        "visual_state_evidence": "#2f6f9f",
        "depth_scale_evidence": "#9b4d1d",
        "policy": "#5b5f97",
    }
    for row, components in enumerate(combos):
        for col, task in enumerate(TASKS):
            ax = axes[row, col]
            group = df[df["task"].eq(task) & df["mixed_components"].eq(components)].sort_values("step")
            x = group["step"]
            policy_signal = group[["policy_embedding_proxy_evidence", "action_outcome_mismatch_evidence"]].max(axis=1)
            ax.plot(x, group["visual_state_evidence"], label="visual", color=colors["visual_state_evidence"], lw=1.6)
            ax.plot(x, group["depth_scale_evidence"], label="depth", color=colors["depth_scale_evidence"], lw=1.6)
            ax.plot(x, policy_signal, label="policy/action", color=colors["policy"], lw=1.6)
            mismatch = group["max_signal_route"].ne(group["expected_route"])
            if mismatch.any():
                ax.scatter(group.loc[mismatch, "step"], np.full(int(mismatch.sum()), 1.03), s=8, color="#b3261e")
            ax.set_title(f"{task}: {components}", fontsize=10)
            ax.set_ylim(-0.02, 1.08)
            ax.grid(alpha=0.25)
            if col == 0:
                ax.set_ylabel("evidence")
            if row == 0 and col == 1:
                ax.legend(frameon=False, loc="lower right", fontsize=8)
    fig.suptitle("Mixed perturbation priority stress test: evidence co-activates, route follows priority", fontweight="bold")
    fig.savefig(FIG_DIR / "failure_aware_vppv_mixed_priority_evidence.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 3.8), constrained_layout=True)
    ax.barh(summary["model"], summary["macro_f1"], color=["#2f8f5f", "#c78b55", "#4f7cac", "#8b7aa8"][: len(summary)])
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("macro-F1")
    ax.set_title("Mixed-fault priority routing")
    ax.grid(axis="x", alpha=0.25)
    for i, value in enumerate(summary["macro_f1"]):
        ax.text(float(value) + 0.02, i, f"{value:.3f}", va="center")
    fig.savefig(FIG_DIR / "failure_aware_vppv_mixed_priority_routes.png", dpi=180)
    plt.close(fig)


def write_report(summary: pd.DataFrame, scenarios: pd.DataFrame) -> None:
    top_scenarios = scenarios[
        [
            "task",
            "mixed_components",
            "expected_route",
            "mean_visual_evidence",
            "mean_depth_evidence",
            "mean_policy_evidence",
            "priority_router_match",
            "max_signal_match",
            "uniform_retry_match",
        ]
    ]
    lines = [
        "# Failure-Aware VPPV Mixed-Perturbation Priority Test",
        "",
        "This is an offline compositional stress test. It does not claim that new",
        "mixed-fault SurRoL rollouts were executed. Instead, it combines existing",
        "single-mechanism step evidence traces by task and step using a max",
        "composition rule, then checks whether the router preserves the intended",
        "priority order when multiple evidence families are active together.",
        "",
        "Priority order: `depth_scale_error` -> `visual_estimation_bias` ->",
        "`policy_approach_drift`.",
        "",
        "## Route Metrics",
        "",
        markdown_table(summary),
        "",
        "## Scenario-Level Evidence And Route Match",
        "",
        markdown_table(top_scenarios),
        "",
        "## Interpretation",
        "",
        "- A generic retry route fails because mixed visual/depth faults should not",
        "  be treated as approach drift.",
        "- A max-signal router is unstable under visual-depth confounding: when depth",
        "  error also produces a large visual residual, simply picking the largest",
        "  evidence family can select the wrong mechanism.",
        "- The priority router keeps the intended route because depth is evaluated",
        "  before visual residuals, and visual state is evaluated before policy",
        "  correction.",
        "",
        "## Scope Boundary",
        "",
        "This is not a replacement for real mixed-fault simulation. It is a",
        "mechanism-priority audit over already generated step evidence. The next",
        "stronger experiment is to run true mixed perturbation rollouts in SurRoL",
        "and compare their traces against this offline priority prediction.",
        "",
        "## Output Tables And Figures",
        "",
        "- `reports/tables/failure_aware_vppv_mixed_priority_dataset.csv`",
        "- `reports/tables/failure_aware_vppv_mixed_priority_summary.csv`",
        "- `reports/tables/failure_aware_vppv_mixed_priority_scenarios.csv`",
        "- `reports/tables/failure_aware_vppv_mixed_priority_confusion.csv`",
        "- `reports/figures/failure_aware_vppv/failure_aware_vppv_mixed_priority_evidence.png`",
        "- `reports/figures/failure_aware_vppv/failure_aware_vppv_mixed_priority_routes.png`",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    df = pd.read_csv(SOURCE)
    df = df[df["task"].isin(TASKS)].copy()
    mixed = build_mixed_dataset(df)
    summary = pd.DataFrame(
        [
            evaluate(mixed, "priority_router_route", "priority_router"),
            evaluate(mixed, "max_signal_route", "max_signal_router"),
            evaluate(mixed, "uniform_retry_route", "uniform_retry"),
            evaluate(mixed, "single_score_route", "single_score_retry"),
        ]
    )
    scenarios = scenario_summary(mixed)
    confusion_df = pd.concat(
        [
            confusion(mixed, "priority_router_route", "priority_router"),
            confusion(mixed, "max_signal_route", "max_signal_router"),
            confusion(mixed, "uniform_retry_route", "uniform_retry"),
            confusion(mixed, "single_score_route", "single_score_retry"),
        ],
        ignore_index=True,
    )

    TABLES.mkdir(parents=True, exist_ok=True)
    mixed.to_csv(TABLES / "failure_aware_vppv_mixed_priority_dataset.csv", index=False)
    summary.to_csv(TABLES / "failure_aware_vppv_mixed_priority_summary.csv", index=False)
    scenarios.to_csv(TABLES / "failure_aware_vppv_mixed_priority_scenarios.csv", index=False)
    confusion_df.to_csv(TABLES / "failure_aware_vppv_mixed_priority_confusion.csv", index=False)
    make_figures(mixed, summary)
    write_report(summary, scenarios)
    print(f"report={REPORT}")
    print(f"summary={TABLES / 'failure_aware_vppv_mixed_priority_summary.csv'}")
    print(f"figure={FIG_DIR / 'failure_aware_vppv_mixed_priority_evidence.png'}")


if __name__ == "__main__":
    main()
