from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aggregate", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("runs") / "experiment_report.md")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def fmt(value: str) -> str:
    return f"{float(value):.3f}"


def get(row: dict, key: str, default: str = "0") -> str:
    return row.get(key, default) or default


def write_table(rows: list[dict]) -> list[str]:
    lines = [
        "| Variant | Seeds | Success | Budget Exhausted | Cost | Final Distance | Shield Interventions | Mean Action Deviation |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {variant} | {seeds} | {success} | {budget} | {cost} | {distance} | {interventions} | {deviation} |".format(
                variant=row["variant"],
                seeds=row["seeds"],
                success=fmt(row["success_mean_mean_over_seeds"]),
                budget=fmt(row["budget_exhausted_mean_mean_over_seeds"]),
                cost=fmt(row["cumulative_cost_mean_mean_over_seeds"]),
                distance=fmt(row["final_distance_mean_mean_over_seeds"]),
                interventions=fmt(get(row, "shield_interventions_mean_mean_over_seeds")),
                deviation=fmt(get(row, "mean_action_deviation_mean_mean_over_seeds")),
            )
        )
    return lines


def main() -> None:
    args = parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    aggregate_rows = read_csv(args.aggregate)
    summary_rows = read_csv(args.summary)

    lines = [
        "# 3D Prototype Experiment Report",
        "",
        "## Setup",
        "",
        "- Environment: abstract 3D constrained surgical tool navigation.",
        "- Base learner: PPO trained directly on the selected preset.",
        "- Comparisons: conditioned PPO, no-phase/budget ablation, standard shield, and tangent shield.",
        "- Evaluation: deterministic policy evaluation on held-out seeded episodes.",
        "- Safety-authority metric: mean action deviation measures how strongly a shield changes proposed actions.",
        "",
        "## Aggregate Results",
        "",
        *write_table(aggregate_rows),
        "",
        "## Seed-Level Results",
        "",
        "| Run | Success | Budget Exhausted | Cost | Final Distance | Shield Interventions | Mean Action Deviation |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            "| {variant} | {success} | {budget} | {cost} | {distance} | {interventions} | {deviation} |".format(
                variant=row["variant"],
                success=fmt(row["success_mean"]),
                budget=fmt(row["budget_exhausted_mean"]),
                cost=fmt(row["cumulative_cost_mean"]),
                distance=fmt(row["final_distance_mean"]),
                interventions=fmt(get(row, "shield_interventions_mean")),
                deviation=fmt(get(row, "mean_action_deviation_mean")),
            )
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Confirmed facts:",
            "",
            "- The 3D training and evaluation pipeline runs end-to-end across multiple seeds.",
            "- Shielded variants can prevent budget exhaustion even when the short-run policy has low task success.",
            "- Action-deviation metrics expose how much authority the safety layer uses.",
            "",
            "Limitations:",
            "",
            "- Pilot runs use limited training steps and should not be treated as final performance.",
            "- Only three seeds are used.",
            "- The task is still an abstract surgical manipulation proxy, not SurRoL yet.",
            "- Longer training and stricter evaluation are needed before making strong research claims.",
            "",
            "Next step:",
            "",
            "- Run longer 3D training and compare success, budget exhaustion, intervention rate, and action deviation.",
            "",
        ]
    )
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"report={args.out}")


if __name__ == "__main__":
    main()
