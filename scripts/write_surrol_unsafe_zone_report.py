from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT_CANDIDATES = [
    ROOT / "runs" / "surrol_needlepick_unsafe_abort_r052_w16_20seed.csv",
    ROOT / "runs" / "surrol_needlepick_unsafe_abort_r052_w16_5seed.csv",
]


def fmt(value: float) -> str:
    return f"{float(value):.3f}"


def main() -> None:
    table_dir = ROOT / "reports" / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    input_path = next((path for path in INPUT_CANDIDATES if path.exists()), None)
    if input_path is None:
        raise FileNotFoundError("No unsafe-zone run CSV found.")
    df = pd.read_csv(input_path)
    summary = (
        df.groupby(["failure", "controller"], as_index=False)
        .agg(
            episodes=("success", "size"),
            seeds=("seed", "nunique"),
            success_mean=("success", "mean"),
            unsafe_abort_rate=("unsafe_abort", "mean"),
            unsafe_warning_events_mean=("unsafe_warning_events", "mean"),
            min_danger_distance_mean=("min_danger_distance", "mean"),
            monitor_triggers_mean=("monitor_triggers", "mean"),
            final_distance_mean=("final_distance", "mean"),
            steps_mean=("steps", "mean"),
        )
        .sort_values(["failure", "controller"])
    )
    summary.to_csv(table_dir / "surrol_unsafe_zone_summary.csv", index=False)

    lines = [
        "# SurRoL Unsafe-Zone / Abort-Candidate Proxy",
        "",
        "## Takeaway",
        "",
        (
            "This step adds an irreversible-risk proxy to SurRoL: a "
            "forbidden/danger zone near the target. If near-target-drift "
            "recovery enters the danger radius, the risk-aware policy stops "
            "recovery and routes the episode to `abort_candidate`. In the "
            "current NeedlePick run, nominal trajectories do not abort, while "
            "near-target drift is split between safe recovery and "
            "abort-candidate routing."
        ),
        "",
        "## Summary",
        "",
        f"- Source: `{input_path.relative_to(ROOT)}`",
        "",
        "| Failure | Controller | Episodes | Success | Unsafe Abort | Warning Events | Min Danger Dist | Triggers |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in summary.iterrows():
        lines.append(
            f"| {row['failure']} | {row['controller']} | {int(row['episodes'])} | "
            f"{fmt(row['success_mean'])} | {fmt(row['unsafe_abort_rate'])} | "
            f"{fmt(row['unsafe_warning_events_mean'])} | {fmt(row['min_danger_distance_mean'])} | "
            f"{fmt(row['monitor_triggers_mean'])} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This is not a real tissue-damage model; it is a forbidden-zone proxy for irreversible-risk reasoning.",
            "- The result demonstrates the intended behavior: recovery is allowed only if it stays outside the danger radius.",
            "- With 20 seeds, radius 0.052 still produces some nominal false aborts under monitor_corrected, so the current danger-zone proxy should be treated as a conservative research signal rather than a deployable threshold.",
            "",
            "## Limitations",
            "",
            "- Only NeedlePick is reported in this first unsafe-zone pass.",
            "- The danger zone is a geometric proxy near the goal, not force/contact/tissue deformation.",
            "- The next step is to define task-specific forbidden regions and include them in learned risk-head labels.",
        ]
    )
    out = ROOT / "reports" / "surrol_unsafe_zone.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"summary={table_dir / 'surrol_unsafe_zone_summary.csv'}")
    print(f"report={out}")


if __name__ == "__main__":
    main()
