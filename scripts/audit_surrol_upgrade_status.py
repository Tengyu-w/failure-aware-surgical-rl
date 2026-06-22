from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "reports" / "tables"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def as_int(value: str | None) -> int:
    try:
        return int(float(value or 0))
    except ValueError:
        return 0


def as_float(value: str | None) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def summarize_seed_coverage(rows: list[dict[str, str]]) -> list[str]:
    lines = ["# Step 1 seed coverage"]
    if not rows:
        return [*lines, "missing reports/tables/surrol_master_paired_results.csv"]

    target_rows = [
        row
        for row in rows
        if row.get("failure") not in {"", "none"}
        and row.get("task") in {"NeedlePick", "GauzeRetrieve", "NeedleReach"}
    ]
    complete = [row for row in target_rows if as_int(row.get("seeds")) >= 10]
    partial = [row for row in target_rows if 0 < as_int(row.get("seeds")) < 10]

    lines.append(f"10-seed rows: {len(complete)}")
    for row in complete:
        recovered = as_float(row.get("recovered_success"))
        recovered_text = "n/a" if recovered is None else f"{recovered:.3f}"
        lines.append(
            f"  OK  {row['task']} / {row['failure']} / {row['recovery_policy']} "
            f"seeds={row['seeds']} recovered={recovered_text}"
        )

    lines.append(f"rows still below 10 seeds: {len(partial)}")
    for row in partial:
        recovered = as_float(row.get("recovered_success"))
        recovered_text = "n/a" if recovered is None else f"{recovered:.3f}"
        lines.append(
            f"  TODO {row['task']} / {row['failure']} / {row['recovery_policy']} "
            f"seeds={row['seeds']} recovered={recovered_text}"
        )
    return lines


def summarize_taxonomy(rows: list[dict[str, str]]) -> list[str]:
    lines = ["", "# Step 2 taxonomy and route coverage"]
    if not rows:
        return [*lines, "missing reports/tables/surrol_fault_taxonomy.csv"]

    by_route: dict[str, int] = defaultdict(int)
    by_family: dict[str, int] = defaultdict(int)
    by_family_task: set[tuple[str, str, str]] = set()
    for row in rows:
        seeds = as_int(row.get("seeds"))
        by_route[row.get("observed_route", "")] += seeds
        by_family[row.get("fault_family", "")] += seeds
        by_family_task.add((row.get("task", ""), row.get("failure", ""), row.get("observed_route", "")))

    for route in sorted(by_route):
        if route:
            lines.append(f"  route {route}: seeds={by_route[route]}")
    lines.append(f"unique task/failure/route combinations: {len(by_family_task)}")
    lines.append("taxonomy families:")
    for family, count in sorted(by_family.items(), key=lambda item: (-item[1], item[0])):
        if family:
            lines.append(f"  {family}: seeds={count}")
    return lines


def summarize_learned_risk() -> list[str]:
    lines = ["", "# Step 3 learned risk evidence"]
    thresholds = read_csv(TABLES / "surrol_learned_risk_head_thresholds.csv")
    memory = read_csv(TABLES / "surrol_reliability_memory_metrics.csv")
    route_summary = read_csv(TABLES / "surrol_learned_route_classifier_summary.csv")
    route_metrics = read_csv(TABLES / "surrol_learned_route_classifier_metrics.csv")

    if thresholds:
        best = thresholds[0]
        lines.append(
            "binary risk head: "
            f"threshold={best.get('threshold')} precision={best.get('precision')} "
            f"recall={best.get('recall')} false_trigger={best.get('false_trigger_rate')} "
            f"miss_rate={best.get('auto_review_miss_rate')}"
        )
    else:
        lines.append("missing binary learned risk head thresholds")

    if memory:
        overall = [row for row in memory if row.get("label") == "overall_accuracy"]
        for row in overall:
            lines.append(
                f"reliability memory {row.get('label_type')}: "
                f"accuracy={row.get('f1')} support={row.get('support')}"
            )
        weak = [
            row
            for row in memory
            if row.get("label") in {"abort_candidate", "unsafe_abort"}
        ]
        for row in weak:
            lines.append(
                f"weak/high-risk class {row.get('label_type')}:{row.get('label')} "
                f"support={row.get('support')} precision={row.get('precision')} "
                f"recall={row.get('recall')} f1={row.get('f1')}"
            )
    else:
        lines.append("missing reliability memory metrics")

    if route_summary:
        summary = route_summary[0]
        lines.append(
            "learned route classifier: "
            f"accuracy={summary.get('accuracy')} macro_f1={summary.get('macro_f1')} "
            f"missed_review_or_abort={summary.get('missed_review_or_abort_rate')} "
            f"false_review_or_abort={summary.get('false_review_or_abort_rate')}"
        )
    else:
        lines.append("missing learned route classifier summary")

    if route_metrics:
        for row in route_metrics:
            if row.get("route") in {"human_review", "abort_candidate", "auto_recovery"}:
                lines.append(
                    f"route {row.get('route')}: support={row.get('support')} "
                    f"precision={row.get('precision')} recall={row.get('recall')} "
                    f"f1={row.get('f1')}"
                )
    return lines


def summarize_observable(rows: list[dict[str, str]]) -> list[str]:
    lines = ["", "# Step 4 observable proxy status"]
    comparison = read_csv(TABLES / "surrol_observable_vs_privileged_jaw_stuck.csv")
    signal_audit = read_csv(TABLES / "surrol_observable_signal_audit.csv")
    sweep = read_csv(TABLES / "observable_proxy_threshold_sweep_10seed.csv")
    observable = [row for row in rows if "observable" in row.get("recovery_policy", "")]
    privileged = [row for row in rows if "internal" in row.get("recovery_policy", "")]
    lines.append(f"observable proxy rows: {len(observable)}")
    lines.append(f"privileged/internal rows retained as upper bound: {len(privileged)}")
    for row in observable:
        lines.append(
            f"  observable {row.get('task')} / {row.get('failure')} "
            f"seeds={row.get('seeds')} recovered={row.get('recovered_success')}"
        )
    if comparison:
        lines.append("observable-vs-privileged jaw-stuck comparison:")
        for row in comparison:
            if row.get("policy") == "observable_phase_replan" and as_int(row.get("seeds")) >= 10:
                lines.append(
                    f"  {row.get('task')}: perturbed={row.get('perturbed_success')} "
                    f"recovered={row.get('recovered_success')} seeds={row.get('seeds')} "
                    f"decision={row.get('privileged_decision_dependency')}"
                )
    else:
        lines.append("missing observable-vs-privileged comparison table")

    threshold_three = [
        row
        for row in sweep
        if row.get("threshold") == "3.0"
        and row.get("failure") in {"jaw_stuck_open", "none"}
        and row.get("controller") in {"perturbed", "monitor_corrected"}
    ]
    if threshold_three:
        lines.append("threshold=3.0 observable risk sweep:")
        for row in threshold_three:
            lines.append(
                f"  {row.get('task')} / {row.get('failure')} / {row.get('controller')}: "
                f"alarm_rate={row.get('alarm_rate')} mean_alarm_step={row.get('mean_alarm_step')}"
            )

    if signal_audit:
        status_counts: dict[str, int] = defaultdict(int)
        for row in signal_audit:
            status_counts[row.get("observable_status", "")] += 1
        lines.append("signal audit status counts:")
        for status, count in sorted(status_counts.items()):
            if status:
                lines.append(f"  {status}: {count}")

    lines.append(
        "remaining limitation: observable decision trigger still calls scripted SurRoL "
        "waypoint regeneration for recovery execution."
    )
    return lines


def main() -> None:
    master = read_csv(TABLES / "surrol_master_paired_results.csv")
    routes = read_csv(TABLES / "surrol_fault_taxonomy.csv")
    lines: list[str] = []
    lines.extend(summarize_seed_coverage(master))
    lines.extend(summarize_taxonomy(routes))
    lines.extend(summarize_learned_risk())
    lines.extend(summarize_observable(master))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
