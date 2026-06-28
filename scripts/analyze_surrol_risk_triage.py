from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

INPUTS = [
    {
        "suite": "standard_corruptions",
        "task": "NeedlePick",
        "episode": ROOT / "runs" / "surrol_needlepick_phase_replan_w32_5seed.csv",
        "steps": ROOT / "runs" / "surrol_needlepick_phase_replan_w32_5seed_steps.csv",
    },
    {
        "suite": "standard_corruptions",
        "task": "GauzeRetrieve",
        "episode": ROOT / "runs" / "surrol_gauzeretrieve_phase_replan_w32_5seed.csv",
        "steps": ROOT / "runs" / "surrol_gauzeretrieve_phase_replan_w32_5seed_steps.csv",
    },
    {
        "suite": "observable_jaw_stuck_10seed",
        "task": "NeedlePick",
        "episode": ROOT / "runs" / "surrol_needlepick_observable_phase_jaw_stuck_w32_10seed.csv",
        "steps": ROOT / "runs" / "surrol_needlepick_observable_phase_jaw_stuck_w32_10seed_steps.csv",
    },
    {
        "suite": "observable_jaw_stuck_10seed",
        "task": "GauzeRetrieve",
        "episode": ROOT / "runs" / "surrol_gauzeretrieve_observable_phase_jaw_stuck_w32_10seed.csv",
        "steps": ROOT / "runs" / "surrol_gauzeretrieve_observable_phase_jaw_stuck_w32_10seed_steps.csv",
    },
    {
        "suite": "third_task_reach_freeze",
        "task": "NeedleReach",
        "episode": ROOT / "runs" / "surrol_needlereach_action_freeze_w16_5seed.csv",
        "steps": ROOT / "runs" / "surrol_needlereach_action_freeze_w16_5seed_steps.csv",
    },
    {
        "suite": "visual_state_drift_5seed",
        "task": "NeedlePick",
        "episode": ROOT / "runs" / "surrol_needlepick_perception_drift_w16_5seed.csv",
        "steps": ROOT / "runs" / "surrol_needlepick_perception_drift_w16_5seed_steps.csv",
    },
    {
        "suite": "visual_state_drift_5seed",
        "task": "GauzeRetrieve",
        "episode": ROOT / "runs" / "surrol_gauzeretrieve_perception_drift_w16_5seed.csv",
        "steps": ROOT / "runs" / "surrol_gauzeretrieve_perception_drift_w16_5seed_steps.csv",
    },
]


def _ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    defaults = {
        "close_command_count": 0.0,
        "observable_replan_signal": 0.0,
        "recovery_phase_replans": 0.0,
        "action_deviation": 0.0,
        "clip_event": 0.0,
        "perception_error_norm": 0.0,
        "stalled_count": 0.0,
        "monitor_trigger": 0.0,
        "recovery_override": 0.0,
        "risk_event": 0.0,
    }
    for col, value in defaults.items():
        if col not in df.columns:
            df[col] = value
    return df


def add_step_scores(seq: pd.DataFrame) -> pd.DataFrame:
    seq = seq.sort_values("step").copy()
    initial_distance = float(seq["distance"].iloc[0])
    min_distance_so_far = seq["distance"].cummin()

    seq["action_anomaly_score"] = (
        (seq["action_deviation"].astype(float) > 0.35) | (seq["clip_event"].astype(float) > 0.0)
    ).astype(float)
    seq["stall_score"] = np.clip(seq["stalled_count"].astype(float) / 8.0, 0.0, 1.0)
    seq["far_score"] = (
        (seq["distance"].astype(float) > 0.08) | (seq["distance"].astype(float) > initial_distance * 0.55)
    ).astype(float)
    seq["no_improve_score"] = ((initial_distance - min_distance_so_far) < 0.035).astype(float)
    seq["grasp_uncertain_score"] = (
        (seq["close_command_count"].astype(float) >= 4)
        & (seq["far_score"] > 0.0)
        & ((seq["stall_score"] >= 1.0) | (seq["no_improve_score"] > 0.0))
    ).astype(float)
    seq["perception_uncertain_score"] = (seq["perception_error_norm"].astype(float) > 0.005).astype(float)

    # This is deliberately conservative: it marks states where a blind retry is
    # hard to justify, not states that are physically proven unsafe.
    seq["triage_risk_score"] = (
        1.0 * seq["action_anomaly_score"]
        + 0.75 * seq["stall_score"]
        + 0.75 * seq["far_score"]
        + 0.75 * seq["no_improve_score"]
        + 1.50 * seq["grasp_uncertain_score"]
        + 1.00 * seq["perception_uncertain_score"]
    )
    return seq


def first_step(seq: pd.DataFrame, mask: pd.Series) -> float:
    selected = seq[mask]
    if selected.empty:
        return np.nan
    return float(selected["step"].iloc[0])


def route_episode(seq: pd.DataFrame, episode_row: pd.Series | None) -> dict:
    seq = add_step_scores(_ensure_columns(seq))
    failure = str(seq["failure"].iloc[0])
    controller = str(seq["controller"].iloc[0])

    max_risk = float(seq["triage_risk_score"].max())
    first_action_anomaly = first_step(seq, seq["action_anomaly_score"] > 0)
    first_grasp_uncertain = first_step(seq, (seq["step"] >= 30) & (seq["grasp_uncertain_score"] > 0))
    first_perception_uncertain = first_step(seq, seq["perception_uncertain_score"] > 0)
    first_review = first_step(seq, (seq["step"] >= 30) & (seq["triage_risk_score"] >= 3.0))
    first_abort = first_step(
        seq,
        (seq["step"] >= 30)
        & (seq["triage_risk_score"] >= 3.75)
        & (seq["stalled_count"].astype(float) >= 12)
        & (seq["distance"].astype(float) > 0.08),
    )
    first_monitor_trigger = first_step(seq, seq["monitor_trigger"].astype(float) > 0)
    first_success = first_step(seq, seq["success"].astype(float) >= 1.0)

    success = float(seq["success"].iloc[-1])
    final_distance = float(seq["distance"].iloc[-1])
    steps = int(seq["step"].max() + 1)
    monitor_triggers = float(seq["monitor_trigger"].sum())
    recovery_replans = float(seq["recovery_phase_replans"].max())
    recovery_override_rate = float(seq["recovery_override"].mean())
    if episode_row is not None:
        success = float(episode_row.get("success", success))
        final_distance = float(episode_row.get("final_distance", final_distance))
        steps = int(episode_row.get("steps", steps))
        monitor_triggers = float(episode_row.get("monitor_triggers", monitor_triggers))
        recovery_replans = float(episode_row.get("recovery_phase_replans", recovery_replans))
        recovery_override_rate = float(episode_row.get("recovery_override_rate", recovery_override_rate))

    if controller == "clean" and np.isnan(first_action_anomaly):
        route = "auto_execute"
        reason = "clean_reference_no_action_anomaly"
    elif failure == "none" and np.isnan(first_review) and np.isnan(first_action_anomaly):
        route = "auto_execute"
        reason = "nominal_no_alarm"
    elif failure in {"perception_bias", "perception_jitter", "depth_scale_error"} or not np.isnan(first_perception_uncertain):
        route = "human_review"
        reason = "visual_state_uncertain"
    elif not np.isnan(first_grasp_uncertain) or failure == "jaw_stuck_open":
        route = "human_review"
        reason = "grasp_outcome_uncertain"
    elif success < 1.0 and not np.isnan(first_abort):
        route = "abort_candidate"
        reason = "persistent_high_risk_no_progress"
    elif not np.isnan(first_action_anomaly) or not np.isnan(first_monitor_trigger):
        route = "auto_recovery"
        reason = "reversible_action_or_execution_anomaly"
    elif failure != "none":
        route = "human_review"
        reason = "abnormal_without_clear_recovery_eligibility"
    else:
        route = "auto_execute"
        reason = "nominal_low_risk"

    return {
        "suite": str(seq["suite"].iloc[0]),
        "task": str(seq["task"].iloc[0]),
        "failure": failure,
        "controller": controller,
        "seed": int(seq["seed"].iloc[0]),
        "episode": int(seq["episode"].iloc[0]),
        "route": route,
        "route_reason": reason,
        "success": success,
        "final_distance": final_distance,
        "steps": steps,
        "max_triage_risk": max_risk,
        "first_action_anomaly_step": first_action_anomaly,
        "first_grasp_uncertain_step": first_grasp_uncertain,
        "first_perception_uncertain_step": first_perception_uncertain,
        "first_review_step": first_review,
        "first_abort_step": first_abort,
        "first_monitor_trigger_step": first_monitor_trigger,
        "first_success_step": first_success,
        "monitor_triggers": monitor_triggers,
        "recovery_phase_replans": recovery_replans,
        "recovery_override_rate": recovery_override_rate,
    }


def load_routes() -> tuple[pd.DataFrame, pd.DataFrame]:
    route_rows = []
    scored_steps = []
    for item in INPUTS:
        if not item["steps"].exists() or not item["episode"].exists():
            print(f"missing_input={item}")
            continue

        steps = _ensure_columns(pd.read_csv(item["steps"]))
        episodes = pd.read_csv(item["episode"])
        steps["suite"] = item["suite"]
        steps["task"] = item["task"]
        episodes["suite"] = item["suite"]
        episodes["task"] = item["task"]

        episode_lookup = {
            (str(row["failure"]), str(row["controller"]), int(row["seed"]), int(row["episode"])): row
            for _, row in episodes.iterrows()
        }
        for _, seq in steps.groupby(["failure", "controller", "seed", "episode"], dropna=False):
            key = (
                str(seq["failure"].iloc[0]),
                str(seq["controller"].iloc[0]),
                int(seq["seed"].iloc[0]),
                int(seq["episode"].iloc[0]),
            )
            route_rows.append(route_episode(seq, episode_lookup.get(key)))
            scored_steps.append(add_step_scores(seq))
    if not route_rows:
        raise RuntimeError("No SurRoL triage inputs found.")
    return pd.DataFrame(route_rows), pd.concat(scored_steps, ignore_index=True)


def summarize(routes: pd.DataFrame) -> pd.DataFrame:
    summary = (
        routes.groupby(["suite", "task", "failure", "controller", "route", "route_reason"], as_index=False)
        .agg(
            episodes=("success", "size"),
            seeds=("seed", "nunique"),
            success_mean=("success", "mean"),
            final_distance_mean=("final_distance", "mean"),
            max_triage_risk_mean=("max_triage_risk", "mean"),
            first_review_step_mean=("first_review_step", "mean"),
            first_abort_step_mean=("first_abort_step", "mean"),
            monitor_triggers_mean=("monitor_triggers", "mean"),
            recovery_phase_replans_mean=("recovery_phase_replans", "mean"),
            recovery_override_rate_mean=("recovery_override_rate", "mean"),
        )
        .sort_values(["suite", "task", "failure", "controller", "route"])
    )
    return summary


def plot_routes(summary: pd.DataFrame, out_dir: Path) -> None:
    route_counts = summary.groupby(["route"], as_index=False)["episodes"].sum()
    order = ["auto_execute", "auto_recovery", "human_review", "abort_candidate"]
    route_counts["route"] = pd.Categorical(route_counts["route"], categories=order, ordered=True)
    route_counts = route_counts.sort_values("route")

    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    ax.bar(route_counts["route"].astype(str), route_counts["episodes"], color=["#4a8f6a", "#3b74a8", "#b7791f", "#b83232"])
    ax.set_title("SurRoL Risk-Aware Routing Counts")
    ax.set_ylabel("Episodes")
    ax.set_xlabel("Route")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_dir / "surrol_risk_triage_routes.png", dpi=200)
    plt.close(fig)


def fmt(value: float) -> str:
    if pd.isna(value):
        return ""
    return f"{float(value):.3f}"


def write_report(routes: pd.DataFrame, summary: pd.DataFrame, out_path: Path) -> None:
    focus = summary[
        (summary["controller"].isin(["perturbed", "monitor_corrected"]))
        & (summary["failure"] != "none")
    ].copy()
    nominal = summary[(summary["failure"] == "none") & (summary["controller"] == "monitor_corrected")]
    route_counts = routes.groupby("route")["success"].size().to_dict()

    lines = [
        "# SurRoL Risk-Aware Intervention Routing",
        "",
        "## Takeaway",
        "",
        (
            "This analysis upgrades the SurRoL recovery logs from a generic "
            "recover-on-anomaly rule to route-first decision making. In the "
            "NeedlePick, GauzeRetrieve, and NeedleReach logs, action noise, "
            "dropout, slip, and freeze are mainly routed to `auto_recovery`, "
            "while visually uncertain or grasp-outcome-uncertain failures such "
            "as silent jaw-stuck are routed to `human_review`."
        ),
        "",
        "## Route Definitions",
        "",
        "| Route | Meaning | Current trigger evidence |",
        "|---|---|---|",
        "| `auto_execute` | Low-risk normal execution | nominal episode with no salient risk alarm |",
        "| `auto_recovery` | Reversible anomaly where short-window automatic recovery is allowed | action anomaly, clipping, or monitor trigger without visual-state or grasp-outcome uncertainty |",
        "| `human_review` | Pause/re-estimate rather than blindly retry | visual/depth state uncertainty, grasp-outcome uncertainty, repeated jaw close commands with remaining distance, or stagnation |",
        "| `abort_candidate` | Candidate unsafe continuation | persistent high risk, no progress, and far-from-goal state; currently a conservative reserved rule |",
        "",
        "## Route Counts",
        "",
        "| Route | Episodes |",
        "|---|---:|",
    ]
    for route in ["auto_execute", "auto_recovery", "human_review", "abort_candidate"]:
        lines.append(f"| {route} | {int(route_counts.get(route, 0))} |")

    lines.extend(
        [
            "",
            "## Key Failure Routing Results",
            "",
            "| Suite | Task | Failure | Controller | Route | Episodes | Success | Mean Risk | First Review Step |",
            "|---|---|---|---|---|---:|---:|---:|---:|",
        ]
    )
    for _, row in focus.iterrows():
        lines.append(
            f"| {row['suite']} | {row['task']} | {row['failure']} | {row['controller']} | {row['route']} | "
            f"{int(row['episodes'])} | {fmt(row['success_mean'])} | {fmt(row['max_triage_risk_mean'])} | "
            f"{fmt(row['first_review_step_mean'])} |"
        )

    lines.extend(
        [
            "",
            "## Nominal Specificity Check",
            "",
            "| Task | Controller | Route | Episodes | Success | Mean Risk |",
            "|---|---|---|---:|---:|---:|",
        ]
    )
    for _, row in nominal.iterrows():
        lines.append(
            f"| {row['task']} | {row['controller']} | {row['route']} | {int(row['episodes'])} | "
            f"{fmt(row['success_mean'])} | {fmt(row['max_triage_risk_mean'])} |"
        )

    lines.extend(
        [
            "",
            "## Research Interpretation",
            "",
            "- The SurRoL prototype now has an initial risk-triage layer, not only recovery demonstrations.",
            "- `auto_recovery` corresponds to low-consequence, reversible execution anomalies; `human_review` corresponds to uncertain grasp or visual-state outcomes where blind retry is not appropriate.",
            "- After adding perception-state proxies, visual/depth/state-estimation errors route to `human_review`, while near-target drift remains `auto_recovery` when recoverable.",
            "- `abort_candidate` remains a proxy rule because these logs do not include real tissue-damage, force-feedback, or hardware-level unsafe-contact evidence.",
            "",
            "## Limitations",
            "",
            "- This is offline replay of existing logs, not online abort control.",
            "- The risk score is a transparent proxy, not a validated learned uncertainty model.",
            "- The current setup does not include real vision, force sensing, or tissue-damage labels, so it should not be described as detecting real surgical harm.",
            "",
            "## Output Files",
            "",
            "- `reports/tables/surrol_risk_triage_episode_routes.csv`",
            "- `reports/tables/surrol_risk_triage_summary.csv`",
            "- `reports/tables/surrol_risk_triage_scored_steps.csv`",
            "- `reports/figures/surrol_risk_triage/surrol_risk_triage_routes.png`",
        ]
    )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    table_dir = ROOT / "reports" / "tables"
    figure_dir = ROOT / "reports" / "figures" / "surrol_risk_triage"
    table_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    routes, scored_steps = load_routes()
    summary = summarize(routes)

    routes.to_csv(table_dir / "surrol_risk_triage_episode_routes.csv", index=False)
    summary.to_csv(table_dir / "surrol_risk_triage_summary.csv", index=False)
    scored_steps.to_csv(table_dir / "surrol_risk_triage_scored_steps.csv", index=False)
    plot_routes(summary, figure_dir)
    report_path = ROOT / "reports" / "surrol_risk_triage.md"
    write_report(routes, summary, report_path)

    print(f"routes={table_dir / 'surrol_risk_triage_episode_routes.csv'}")
    print(f"summary={table_dir / 'surrol_risk_triage_summary.csv'}")
    print(f"scored_steps={table_dir / 'surrol_risk_triage_scored_steps.csv'}")
    print(f"figure={figure_dir / 'surrol_risk_triage_routes.png'}")
    print(f"report={report_path}")


if __name__ == "__main__":
    main()
