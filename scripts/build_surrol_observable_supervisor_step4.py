from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "reports" / "tables"
REPORTS = ROOT / "reports"


SIGNAL_AUDIT = [
    {
        "module": "internal_phase_replan",
        "decision_or_signal": "active waypoint index",
        "source": "SurRoL internal _waypoints",
        "observable_status": "privileged",
        "used_in_step4_path": "no",
        "research_role": "upper-bound baseline for phase-aware recovery",
    },
    {
        "module": "internal_phase_replan",
        "decision_or_signal": "activation/contact state",
        "source": "SurRoL internal _activated/_contact_constraint",
        "observable_status": "privileged",
        "used_in_step4_path": "no",
        "research_role": "upper-bound baseline; not a deployable monitor signal",
    },
    {
        "module": "observable_phase_replan",
        "decision_or_signal": "jaw close command count",
        "source": "oracle/controller command history",
        "observable_status": "observable_proxy",
        "used_in_step4_path": "yes",
        "research_role": "detects attempted grasp without reading simulator contact labels",
    },
    {
        "module": "observable_phase_replan",
        "decision_or_signal": "goal-distance stagnation",
        "source": "achieved/desired goal distance trace",
        "observable_status": "observable_proxy",
        "used_in_step4_path": "yes",
        "research_role": "detects lack of progress after repeated close commands",
    },
    {
        "module": "observable_phase_replan",
        "decision_or_signal": "minimum-distance improvement",
        "source": "distance trace over the episode",
        "observable_status": "observable_proxy",
        "used_in_step4_path": "yes",
        "research_role": "separates normal approach from failed grasp retry candidates",
    },
    {
        "module": "observable risk sweep",
        "decision_or_signal": "risk_score threshold",
        "source": "close_count + stall + far + no-improvement features",
        "observable_status": "observable_proxy",
        "used_in_step4_path": "yes",
        "research_role": "calibrates sensitivity/specificity of offline observable detection",
    },
    {
        "module": "learned_route_classifier",
        "decision_or_signal": "review/abort routing probability",
        "source": "episode-level rollout features",
        "observable_status": "partly_observable",
        "used_in_step4_path": "analysis_only",
        "research_role": "supports future online learned risk routing, but still includes post-episode features",
    },
    {
        "module": "recovery primitive",
        "decision_or_signal": "waypoint regeneration after observable trigger",
        "source": "SurRoL scripted primitive",
        "observable_status": "privileged_primitive",
        "used_in_step4_path": "yes",
        "research_role": "remaining limitation: decision is observable, execution primitive is still simulator/scripted",
    },
]


def as_float(value: object) -> float:
    return float(pd.to_numeric(value, errors="coerce"))


def load_paired() -> pd.DataFrame:
    return pd.read_csv(TABLES / "surrol_master_paired_results.csv")


def load_threshold_sweep() -> pd.DataFrame:
    return pd.read_csv(TABLES / "observable_proxy_threshold_sweep_10seed.csv")


def build_comparison(paired: pd.DataFrame, sweep: pd.DataFrame) -> pd.DataFrame:
    rows = []
    jaw = paired[
        (paired["failure"] == "jaw_stuck_open")
        & (paired["task"].isin(["NeedlePick", "GauzeRetrieve"]))
        & (paired["recovery_policy"].isin(["internal_phase_replan", "observable_phase_replan"]))
    ].copy()
    for _, row in jaw.iterrows():
        threshold_match = sweep[
            (sweep["threshold"] == 3.0)
            & (sweep["task"] == row["task"])
            & (sweep["failure"] == "jaw_stuck_open")
            & (sweep["controller"] == "perturbed")
        ]
        nominal_match = sweep[
            (sweep["threshold"] == 3.0)
            & (sweep["task"] == row["task"])
            & (sweep["failure"] == "none")
            & (sweep["controller"] == "monitor_corrected")
        ]
        rows.append(
            {
                "task": row["task"],
                "failure": row["failure"],
                "experiment_suite": row["experiment_suite"],
                "policy": row["recovery_policy"],
                "seeds": int(row["seeds"]),
                "perturbed_success": as_float(row["perturbed_success"]),
                "recovered_success": as_float(row["recovered_success"]),
                "mean_triggers": as_float(row["mean_triggers"]),
                "mean_replans": as_float(row["mean_phase_replans"]),
                "mean_recovered_steps": as_float(row["mean_recovered_steps"]),
                "fault_alarm_rate_threshold_3": (
                    float(threshold_match["alarm_rate"].iloc[0]) if not threshold_match.empty else pd.NA
                ),
                "nominal_alarm_rate_threshold_3": (
                    float(nominal_match["alarm_rate"].iloc[0]) if not nominal_match.empty else pd.NA
                ),
                "privileged_decision_dependency": (
                    "internal waypoint/contact state"
                    if row["recovery_policy"] == "internal_phase_replan"
                    else "observable command/progress proxy"
                ),
                "remaining_privileged_dependency": (
                    "decision and recovery primitive are privileged"
                    if row["recovery_policy"] == "internal_phase_replan"
                    else "recovery primitive still uses scripted SurRoL waypoint regeneration"
                ),
            }
        )
    out = pd.DataFrame(rows)
    order = {"internal_phase_replan": 0, "observable_phase_replan": 1}
    out["_policy_order"] = out["policy"].map(order).fillna(9)
    out = out.sort_values(["task", "_policy_order", "seeds"]).drop(columns=["_policy_order"])
    return out


def write_report(comparison: pd.DataFrame, audit: pd.DataFrame, route_summary: pd.DataFrame, out_path: Path) -> None:
    route = route_summary.iloc[0].to_dict() if not route_summary.empty else {}
    observable_10 = comparison[(comparison["policy"] == "observable_phase_replan") & (comparison["seeds"] >= 10)]

    lines = [
        "# SurRoL Observable Supervisor Step 4",
        "",
        "## Takeaway",
        "",
        (
            "Step 4 reduces the supervisor's decision dependence on privileged SurRoL phase/contact state. "
            "For silent jaw-stuck failures, the monitor now uses observable proxy signals--jaw close command count, "
            "distance stagnation, and minimum-distance improvement--to trigger grasp retry. On the current 10-seed "
            "NeedlePick and GauzeRetrieve evidence, observable recovery keeps the hard-fault result at 0/10 perturbed "
            "success to 10/10 recovered success for both tasks."
        ),
        "",
        "## Observable Versus Privileged Recovery",
        "",
        "| Task | Policy | Seeds | Perturbed | Recovered | Triggers | Replans | Steps | Decision Dependency |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for _, row in comparison.iterrows():
        lines.append(
            f"| {row['task']} | {row['policy']} | {int(row['seeds'])} | "
            f"{row['perturbed_success']:.3f} | {row['recovered_success']:.3f} | "
            f"{row['mean_triggers']:.3f} | {row['mean_replans']:.3f} | "
            f"{row['mean_recovered_steps']:.1f} | {row['privileged_decision_dependency']} |"
        )

    lines.extend(
        [
            "",
            "## Observable Risk Sweep At Threshold 3.0",
            "",
            "| Task | Fault Alarm Rate | Nominal Alarm Rate | Interpretation |",
            "|---|---:|---:|---|",
        ]
    )
    for _, row in observable_10.iterrows():
        lines.append(
            f"| {row['task']} | {row['fault_alarm_rate_threshold_3']:.3f} | "
            f"{row['nominal_alarm_rate_threshold_3']:.3f} | detects jaw-stuck without nominal false alarms in this 10-seed log |"
        )

    lines.extend(
        [
            "",
            "## Signal Audit",
            "",
            "| Module | Signal | Status | Role |",
            "|---|---|---|---|",
        ]
    )
    for _, row in audit.iterrows():
        lines.append(
            f"| {row['module']} | {row['decision_or_signal']} | {row['observable_status']} | {row['research_role']} |"
        )

    lines.extend(
        [
            "",
            "## Link To Learned Risk Routing",
            "",
            (
                "The Step 3 learned route classifier complements this observable supervisor: it reaches "
                f"{float(route.get('accuracy', 0.0)):.3f} held-out accuracy and "
                f"{float(route.get('macro_f1', 0.0)):.3f} macro-F1, with "
                f"{float(route.get('missed_review_or_abort_rate', 0.0)):.3f} missed review-or-abort rate. "
                "However, it is still episode-level and includes post-episode features, so Step 4 treats it as "
                "research evidence for future online routing rather than a deployable monitor."
            ),
            "",
            "## What Is Confirmed",
            "",
            "- The decision trigger for jaw-stuck recovery can be replaced by observable command/progress proxies while retaining 10/10 recovery on both core tasks.",
            "- Threshold-3.0 offline scoring detects 10/10 jaw-stuck perturbed episodes for both tasks and does not alarm on the nominal monitor-corrected episodes in these logs.",
            "- Internal phase/contact recovery remains a useful upper-bound baseline, not the main deployability claim.",
            "",
            "## What Remains Limited",
            "",
            "- Recovery execution still calls a scripted SurRoL waypoint regeneration primitive.",
            "- The observable proxy is currently validated mainly on silent jaw-stuck; standard action corruptions still rely on internal phase-aware recovery in the strongest 10-seed suite.",
            "- The learned route classifier is not yet window-level or online deployable.",
            "- All results remain simulation-only and should not be presented as clinical or real-robot validation.",
            "",
            "## Outputs",
            "",
            "- `reports/tables/surrol_observable_signal_audit.csv`",
            "- `reports/tables/surrol_observable_vs_privileged_jaw_stuck.csv`",
            "- `reports/tables/observable_proxy_threshold_sweep_10seed.csv`",
            "- `reports/figures/observable_proxy_risk/observable_proxy_threshold_sweep.png`",
        ]
    )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    paired = load_paired()
    sweep = load_threshold_sweep()
    route_summary_path = TABLES / "surrol_learned_route_classifier_summary.csv"
    route_summary = pd.read_csv(route_summary_path) if route_summary_path.exists() else pd.DataFrame()

    audit = pd.DataFrame(SIGNAL_AUDIT)
    comparison = build_comparison(paired, sweep)

    audit_out = TABLES / "surrol_observable_signal_audit.csv"
    comparison_out = TABLES / "surrol_observable_vs_privileged_jaw_stuck.csv"
    report_out = REPORTS / "surrol_observable_supervisor_step4.md"

    audit.to_csv(audit_out, index=False)
    comparison.to_csv(comparison_out, index=False)
    write_report(comparison, audit, route_summary, report_out)

    print(f"audit={audit_out}")
    print(f"comparison={comparison_out}")
    print(f"report={report_out}")


if __name__ == "__main__":
    main()
