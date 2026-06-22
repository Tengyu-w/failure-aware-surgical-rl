from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    out = ROOT / "reports" / "surrol_third_task_status_round23_zh.md"
    pnp_path = ROOT / "runs" / "surrol_pickandplace_clean_smoke.csv"
    lines = [
        "# SurRoL Third Complex Task Status",
        "",
        "## Takeaway",
        "",
        (
            "PickAndPlace was tested as the preferred complex third task, but it is not ready for formal "
            "failure/recovery experiments in this local setup. The non-haptic class can be imported only after "
            "mocking the unused haptic SWIG module, and clean oracle success is unstable."
        ),
        "",
        "## PickAndPlace Clean Oracle Smoke",
        "",
        "| Seed | Success | Steps | Final Distance |",
        "|---:|---:|---:|---:|",
    ]
    if pnp_path.exists():
        df = pd.read_csv(pnp_path)
        for _, row in df.iterrows():
            lines.append(
                f"| {int(row['seed'])} | {float(row['success']):.3f} | {int(row['steps'])} | {float(row['final_distance']):.3f} |"
            )
        lines.extend(
            [
                "",
                f"Clean success: {df['success'].mean():.3f} ({int(df['success'].sum())}/{len(df)})",
            ]
        )
    else:
        lines.append("| | | | |")
        lines.append("")
        lines.append("PickAndPlace smoke CSV was not found.")

    lines.extend(
        [
            "",
            "## Decision",
            "",
            "- Do not use PickAndPlace yet for formal risk/recovery claims.",
            "- Treat it as an unstable candidate until clean oracle reaches a reliable baseline.",
            "- NeedleRegrasp remains blocked by success/goal semantics from the earlier smoke.",
            "- The current formal task set should remain NeedlePick + GauzeRetrieve, with NeedleReach only as a simple sanity task.",
        ]
    )
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"report={out}")


if __name__ == "__main__":
    main()
