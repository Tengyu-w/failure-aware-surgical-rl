from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write a concise risk-gated tangent report.")
    parser.add_argument("--metrics", type=Path, default=ROOT / "outputs" / "risk_model" / "risk_model_metrics.json")
    parser.add_argument(
        "--coefficients", type=Path, default=ROOT / "outputs" / "risk_model" / "logistic_coefficients.csv"
    )
    parser.add_argument("--rules", type=Path, default=ROOT / "outputs" / "risk_model" / "decision_tree_rules.txt")
    parser.add_argument(
        "--offline-sweep", type=Path, default=ROOT / "outputs" / "risk_gated_tangent" / "offline_threshold_sweep.csv"
    )
    parser.add_argument(
        "--online-summary", type=Path, default=ROOT / "outputs" / "risk_gated_tangent" / "online_summary.csv"
    )
    parser.add_argument(
        "--aggregate-summary",
        type=Path,
        default=ROOT / "outputs" / "risk_gated_tangent" / "aggregate_summary.csv",
    )
    parser.add_argument("--out", type=Path, default=ROOT / "reports" / "risk_gated_tangent_report.md")
    return parser.parse_args()


def fmt(value, digits: int = 3) -> str:
    try:
        if pd.isna(value):
            return "n/a"
        return f"{float(value):.{digits}f}"
    except Exception:
        return str(value)


def markdown_table(df: pd.DataFrame, columns: list[str], max_rows: int = 12) -> str:
    if df.empty:
        return "_No rows available._"
    shown = df.loc[:, columns].head(max_rows).copy()
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in shown.iterrows():
        lines.append("| " + " | ".join(fmt(row[column]) for column in columns) + " |")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    metrics = json.loads(args.metrics.read_text(encoding="utf-8"))
    coeffs = pd.read_csv(args.coefficients) if args.coefficients.exists() else pd.DataFrame()
    sweep = pd.read_csv(args.offline_sweep) if args.offline_sweep.exists() else pd.DataFrame()
    online = pd.read_csv(args.online_summary) if args.online_summary.exists() else pd.DataFrame()
    aggregate = pd.read_csv(args.aggregate_summary) if args.aggregate_summary.exists() else pd.DataFrame()
    rules = args.rules.read_text(encoding="utf-8") if args.rules.exists() else "No decision-tree rules available."

    logistic = metrics.get("logistic", {})
    tree = metrics.get("decision_tree", {})
    best = sweep.sort_values(["missed_risk_rate", "intervention_rate"]).head(1) if not sweep.empty else pd.DataFrame()

    lines = [
        "# Risk-Gated Tangent Backup for Explainable Safe Surgical RL",
        "",
        "## Question",
        "Can a reliability signal decide when the tangent backup controller is necessary, instead of applying safety correction at every timestep?",
        "",
        "## Method",
        "1. Build weak timestep risk labels from rollout logs and lightweight navigation rollouts.",
        "2. Train interpretable logistic and depth-3 decision-tree risk models.",
        "3. Use predicted risk to gate tangent backup activation.",
        "4. Compare offline threshold coverage and lightweight online controller behavior.",
        "",
        "## Risk Definition",
        "A timestep is weakly labeled high risk when it is close to a forbidden region, has high contact/force proxy, has low remaining budget, stalls while still far from the goal, or belongs to an episode that ultimately fails or exhausts budget.",
        "",
        "## Model Metrics",
        f"- Rows: {metrics.get('n_rows', 'n/a')} total, {metrics.get('n_train', 'n/a')} train, {metrics.get('n_test', 'n/a')} test.",
        f"- Split: {metrics.get('split_strategy', 'n/a')}.",
        f"- Logistic: AUROC={fmt(logistic.get('auroc'))}, AUPR={fmt(logistic.get('aupr'))}, F1={fmt(logistic.get('f1'))}, false_safe_rate={fmt(logistic.get('false_safe_rate'))}.",
        f"- Decision tree: AUROC={fmt(tree.get('auroc'))}, AUPR={fmt(tree.get('aupr'))}, F1={fmt(tree.get('f1'))}, false_safe_rate={fmt(tree.get('false_safe_rate'))}.",
        "",
        "## Strongest Logistic Signals",
        markdown_table(coeffs, ["feature", "coefficient", "abs_coefficient"], max_rows=8),
        "",
        "## Decision Tree Rules",
        "```text",
        rules.strip(),
        "```",
        "",
        "## Offline Gate Sweep",
        markdown_table(
            sweep,
            [
                "threshold",
                "risk_coverage",
                "missed_risk_rate",
                "intervention_rate",
                "activation_reduction_vs_always_gate",
            ],
        ),
        "",
    ]
    if not best.empty:
        row = best.iloc[0]
        lines.extend(
            [
                "The best threshold under the low-missed-risk then low-intervention ordering was "
                f"{fmt(row['threshold'])}: it covered {fmt(row['risk_coverage'])} of weak-label risk states "
                f"with intervention_rate={fmt(row['intervention_rate'])}.",
                "",
            ]
        )

    lines.extend(
        [
        "## Online Smoke Comparison",
        markdown_table(
            online,
                [
                    "method",
                    "preset",
                    "seed",
                    "success_rate",
                    "budget_exhaustion_rate",
                    "mean_interventions",
                    "gate_activation_rate",
                ],
            ),
        "",
        "## Aggregate Result Across Seeds",
        markdown_table(
            aggregate,
            [
                "method",
                "preset",
                "success_rate",
                "budget_exhaustion_rate",
                "mean_interventions",
                "intervention_rate",
                "mean_tangent_corrections",
                "seeds",
            ],
        ),
        "",
        "## Interpretation",
            "This upgrade turns the tangent backup controller from an always-available correction layer into a risk-gated supervisor. The key evidence is not only task success, but whether the gate preserves coverage of risky states while reducing unnecessary controller activation.",
            "",
            "## Limitations",
            "- The labels are weak simulation labels, not clinical or hardware safety ground truth.",
            "- Offline threshold coverage does not prove online causal safety preservation.",
            "- If the held-out split shares similar generators or failure modes with training, external validity remains limited.",
            "- The next ablation should sweep thresholds online across prototype and strict presets with multiple seeds.",
            "",
            "## Reusable Claim",
            "I further upgraded the project with an explainable risk-gated supervisor: instead of always activating the backup controller, a lightweight risk model predicts when the policy is entering a risky state and gates the tangent backup controller accordingly. This turns reliability analysis from post-hoc explanation into a runtime decision signal for safer and more efficient surgical RL.",
            "",
        ]
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"report={args.out}")


if __name__ == "__main__":
    main()
