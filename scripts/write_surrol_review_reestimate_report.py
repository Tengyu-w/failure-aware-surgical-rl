from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

BASELINE_INPUTS = [
    ("NeedlePick", ROOT / "runs" / "surrol_needlepick_perception_drift_w16_5seed.csv"),
    ("GauzeRetrieve", ROOT / "runs" / "surrol_gauzeretrieve_perception_drift_w16_5seed.csv"),
]
REESTIMATE_INPUTS = [
    ("NeedlePick", ROOT / "runs" / "surrol_needlepick_review_reestimate_w16_5seed.csv"),
    ("GauzeRetrieve", ROOT / "runs" / "surrol_gauzeretrieve_review_reestimate_w16_5seed.csv"),
]


def fmt(value: float) -> str:
    return f"{float(value):.3f}"


def load_inputs(inputs: list[tuple[str, Path]], policy: str) -> pd.DataFrame:
    frames = []
    for task, path in inputs:
        if not path.exists():
            raise FileNotFoundError(path)
        df = pd.read_csv(path)
        df["task"] = task
        df["policy"] = policy
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["policy", "task", "failure", "controller"], as_index=False)
        .agg(
            episodes=("success", "size"),
            seeds=("seed", "nunique"),
            success_mean=("success", "mean"),
            final_distance_mean=("final_distance", "mean"),
            triggers_mean=("monitor_triggers", "mean"),
            visual_reestimate_triggers_mean=("visual_reestimate_triggers", "mean")
            if "visual_reestimate_triggers" in df.columns
            else ("monitor_triggers", "mean"),
            steps_mean=("steps", "mean"),
        )
        .sort_values(["task", "failure", "policy", "controller"])
    )


def paired(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    failures = ["perception_bias", "depth_scale_error"]
    for task in sorted(summary["task"].unique()):
        for failure in failures:
            base = summary[
                (summary["policy"] == "oracle_override")
                & (summary["task"] == task)
                & (summary["failure"] == failure)
            ]
            reest = summary[
                (summary["policy"] == "review_reestimate")
                & (summary["task"] == task)
                & (summary["failure"] == failure)
            ]
            def get(group: pd.DataFrame, controller: str, col: str) -> float:
                row = group[group["controller"] == controller]
                if row.empty:
                    return float("nan")
                return float(row[col].iloc[0])

            rows.append(
                {
                    "task": task,
                    "failure": failure,
                    "seeds": int(get(reest, "monitor_corrected", "seeds")),
                    "perturbed_success": get(base, "perturbed", "success_mean"),
                    "blind_monitor_success": get(base, "monitor_corrected", "success_mean"),
                    "reestimate_success": get(reest, "monitor_corrected", "success_mean"),
                    "blind_monitor_distance": get(base, "monitor_corrected", "final_distance_mean"),
                    "reestimate_distance": get(reest, "monitor_corrected", "final_distance_mean"),
                    "reestimate_triggers": get(reest, "monitor_corrected", "visual_reestimate_triggers_mean"),
                    "reestimate_steps": get(reest, "monitor_corrected", "steps_mean"),
                }
            )
    return pd.DataFrame(rows)


def write_report(paired_df: pd.DataFrame, out: Path) -> None:
    lines = [
        "# SurRoL Human-Review Re-Estimation Closed-Loop Experiment",
        "",
        "## 一句话结论",
        "",
        (
            "这一步把前面的 `human_review` 从离线路由变成了可验证的闭环：当 SurRoL 中出现 perception bias "
            "或 depth scale error 时，盲目 oracle override 不能恢复；但如果触发 review/re-estimation，"
            "即停止使用错误视觉状态并重新估计状态，NeedlePick 和 GauzeRetrieve 都能从 0/5 恢复到 5/5。"
        ),
        "",
        "## Paired Results",
        "",
        "| Task | Failure | Seeds | Perturbed | Blind Monitor | Review/Re-estimate | Blind Dist | Re-est Dist | Re-est Triggers |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in paired_df.iterrows():
        lines.append(
            f"| {row['task']} | {row['failure']} | {int(row['seeds'])} | "
            f"{fmt(row['perturbed_success'])} | {fmt(row['blind_monitor_success'])} | "
            f"{fmt(row['reestimate_success'])} | {fmt(row['blind_monitor_distance'])} | "
            f"{fmt(row['reestimate_distance'])} | {fmt(row['reestimate_triggers'])} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This supports the project framing that visual-state errors should not be handled as ordinary motion drift.",
            "- The supervisor's job is to route unreliable visual states to re-estimation, not to repeatedly apply the same recovery primitive.",
            "- The result is an upper-bound proxy because the re-estimation step uses the clean simulator state rather than a real FastSAM/IGEV re-run.",
            "",
            "## Thesis-Ready Wording",
            "",
            (
                "In VPPV-style surgical autonomy, failures caused by perceptual state errors require a different intervention "
                "from recoverable execution drift. In our SurRoL proxy, blind monitor override failed to recover perception-bias "
                "and depth-scale corruptions, whereas a review-triggered state re-estimation policy restored task success across "
                "both NeedlePick and GauzeRetrieve."
            ),
            "",
            "## Outputs",
            "",
            "- `runs/surrol_needlepick_review_reestimate_w16_5seed.csv`",
            "- `runs/surrol_gauzeretrieve_review_reestimate_w16_5seed.csv`",
            "- `reports/tables/surrol_review_reestimate_summary.csv`",
            "- `reports/tables/surrol_review_reestimate_paired.csv`",
        ]
    )
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    table_dir = ROOT / "reports" / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    baseline = load_inputs(BASELINE_INPUTS, "oracle_override")
    reestimate = load_inputs(REESTIMATE_INPUTS, "review_reestimate")
    df = pd.concat([baseline, reestimate], ignore_index=True)
    summary = summarize(df)
    paired_df = paired(summary)
    summary.to_csv(table_dir / "surrol_review_reestimate_summary.csv", index=False)
    paired_df.to_csv(table_dir / "surrol_review_reestimate_paired.csv", index=False)
    write_report(paired_df, ROOT / "reports" / "surrol_review_reestimate_round20_zh.md")
    print(f"summary={table_dir / 'surrol_review_reestimate_summary.csv'}")
    print(f"paired={table_dir / 'surrol_review_reestimate_paired.csv'}")
    print(f"report={ROOT / 'reports' / 'surrol_review_reestimate_round20_zh.md'}")


if __name__ == "__main__":
    main()
