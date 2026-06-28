from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

INPUTS = [
    {
        "task": "NeedlePick",
        "severity": "low",
        "perception_bias_scale": 0.25,
        "depth_scale_error": 0.03,
        "near_target_drift_scale": 0.50,
        "path": ROOT / "runs" / "surrol_needlepick_severity_low_w16_5seed.csv",
    },
    {
        "task": "NeedlePick",
        "severity": "medium",
        "perception_bias_scale": 1.00,
        "depth_scale_error": 0.12,
        "near_target_drift_scale": 1.00,
        "path": ROOT / "runs" / "surrol_needlepick_perception_drift_w16_5seed.csv",
    },
    {
        "task": "NeedlePick",
        "severity": "high",
        "perception_bias_scale": 1.50,
        "depth_scale_error": 0.18,
        "near_target_drift_scale": 1.50,
        "path": ROOT / "runs" / "surrol_needlepick_severity_high_w16_5seed.csv",
    },
    {
        "task": "GauzeRetrieve",
        "severity": "low",
        "perception_bias_scale": 0.25,
        "depth_scale_error": 0.03,
        "near_target_drift_scale": 0.50,
        "path": ROOT / "runs" / "surrol_gauzeretrieve_severity_low_w16_5seed.csv",
    },
    {
        "task": "GauzeRetrieve",
        "severity": "medium",
        "perception_bias_scale": 1.00,
        "depth_scale_error": 0.12,
        "near_target_drift_scale": 1.00,
        "path": ROOT / "runs" / "surrol_gauzeretrieve_perception_drift_w16_5seed.csv",
    },
    {
        "task": "GauzeRetrieve",
        "severity": "high",
        "perception_bias_scale": 1.50,
        "depth_scale_error": 0.18,
        "near_target_drift_scale": 1.50,
        "path": ROOT / "runs" / "surrol_gauzeretrieve_severity_high_w16_5seed.csv",
    },
]

SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}
FAILURE_ORDER = ["perception_bias", "depth_scale_error", "near_target_drift"]


def fmt(value: float) -> str:
    return f"{float(value):.3f}"


def load() -> pd.DataFrame:
    frames = []
    for item in INPUTS:
        if not item["path"].exists():
            raise FileNotFoundError(item["path"])
        df = pd.read_csv(item["path"])
        df["task"] = item["task"]
        df["severity"] = item["severity"]
        df["severity_rank"] = SEVERITY_ORDER[item["severity"]]
        df["perception_bias_scale"] = item["perception_bias_scale"]
        df["depth_scale_error"] = item["depth_scale_error"]
        df["near_target_drift_scale"] = item["near_target_drift_scale"]
        df["source_csv"] = str(item["path"].relative_to(ROOT))
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby(
            [
                "task",
                "severity",
                "severity_rank",
                "failure",
                "controller",
                "perception_bias_scale",
                "depth_scale_error",
                "near_target_drift_scale",
            ],
            as_index=False,
        )
        .agg(
            episodes=("success", "size"),
            seeds=("seed", "nunique"),
            success_mean=("success", "mean"),
            final_distance_mean=("final_distance", "mean"),
            triggers_mean=("monitor_triggers", "mean"),
            override_rate_mean=("recovery_override_rate", "mean"),
            steps_mean=("steps", "mean"),
        )
        .sort_values(["task", "failure", "severity_rank", "controller"])
    )
    return summary


def paired(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (task, severity, failure), group in summary.groupby(["task", "severity", "failure"], dropna=False):
        if failure == "none":
            continue
        by_controller = {row["controller"]: row for _, row in group.iterrows()}
        perturbed = by_controller.get("perturbed")
        monitor = by_controller.get("monitor_corrected")
        clean = by_controller.get("clean")
        if perturbed is None or monitor is None:
            continue
        rows.append(
            {
                "task": task,
                "severity": severity,
                "severity_rank": SEVERITY_ORDER[severity],
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
    return pd.DataFrame(rows).sort_values(["failure", "task", "severity_rank"])


def suggested_route(row: pd.Series) -> str:
    failure = str(row["failure"])
    monitor_success = float(row["monitor_success"])
    triggers = float(row["mean_triggers"])
    if failure in {"perception_bias", "depth_scale_error"}:
        if monitor_success < 0.8:
            return "human_review / re-estimate state"
        return "auto_execute_or_review_by_threshold"
    if failure == "near_target_drift":
        if monitor_success >= 0.8 and triggers > 0:
            return "auto_recovery"
        if monitor_success >= 0.8:
            return "auto_execute"
        return "threshold_needs_calibration"
    return "case_by_case"


def plot(paired_df: pd.DataFrame, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for task, task_df in paired_df.groupby("task"):
        fig, axes = plt.subplots(1, 3, figsize=(12.8, 3.8), sharey=True)
        for ax, failure in zip(axes, FAILURE_ORDER):
            group = task_df[task_df["failure"] == failure].sort_values("severity_rank")
            ax.plot(group["severity"], group["perturbed_success"], marker="o", label="perturbed")
            ax.plot(group["severity"], group["monitor_success"], marker="o", label="monitor")
            ax.set_title(failure)
            ax.set_ylim(-0.05, 1.05)
            ax.set_xlabel("Severity")
            ax.grid(alpha=0.3)
        axes[0].set_ylabel("Success rate")
        axes[-1].legend(frameon=False, loc="lower right")
        fig.suptitle(f"{task}: Severity Sweep")
        fig.tight_layout()
        fig.savefig(out_dir / f"{task.lower()}_severity_sweep.png", dpi=200)
        plt.close(fig)


def write_report(paired_df: pd.DataFrame, out: Path) -> None:
    lines = [
        "# SurRoL Severity Sweep For Visual-State Error And Near-Target Drift",
        "",
        "## 一句话结论",
        "",
        (
            "这一步完成了 error/drift severity sweep：在 NeedlePick 和 GauzeRetrieve 上分别测试低、中、高三档 "
            "perception bias、depth scale error 和 near-target drift。结果支持一个更细的分流边界："
            "视觉/深度状态错误一旦造成失败，短窗 recovery 基本不能解决，应进入视觉状态重估或人工复核；"
            "near-target drift 在中高强度下可以被 monitor 自动恢复，但低强度 drift 在 NeedlePick 上存在漏触发，"
            "说明阈值还需要校准。"
        ),
        "",
        "## Paired Severity Results",
        "",
        "| Task | Failure | Severity | Seeds | Perturbed | Monitor | Triggers | Perturbed Dist | Monitor Dist | Suggested Route |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for _, row in paired_df.iterrows():
        lines.append(
            f"| {row['task']} | {row['failure']} | {row['severity']} | {int(row['seeds'])} | "
            f"{fmt(row['perturbed_success'])} | {fmt(row['monitor_success'])} | {fmt(row['mean_triggers'])} | "
            f"{fmt(row['perturbed_final_distance'])} | {fmt(row['monitor_final_distance'])} | {suggested_route(row)} |"
        )

    lines.extend(
        [
            "",
            "## 边界解读",
            "",
            "- `perception_bias`: GauzeRetrieve 低强度仍可承受，但中高强度失败；NeedlePick 低强度已有 2/5 失败，中高强度 0/5。",
            "- `depth_scale_error`: 两个任务即使低强度也较脆弱，说明深度/三维状态误差是更高优先级的复核对象。",
            "- `near_target_drift`: 中高强度漂移可由 monitor 恢复到 5/5；低强度下 GauzeRetrieve 本身成功，NeedlePick 存在漏触发，应调低 near-target drift 的检测阈值或增加终点误差监测。",
            "",
            "## 和初衷的关系",
            "",
            "这组实验没有改变主流手术机器人工作流，而是在现有视觉状态估计与 final control 交接处增加可靠性边界：",
            "可逆漂移允许自动恢复，视觉/深度状态不可靠则进入复核或重估。",
            "",
            "## 局限",
            "",
            "- Severity 是状态空间代理，不是真实 FastSAM/IGEV 图像错误。",
            "- 每个任务每档 5 seed，仍然是轻量研究原型证据。",
            "- Monitor 阈值仍是规则型，下一步应把漏触发样本用于校准。",
            "",
            "## Outputs",
            "",
            "- `reports/tables/surrol_severity_sweep_summary.csv`",
            "- `reports/tables/surrol_severity_sweep_paired.csv`",
            "- `reports/figures/surrol_severity_sweep/needlepick_severity_sweep.png`",
            "- `reports/figures/surrol_severity_sweep/gauzeretrieve_severity_sweep.png`",
        ]
    )
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    table_dir = ROOT / "reports" / "tables"
    figure_dir = ROOT / "reports" / "figures" / "surrol_severity_sweep"
    table_dir.mkdir(parents=True, exist_ok=True)
    df = load()
    summary = summarize(df)
    paired_df = paired(summary)
    summary.to_csv(table_dir / "surrol_severity_sweep_summary.csv", index=False)
    paired_df.to_csv(table_dir / "surrol_severity_sweep_paired.csv", index=False)
    plot(paired_df, figure_dir)
    report_path = ROOT / "reports" / "surrol_severity_sweep.md"
    write_report(paired_df, report_path)
    print(f"summary={table_dir / 'surrol_severity_sweep_summary.csv'}")
    print(f"paired={table_dir / 'surrol_severity_sweep_paired.csv'}")
    print(f"figures={figure_dir}")
    print(f"report={report_path}")


if __name__ == "__main__":
    main()
