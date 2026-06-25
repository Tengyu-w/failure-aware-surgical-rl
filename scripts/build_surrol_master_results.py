from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


EXPERIMENTS = [
    {
        "path": "runs/surrol_needlepick_phase_replan_w32_5seed.csv",
        "policy": "internal_phase_replan",
        "suite": "standard_corruptions",
        "notes": "NeedlePick standard action corruptions, internal phase-aware recovery",
    },
    {
        "path": "runs/surrol_needlepick_phase_replan_w32_10seed.csv",
        "policy": "internal_phase_replan",
        "suite": "standard_corruptions_10seed",
        "notes": "NeedlePick standard action corruptions, internal phase-aware recovery, 10 seed",
    },
    {
        "path": "runs/surrol_gauzeretrieve_phase_replan_w32_5seed.csv",
        "policy": "internal_phase_replan",
        "suite": "standard_corruptions",
        "notes": "GauzeRetrieve standard action corruptions, internal phase-aware recovery",
    },
    {
        "path": "runs/surrol_gauzeretrieve_phase_replan_w32_10seed.csv",
        "policy": "internal_phase_replan",
        "suite": "standard_corruptions_10seed",
        "notes": "GauzeRetrieve standard action corruptions, internal phase-aware recovery, 10 seed",
    },
    {
        "path": "runs/surrol_needlepick_jaw_stuck_phase_replan_w32_5seed.csv",
        "policy": "internal_phase_replan",
        "suite": "silent_jaw_stuck",
        "notes": "NeedlePick hard execution fault, internal phase-aware recovery",
    },
    {
        "path": "runs/surrol_gauzeretrieve_jaw_stuck_phase_replan_w32_5seed.csv",
        "policy": "internal_phase_replan",
        "suite": "silent_jaw_stuck",
        "notes": "GauzeRetrieve hard execution fault, internal phase-aware recovery",
    },
    {
        "path": "runs/surrol_needlepick_observable_phase_jaw_stuck_w32_5seed.csv",
        "policy": "observable_phase_replan",
        "suite": "silent_jaw_stuck_observable_proxy",
        "notes": "NeedlePick hard execution fault, observable proxy recovery, 5 seed",
    },
    {
        "path": "runs/surrol_gauzeretrieve_observable_phase_jaw_stuck_w32_5seed.csv",
        "policy": "observable_phase_replan",
        "suite": "silent_jaw_stuck_observable_proxy",
        "notes": "GauzeRetrieve hard execution fault, observable proxy recovery, 5 seed",
    },
    {
        "path": "runs/surrol_needlepick_observable_phase_jaw_stuck_w32_10seed.csv",
        "policy": "observable_phase_replan",
        "suite": "silent_jaw_stuck_observable_proxy_10seed",
        "notes": "NeedlePick hard execution fault, observable proxy recovery, 10 seed",
    },
    {
        "path": "runs/surrol_gauzeretrieve_observable_phase_jaw_stuck_w32_10seed.csv",
        "policy": "observable_phase_replan",
        "suite": "silent_jaw_stuck_observable_proxy_10seed",
        "notes": "GauzeRetrieve hard execution fault, observable proxy recovery, 10 seed",
    },
    {
        "path": "runs/surrol_needlereach_action_freeze_w16_5seed.csv",
        "policy": "oracle_override",
        "suite": "third_task_reach_freeze",
        "notes": "NeedleReach third-task smoke: action-freeze failure, oracle override recovery, 5 seed",
    },
    {
        "path": "runs/surrol_needlepick_perception_drift_w16_5seed.csv",
        "policy": "risk_triage_oracle_override",
        "suite": "visual_state_drift_5seed",
        "notes": "NeedlePick VPPV-aligned proxy: visual-state errors route to review, near-target drift routes to auto recovery",
    },
    {
        "path": "runs/surrol_gauzeretrieve_perception_drift_w16_5seed.csv",
        "policy": "risk_triage_oracle_override",
        "suite": "visual_state_drift_5seed",
        "notes": "GauzeRetrieve VPPV-aligned proxy: visual-state errors route to review, near-target drift routes to auto recovery",
    },
    {
        "path": "runs/surrol_needlepick_review_reestimate_w16_5seed.csv",
        "policy": "review_reestimate",
        "suite": "visual_state_reestimate_5seed",
        "notes": "NeedlePick closed-loop proxy: review-triggered visual-state re-estimation after perception/depth error",
    },
    {
        "path": "runs/surrol_needlepick_review_reestimate_w16_10seed.csv",
        "policy": "review_reestimate",
        "suite": "visual_state_reestimate_10seed",
        "notes": "NeedlePick closed-loop proxy: review-triggered visual-state re-estimation after perception/depth error, 10 seed",
    },
    {
        "path": "runs/surrol_gauzeretrieve_review_reestimate_w16_5seed.csv",
        "policy": "review_reestimate",
        "suite": "visual_state_reestimate_5seed",
        "notes": "GauzeRetrieve closed-loop proxy: review-triggered visual-state re-estimation after perception/depth error",
    },
    {
        "path": "runs/surrol_gauzeretrieve_review_reestimate_w16_10seed.csv",
        "policy": "review_reestimate",
        "suite": "visual_state_reestimate_10seed",
        "notes": "GauzeRetrieve closed-loop proxy: review-triggered visual-state re-estimation after perception/depth error, 10 seed",
    },
]


def fmt(value: float) -> str:
    return f"{value:.3f}"


def load_experiments() -> pd.DataFrame:
    frames = []
    for exp in EXPERIMENTS:
        path = ROOT / exp["path"]
        if not path.exists():
            print(f"missing={path}")
            continue
        df = pd.read_csv(path)
        df["source_csv"] = exp["path"]
        df["recovery_policy"] = exp["policy"]
        df["experiment_suite"] = exp["suite"]
        df["experiment_notes"] = exp["notes"]
        frames.append(df)
    if not frames:
        raise RuntimeError("No experiment CSVs found.")
    return pd.concat(frames, ignore_index=True)


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby(
            [
                "experiment_suite",
                "task",
                "failure",
                "recovery_policy",
                "controller",
                "source_csv",
                "experiment_notes",
            ],
            dropna=False,
            as_index=False,
        )
        .agg(
            episodes=("success", "size"),
            seeds=("seed", "nunique"),
            success_mean=("success", "mean"),
            success_std=("success", "std"),
            final_distance_mean=("final_distance", "mean"),
            final_distance_std=("final_distance", "std"),
            triggers_mean=("monitor_triggers", "mean"),
            phase_replans_mean=("recovery_phase_replans", "mean"),
            override_rate_mean=("recovery_override_rate", "mean"),
            steps_mean=("steps", "mean"),
            steps_std=("steps", "std"),
        )
    )
    numeric_cols = [
        "success_std",
        "final_distance_std",
        "steps_std",
    ]
    for col in numeric_cols:
        grouped[col] = grouped[col].fillna(0.0)
    return grouped.sort_values(["experiment_suite", "task", "failure", "recovery_policy", "controller"])


def paired_view(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    keys = ["experiment_suite", "task", "failure", "recovery_policy"]
    for key, group in summary.groupby(keys, dropna=False):
        controllers = {row["controller"]: row for _, row in group.iterrows()}
        perturbed = controllers.get("perturbed")
        recovered = controllers.get("monitor_corrected")
        clean = controllers.get("clean")
        if perturbed is None and recovered is None:
            continue
        rows.append(
            {
                "experiment_suite": key[0],
                "task": key[1],
                "failure": key[2],
                "recovery_policy": key[3],
                "seeds": int((recovered if recovered is not None else perturbed)["seeds"]),
                "clean_success": clean["success_mean"] if clean is not None else pd.NA,
                "perturbed_success": perturbed["success_mean"] if perturbed is not None else pd.NA,
                "recovered_success": recovered["success_mean"] if recovered is not None else pd.NA,
                "recovered_final_distance": recovered["final_distance_mean"] if recovered is not None else pd.NA,
                "mean_triggers": recovered["triggers_mean"] if recovered is not None else pd.NA,
                "mean_phase_replans": recovered["phase_replans_mean"] if recovered is not None else pd.NA,
                "mean_recovered_steps": recovered["steps_mean"] if recovered is not None else pd.NA,
            }
        )
    return pd.DataFrame(rows).sort_values(["experiment_suite", "task", "failure", "recovery_policy"])


def write_markdown(summary: pd.DataFrame, paired: pd.DataFrame, out_path: Path) -> None:
    key_rows = paired[
        (paired["failure"] != "none")
        & paired["perturbed_success"].notna()
        & paired["recovered_success"].notna()
    ].copy()

    lines = [
        "# SurRoL Reliability-Supervised Recovery Master Results",
        "",
        "## Takeaway",
        "",
        (
            "The current prototype now separates recoverable execution drift from visual-state uncertainty. "
            "Across NeedlePick and GauzeRetrieve, standard action corruptions and near-target drift can be "
            "handled by short-window monitor recovery, while perception-bias and depth-scale errors remain "
            "unrecovered and should be routed to review or visual-state re-estimation. The strongest hard-fault "
            "evidence remains the 10-seed observable-proxy jaw-stuck test, where both core tasks recover from "
            "0/10 perturbed success to 10/10 monitor-corrected success."
        ),
        "",
        "## Key Paired Results",
        "",
        "| Suite | Task | Failure | Policy | Seeds | Perturbed | Recovered | Triggers | Phase Replans | Steps |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in key_rows.iterrows():
        lines.append(
            f"| {row['experiment_suite']} | {row['task']} | {row['failure']} | {row['recovery_policy']} | "
            f"{int(row['seeds'])} | {fmt(float(row['perturbed_success']))} | {fmt(float(row['recovered_success']))} | "
            f"{fmt(float(row['mean_triggers']))} | {fmt(float(row['mean_phase_replans']))} | "
            f"{fmt(float(row['mean_recovered_steps']))} |"
        )

    lines.extend(
        [
            "",
            "## Visual-State Error And Near-Target Drift",
            "",
            "| Task | Failure | Perturbed | Monitor | Suggested Route |",
            "|---|---|---:|---:|---|",
        ]
    )
    visual = paired[
        (paired["experiment_suite"] == "visual_state_drift_5seed")
        & (paired["failure"].isin(["perception_bias", "depth_scale_error", "near_target_drift"]))
    ]
    for _, row in visual.iterrows():
        route = "human review / re-estimate state"
        if row["failure"] == "near_target_drift":
            route = "auto recovery"
        lines.append(
            f"| {row['task']} | {row['failure']} | {fmt(float(row['perturbed_success']))} | "
            f"{fmt(float(row['recovered_success']))} | {route} |"
        )

    lines.extend(
        [
            "",
            "## Review-Triggered Visual-State Re-Estimation",
            "",
            "| Task | Failure | Perturbed | Blind Monitor | Re-Estimate |",
            "|---|---|---:|---:|---:|",
        ]
    )
    visual_base = paired[
        (paired["experiment_suite"] == "visual_state_drift_5seed")
        & (paired["failure"].isin(["perception_bias", "depth_scale_error"]))
    ]
    visual_reest = paired[
        (paired["experiment_suite"] == "visual_state_reestimate_5seed")
        & (paired["failure"].isin(["perception_bias", "depth_scale_error"]))
    ]
    for _, row in visual_base.iterrows():
        match = visual_reest[(visual_reest["task"] == row["task"]) & (visual_reest["failure"] == row["failure"])]
        if match.empty:
            continue
        reest_success = float(match["recovered_success"].iloc[0])
        lines.append(
            f"| {row['task']} | {row['failure']} | {fmt(float(row['perturbed_success']))} | "
            f"{fmt(float(row['recovered_success']))} | {fmt(reest_success)} |"
        )

    lines.extend(
        [
            "",
            "## 10-Seed Observable Proxy Result",
            "",
            "| Task | Failure | Perturbed | Observable Recovery | Mean Grasp Retries | Mean Steps |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    ten = paired[
        (paired["experiment_suite"] == "silent_jaw_stuck_observable_proxy_10seed")
        & (paired["failure"] == "jaw_stuck_open")
    ]
    for _, row in ten.iterrows():
        lines.append(
            f"| {row['task']} | {row['failure']} | {fmt(float(row['perturbed_success']))} | "
            f"{fmt(float(row['recovered_success']))} | {fmt(float(row['mean_phase_replans']))} | "
            f"{fmt(float(row['mean_recovered_steps']))} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Standard action corruptions show that runtime correction can recover corrupted rollouts across NeedlePick and GauzeRetrieve.",
            "- VPPV-aligned visual-state proxy errors are not solved by blind recovery; they motivate review or re-estimation.",
            "- Review-triggered visual-state re-estimation closes this loop in simulation, recovering perception/depth failures that blind override cannot recover.",
            "- Near-target drift is recoverable with a short monitor override, matching the intended scope of a low-intrusion supervisor.",
            "- Silent jaw-stuck faults show that grasp-stage failures require phase-aware retry rather than only short-horizon action correction.",
            "- Observable proxy recovery keeps the 10-seed hard-fault success at 10/10 for both tasks while moving the replan decision away from direct waypoint/activation checks.",
            "",
            "## Limitations",
            "",
            "- This is still a simulation-only SurRoL prototype.",
            "- The observable proxy is rule-based, not learned uncertainty estimation.",
            "- Recovery primitives still call SurRoL waypoint generation, even when the replan decision uses proxy signals.",
            "- The broader standard-corruption suite remains 5 seed; only the key observable hard-fault setting is currently 10 seed.",
        ]
    )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    out_dir = ROOT / "reports" / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    df = load_experiments()
    summary = summarize(df)
    paired = paired_view(summary)

    raw_out = out_dir / "surrol_master_episode_rows.csv"
    summary_out = out_dir / "surrol_master_summary.csv"
    paired_out = out_dir / "surrol_master_paired_results.csv"
    report_out = ROOT / "reports" / "surrol_master_results.md"

    df.to_csv(raw_out, index=False)
    summary.to_csv(summary_out, index=False)
    paired.to_csv(paired_out, index=False)
    write_markdown(summary, paired, report_out)

    print(f"raw={raw_out}")
    print(f"summary={summary_out}")
    print(f"paired={paired_out}")
    print(f"report={report_out}")


if __name__ == "__main__":
    main()
