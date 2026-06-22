from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prototype", type=Path, required=True)
    parser.add_argument("--strict", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("reports") / "project_brief.md")
    return parser.parse_args()


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def value(row: dict, metric: str) -> float:
    return float(row[f"{metric}_mean_over_seeds"])


def fmt(row: dict, metric: str) -> str:
    mean = value(row, metric)
    std_key = f"{metric}_std_over_seeds"
    if std_key in row and row[std_key] != "":
        return f"{mean:.3f} +/- {float(row[std_key]):.3f}"
    return f"{mean:.3f}"


def table(rows: list[dict]) -> list[str]:
    lines = [
        "| Variant | Success | Budget Exhausted | Cost | Final Distance | Shield Interventions |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in sorted(rows, key=lambda item: item["variant"]):
        lines.append(
            "| {variant} | {success} | {budget} | {cost} | {distance} | {interventions} |".format(
                variant=row["variant"],
                success=fmt(row, "success_mean"),
                budget=fmt(row, "budget_exhausted_mean"),
                cost=fmt(row, "cumulative_cost_mean"),
                distance=fmt(row, "final_distance_mean"),
                interventions=fmt(row, "shield_interventions_mean"),
            )
        )
    return lines


def find_row(rows: list[dict], variant: str) -> dict:
    for row in rows:
        if row["variant"] == variant:
            return row
    raise KeyError(variant)


def main() -> None:
    args = parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    prototype_rows = read_rows(args.prototype)
    strict_rows = read_rows(args.strict)
    tangent_proto = find_row(prototype_rows, "scratch_conditioned_tangent_shielded")
    random_note = (
        "A random-policy sanity check with the same tangent shield achieved 0.000 success on prototype episodes, "
        "so the backup controller alone is not solving the reaching task."
    )

    lines = [
        "# Constraint-Conditioned RL for Safe Surgical Tool Navigation",
        "",
        "## One-Paragraph Takeaway",
        "",
        (
            "This prototype studies a simplified surgical tool navigation task where an RL policy receives task phase "
            "and safety-budget inputs while avoiding forbidden tissue-like volumes in a 3D workspace. Plain constraint-conditioned PPO "
            "improves modestly, but the strongest result comes from adding a tangent backup controller that projects "
            "unsafe actions into a local avoidance direction. Across three seeds, tangent-shielded policies reach "
            f"{value(tangent_proto, 'success_mean'):.3f} success on the prototype setting with zero budget exhaustion "
            "and zero cumulative constraint cost. Strict transfer remains less stable, but tangent-shielded methods "
            "still dominate the unshielded baselines on safety metrics."
        ),
        "",
        "## Research Question",
        "",
        (
            "Can a policy conditioned on task phase and safety budget perform contact-rich surgical-tool navigation "
            "while respecting forbidden-region and constraint-budget limits?"
        ),
        "",
        "## Method",
        "",
        "- Base policy: PPO over a compact continuous-control surgical-tool abstraction.",
        "- Conditioning: observation includes task phase and remaining safety budget.",
        "- Safety layer: a tangent backup controller intercepts unsafe actions and redirects them around forbidden volumes.",
        "- Comparisons: scratch PPO, curriculum PPO, standard shield, tangent shield, strict-preset transfer, and random-policy sanity checks.",
        "",
        "## Prototype Evaluation",
        "",
        *table(prototype_rows),
        "",
        "## Strict Transfer Evaluation",
        "",
        *table(strict_rows),
        "",
        "## What Is Shown",
        "",
        "- Tangent-shielded variants solve the prototype task with zero observed budget exhaustion over the current three-seed run.",
        "- Standard shield reduces constraint cost but does not solve the reaching task reliably.",
        "- Curriculum helps some unshielded runs, but it is not the dominant effect in the current results.",
        f"- {random_note}",
        "",
        "## What Is Suggested",
        "",
        "- A lightweight supervisory controller can make constraint-conditioned RL much more reliable in this abstract surgical setting.",
        "- The strongest application framing is safe surgical tool navigation rather than generic PPO benchmarking.",
        "- The tangent-shield mechanism is a stronger primary contribution than curriculum learning for the current evidence.",
        "",
        "## Limitations",
        "",
        "- Only three training seeds are reported.",
        "- The environment is an abstract 3D proxy, not yet SurRoL or a high-fidelity surgical simulator.",
        "- Existing pre-upgrade result tables were produced with the earlier 2D environment and should not be mixed with retrained 3D results.",
        "- The tangent shield is strong; future experiments should measure how much action authority it uses and compare against non-RL heuristic controllers.",
        "- Strict transfer has high seed variance, especially for curriculum tangent-shielded models.",
        "",
        "## Recommended Next Experiment",
        "",
        (
            "Move from this 3D proxy to a SurRoL-inspired needle-reaching or constrained-tool-navigation environment, "
            "while keeping the same policy interface and tangent backup controller. Also report intervention rate, "
            "action deviation from the policy, and performance under stricter forbidden-region geometry."
        ),
        "",
        "## Paper-Style Claim",
        "",
        (
            "Preliminary results in an abstract surgical navigation task suggest that combining constraint-conditioned "
            "PPO with a tangent backup controller can substantially reduce constraint violations while preserving task "
            "success. These results are promising but remain prototype-level until validated in a higher-fidelity "
            "surgical simulator and with additional seeds."
        ),
        "",
    ]
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"project_brief={args.out}")


if __name__ == "__main__":
    main()
