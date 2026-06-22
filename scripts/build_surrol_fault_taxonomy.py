from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "reports" / "tables"
REPORTS = ROOT / "reports"


@dataclass(frozen=True)
class FaultDefinition:
    family: str
    intended_route: str
    interpretation: str
    limitation: str


FAULTS = {
    "none": FaultDefinition(
        "nominal_execution",
        "auto_execute",
        "Nominal SurRoL rollout without injected failure.",
        "This is a specificity check rather than a failure case.",
    ),
    "action_noise": FaultDefinition(
        "reversible_execution_drift",
        "auto_recovery",
        "Low-level action perturbation that can often be corrected by short-window recovery.",
        "NeedlePick has one remaining 10-seed failure case under action noise.",
    ),
    "action_dropout": FaultDefinition(
        "reversible_execution_drift",
        "auto_recovery",
        "Intermittent zeroed actions; recovery should restore progress without human review.",
        "Current recovery still uses simulator task primitives.",
    ),
    "execution_slip": FaultDefinition(
        "reversible_execution_drift",
        "auto_recovery",
        "Execution disturbance that may require phase-aware retry rather than plain override.",
        "Slip is synthetic and should not be presented as real actuator validation.",
    ),
    "action_freeze": FaultDefinition(
        "reversible_execution_drift",
        "auto_recovery",
        "Third-task breadth check where actions freeze and recovery re-enters progress.",
        "NeedleReach is a simpler reach task, not a full complex manipulation benchmark.",
    ),
    "near_target_drift": FaultDefinition(
        "near_target_recovery_risk",
        "auto_recovery",
        "Near-goal perturbation that is recoverable unless it enters a danger-zone proxy.",
        "Unsafe-zone routing is still geometric, not force/tissue-damage based.",
    ),
    "jaw_stuck_open": FaultDefinition(
        "grasp_contact_uncertainty",
        "human_review_or_observable_grasp_retry",
        "Silent grasp-stage failure where the gripper outcome is unreliable.",
        "Observable proxy works, but the retry primitive still calls SurRoL task logic.",
    ),
    "perception_bias": FaultDefinition(
        "visual_state_error",
        "human_review_reestimate",
        "Biased visual/state estimate; blind action recovery should not be trusted.",
        "Re-estimation currently uses a clean simulator-state proxy, not a real perception rerun.",
    ),
    "depth_scale_error": FaultDefinition(
        "visual_state_error",
        "human_review_reestimate",
        "Depth or scale error in state estimation; route to review/re-estimation.",
        "Re-estimation currently uses a clean simulator-state proxy, not a calibrated vision model.",
    ),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def fnum(value: str | None) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def fmt(value: float | None) -> str:
    return "" if value is None else f"{value:.3f}"


def limitation_for(task: str, failure: str, definition: FaultDefinition) -> str:
    if failure == "action_noise" and task != "NeedlePick":
        return "Current recovery still uses simulator task primitives."
    return definition.limitation


def best_evidence_rows(master_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    candidates = [
        row
        for row in master_rows
        if row.get("failure") not in {"", None}
        and row.get("task") in {"NeedlePick", "GauzeRetrieve", "NeedleReach"}
    ]
    # Prefer the highest seed count for each task/failure/policy family. This keeps
    # historical 5-seed rows available in source tables but presents strongest evidence.
    best: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in candidates:
        failure = row.get("failure", "")
        definition = FAULTS.get(failure)
        if definition is None:
            continue
        key = (row.get("task", ""), failure, definition.family)
        current = best.get(key)
        row_seeds = int(float(row.get("seeds") or 0))
        current_seeds = int(float(current.get("seeds") or 0)) if current else -1
        if current is None or row_seeds > current_seeds:
            best[key] = row
    return sorted(best.values(), key=lambda row: (FAULTS[row["failure"]].family, row["task"], row["failure"]))


def route_lookup(route_rows: list[dict[str, str]]) -> dict[tuple[str, str], tuple[str, str]]:
    selected: dict[tuple[str, str], tuple[str, str]] = {}
    for row in route_rows:
        if row.get("controller") != "monitor_corrected":
            continue
        key = (row.get("task", ""), row.get("failure", ""))
        episodes = int(float(row.get("episodes") or 0))
        current = selected.get(key)
        current_episodes = int(current[2]) if current and len(current) > 2 else -1
        if current is None or episodes > current_episodes:
            selected[key] = (row.get("route", ""), row.get("route_reason", ""), str(episodes))
    return {key: (value[0], value[1]) for key, value in selected.items()}


def build_taxonomy(master_rows: list[dict[str, str]], route_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    routes = route_lookup(route_rows)
    rows = []
    for evidence in best_evidence_rows(master_rows):
        failure = evidence["failure"]
        definition = FAULTS[failure]
        observed_route, route_reason = routes.get((evidence.get("task", ""), failure), ("", ""))
        rows.append(
            {
                "fault_family": definition.family,
                "task": evidence.get("task", ""),
                "failure": failure,
                "intended_route": definition.intended_route,
                "observed_route": observed_route,
                "route_reason": route_reason,
                "recovery_policy": evidence.get("recovery_policy", ""),
                "seeds": evidence.get("seeds", ""),
                "perturbed_success": fmt(fnum(evidence.get("perturbed_success"))),
                "recovered_success": fmt(fnum(evidence.get("recovered_success"))),
                "recovered_final_distance": fmt(fnum(evidence.get("recovered_final_distance"))),
                "interpretation": definition.interpretation,
                "limitation": limitation_for(evidence.get("task", ""), failure, definition),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        "# SurRoL Fault Taxonomy And Intervention Routing",
        "",
        "## Takeaway",
        "",
        (
            "The upgraded SurRoL prototype now organizes failures into a small "
            "runtime-reliability taxonomy rather than treating every failure as a generic "
            "control disturbance. Reversible action/execution faults are routed to automatic "
            "recovery, visual-state errors are routed to review/re-estimation, and silent "
            "grasp-contact faults are handled by observable grasp retry or human-review style "
            "routing. This is still a simulation-only research prototype; the current routes "
            "are rule/proxy based and should not be described as clinical or real-robot validation."
        ),
        "",
        "## Route Definitions",
        "",
        "| Route | Meaning | Current Evidence |",
        "|---|---|---|",
        "| `auto_execute` | Continue nominal execution | clean/no-alarm SurRoL rollouts remain successful |",
        "| `auto_recovery` | Try bounded automatic recovery | action noise/dropout/slip/freeze and near-target drift |",
        "| `human_review` | Stop blind recovery and request review/re-estimation | visual-state errors and uncertain grasp outcomes |",
        "| `abort_candidate` | Candidate for stopping recovery under irreversible risk | only a geometric danger-zone proxy so far |",
        "",
        "## Evidence Table",
        "",
        "| Fault Family | Task | Failure | Intended Route | Observed Route | Seeds | Perturbed | Recovered | Limitation |",
        "|---|---|---|---|---|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['fault_family']} | {row['task']} | {row['failure']} | "
            f"`{row['intended_route']}` | `{row['observed_route']}` | {row['seeds']} | "
            f"{row['perturbed_success']} | {row['recovered_success']} | {row['limitation']} |"
        )

    lines.extend(
        [
            "",
            "## What Is Shown",
            "",
            "- The standard action-corruption suite now has 10-seed evidence on NeedlePick and GauzeRetrieve.",
            "- Visual-state errors now have 10-seed review/re-estimation evidence on both core tasks.",
            "- Observable jaw-stuck recovery already has 10-seed evidence on both core tasks.",
            "- The taxonomy separates recoverable execution drift from failures that should be reviewed or re-estimated.",
            "",
            "## What Remains Unproven",
            "",
            "- The routing policy is not yet a fully learned calibrated risk classifier.",
            "- `abort_candidate` remains weak because current evidence uses a danger-zone proxy with low support.",
            "- Several recovery primitives still use SurRoL task logic; Step 4 should reduce privileged simulator-state dependence.",
            "- No real-robot, clinical, or sim-to-real claim is supported.",
            "",
            "## Application-Ready Wording",
            "",
            (
                "> I formalized the SurRoL migration as a runtime-reliability taxonomy: "
                "reversible execution drift is routed to bounded automatic recovery, visual-state "
                "errors are routed to review/re-estimation, and grasp-contact uncertainty is handled "
                "through observable retry or human-review style routing. In 10-seed SurRoL pilots, "
                "the system restores most injected failures from zero perturbed success to successful "
                "monitor-corrected execution, while retaining clear limitations around learned risk "
                "calibration and privileged simulator primitives."
            ),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    master_rows = read_csv(TABLES / "surrol_master_paired_results.csv")
    route_rows = read_csv(TABLES / "surrol_risk_triage_summary.csv")
    rows = build_taxonomy(master_rows, route_rows)
    if not rows:
        raise RuntimeError("No taxonomy rows generated.")
    write_csv(TABLES / "surrol_fault_taxonomy.csv", rows)
    write_report(REPORTS / "surrol_fault_taxonomy_step2.md", rows)
    print(f"taxonomy_csv={TABLES / 'surrol_fault_taxonomy.csv'}")
    print(f"taxonomy_report={REPORTS / 'surrol_fault_taxonomy_step2.md'}")


if __name__ == "__main__":
    main()
