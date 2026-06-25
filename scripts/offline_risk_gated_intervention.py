from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline threshold sweep for risk-gated tangent activation.")
    parser.add_argument(
        "--predictions",
        type=Path,
        default=ROOT / "outputs" / "risk_model" / "risk_score_predictions.csv",
    )
    parser.add_argument("--out-dir", type=Path, default=ROOT / "outputs" / "risk_gated_tangent")
    parser.add_argument("--score-column", default="risk_prob_logistic")
    parser.add_argument("--thresholds", default="0.3,0.4,0.5,0.6,0.7")
    return parser.parse_args()


def parse_thresholds(value: str) -> list[float]:
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def sweep_thresholds(df: pd.DataFrame, score_column: str, thresholds: list[float]) -> pd.DataFrame:
    if score_column not in df.columns:
        raise ValueError(f"Missing score column {score_column!r}. Available columns: {list(df.columns)}")
    if "risk_label" not in df.columns:
        raise ValueError("Predictions file must include risk_label.")

    risk = df["risk_label"].astype(int) == 1
    rows = []
    for threshold in thresholds:
        intervene = df[score_column] >= threshold
        true_risk = int(risk.sum())
        true_safe = int((~risk).sum())
        covered_risk = int((intervene & risk).sum())
        missed_risk = int((~intervene & risk).sum())
        unnecessary = int((intervene & ~risk).sum())
        rows.append(
            {
                "threshold": float(threshold),
                "risk_coverage": covered_risk / max(true_risk, 1),
                "missed_risk_rate": missed_risk / max(true_risk, 1),
                "intervention_rate": float(intervene.mean()),
                "unnecessary_intervention_rate": unnecessary / max(true_safe, 1),
                "activation_reduction_vs_always_gate": 1.0 - float(intervene.mean()),
                "covered_risk_steps": covered_risk,
                "missed_risk_steps": missed_risk,
                "unnecessary_intervention_steps": unnecessary,
                "total_steps": int(len(df)),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(args.predictions)
    thresholds = parse_thresholds(args.thresholds)
    summary = sweep_thresholds(df, args.score_column, thresholds)
    summary.to_csv(args.out_dir / "offline_threshold_sweep.csv", index=False)

    best = summary.sort_values(["missed_risk_rate", "intervention_rate", "threshold"]).iloc[0].to_dict()
    comparison = pd.DataFrame(
        [
            {
                "method": "always_tangent_proxy",
                "threshold": np.nan,
                "risk_coverage": 1.0,
                "missed_risk_rate": 0.0,
                "intervention_rate": 1.0,
                "activation_reduction_vs_always_gate": 0.0,
            },
            {
                "method": "risk_gated_tangent_proxy",
                **best,
            },
        ]
    )
    comparison.to_csv(args.out_dir / "summary.csv", index=False)

    payload = {
        "predictions": str(args.predictions),
        "score_column": args.score_column,
        "best_threshold_by_low_missed_risk_then_low_intervention": best,
        "interpretation": (
            "Offline gating is useful when it covers most weak-label risk states while reducing activation "
            "relative to an always-on gate. This is a proxy analysis, not a guarantee that online intervention "
            "will preserve success."
        ),
    }
    with (args.out_dir / "offline_risk_gated_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    print(summary.to_string(index=False))
    print("\nBest threshold:")
    print(json.dumps(best, indent=2))


if __name__ == "__main__":
    main()
