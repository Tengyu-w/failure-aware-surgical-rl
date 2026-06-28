from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUTS = [
    ("NeedlePick", ROOT / "runs" / "surrol_needlepick_perception_drift_w16_5seed.csv"),
    ("GauzeRetrieve", ROOT / "runs" / "surrol_gauzeretrieve_perception_drift_w16_5seed.csv"),
]


def fmt(value: float) -> str:
    return f"{float(value):.3f}"


def load() -> pd.DataFrame:
    frames = []
    for task, path in INPUTS:
        if not path.exists():
            raise FileNotFoundError(path)
        df = pd.read_csv(path)
        df["task"] = task
        df["source_csv"] = str(path.relative_to(ROOT))
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["task", "failure", "controller"], as_index=False)
        .agg(
            episodes=("success", "size"),
            seeds=("seed", "nunique"),
            success_mean=("success", "mean"),
            final_distance_mean=("final_distance", "mean"),
            triggers_mean=("monitor_triggers", "mean"),
            override_rate_mean=("recovery_override_rate", "mean"),
            steps_mean=("steps", "mean"),
        )
        .sort_values(["task", "failure", "controller"])
    )


def paired(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (task, failure), group in summary.groupby(["task", "failure"], dropna=False):
        by_controller = {row["controller"]: row for _, row in group.iterrows()}
        perturbed = by_controller.get("perturbed")
        monitor = by_controller.get("monitor_corrected")
        clean = by_controller.get("clean")
        if failure == "none" or perturbed is None or monitor is None:
            continue
        rows.append(
            {
                "task": task,
                "failure": failure,
                "seeds": int(monitor["seeds"]),
                "clean_success": clean["success_mean"] if clean is not None else pd.NA,
                "perturbed_success": perturbed["success_mean"],
                "monitor_success": monitor["success_mean"],
                "perturbed_final_distance": perturbed["final_distance_mean"],
                "monitor_final_distance": monitor["final_distance_mean"],
                "mean_triggers": monitor["triggers_mean"],
                "override_rate": monitor["override_rate_mean"],
            }
        )
    return pd.DataFrame(rows).sort_values(["failure", "task"])


def route_for_failure(failure: str) -> str:
    if failure in {"perception_bias", "depth_scale_error", "perception_jitter"}:
        return "human_review / re-estimate visual state"
    if failure == "near_target_drift":
        return "auto_recovery"
    return "case_by_case"


def write_report(summary: pd.DataFrame, paired_df: pd.DataFrame, out: Path) -> None:
    lines = [
        "# SurRoL Visual-State Error And Near-Target Drift Experiment",
        "",
        "## 一句话结论",
        "",
        (
            "这组 5-seed 实验把项目重新收束到 VPPV 论文的核心局限：视觉/深度状态估计错误，以及 RL policy "
            "接近目标后的 final-control drift。结果显示，perception/depth 错误会让 NeedlePick 和 GauzeRetrieve "
            "都失败，且短窗 oracle override 不能可靠恢复，因此应进入人工复核或重新估计；near-target drift 则是可逆的执行偏差，"
            "monitor 可以从 perturbed 失败恢复到 5/5 成功。"
        ),
        "",
        "## Paired Results",
        "",
        "| Task | Failure | Seeds | Clean | Perturbed | Monitor | Perturbed Dist | Monitor Dist | Triggers | Suggested Route |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for _, row in paired_df.iterrows():
        lines.append(
            f"| {row['task']} | {row['failure']} | {int(row['seeds'])} | "
            f"{fmt(row['clean_success'])} | {fmt(row['perturbed_success'])} | {fmt(row['monitor_success'])} | "
            f"{fmt(row['perturbed_final_distance'])} | {fmt(row['monitor_final_distance'])} | "
            f"{fmt(row['mean_triggers'])} | {route_for_failure(str(row['failure']))} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `perception_bias` and `depth_scale_error` proxy errors in image parsing, depth estimation, or perceptual state regression.",
            "- These perception-state failures should not be framed as cases where the robot simply retries the same motion.",
            "- `near_target_drift` proxies the paper-relevant handoff problem from learned high-level motion to final visual-servoing/control.",
            "- This supports a low-intrusion supervisor: preserve the mainstream control pipeline, but route unreliable visual states to review/re-estimation.",
            "",
            "## Limitations",
            "",
            "- The perception errors are state-space proxies, not actual FastSAM/IGEV image failures.",
            "- Only 5 seeds per task are reported here.",
            "- The recovery controller is still scripted oracle override, not a learned or robot-certified controller.",
            "",
            "## Outputs",
            "",
            "- `runs/surrol_needlepick_perception_drift_w16_5seed.csv`",
            "- `runs/surrol_gauzeretrieve_perception_drift_w16_5seed.csv`",
            "- `reports/tables/surrol_perception_drift_summary.csv`",
            "- `reports/tables/surrol_perception_drift_paired.csv`",
        ]
    )
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    table_dir = ROOT / "reports" / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    df = load()
    summary = summarize(df)
    paired_df = paired(summary)
    summary.to_csv(table_dir / "surrol_perception_drift_summary.csv", index=False)
    paired_df.to_csv(table_dir / "surrol_perception_drift_paired.csv", index=False)
    report_path = ROOT / "reports" / "surrol_perception_drift.md"
    write_report(summary, paired_df, report_path)
    print(f"summary={table_dir / 'surrol_perception_drift_summary.csv'}")
    print(f"paired={table_dir / 'surrol_perception_drift_paired.csv'}")
    print(f"report={report_path}")


if __name__ == "__main__":
    main()
