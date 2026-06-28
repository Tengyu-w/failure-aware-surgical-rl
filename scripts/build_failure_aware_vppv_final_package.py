"""Build the final failure-aware VPPV evidence package.

This script does not rerun experiments. It gathers the already generated
step-level, cross-task, severity-holdout, mixed-priority, and true-mixed
rollout summaries into a compact teacher-facing package.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "reports" / "tables"
REPORTS = ROOT / "reports"

EVIDENCE_MATRIX = TABLES / "failure_aware_vppv_final_evidence_matrix.csv"
KEY_NUMBERS = TABLES / "failure_aware_vppv_final_key_numbers.csv"
TEACHER_BRIEF = REPORTS / "failure_aware_vppv_final_teacher_brief.md"
READINESS_AUDIT = REPORTS / "failure_aware_vppv_github_readiness_audit.md"


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(TABLES / name)


def f3(value: float) -> str:
    return f"{float(value):.3f}"


def pct_success(successes: int, total: int) -> str:
    return f"{successes}/{total}"


def metric_lookup(df: pd.DataFrame, **filters: str) -> pd.Series:
    mask = pd.Series(True, index=df.index)
    for column, value in filters.items():
        mask &= df[column].astype(str).eq(str(value))
    matches = df.loc[mask]
    if matches.empty:
        raise ValueError(f"No row found for filters: {filters}")
    return matches.iloc[0]


def build_numbers() -> dict[str, str]:
    step = read_csv("failure_aware_vppv_step_route_summary.csv")
    cross = read_csv("failure_aware_vppv_cross_task_summary.csv")
    severity = read_csv("failure_aware_vppv_severity_holdout_summary.csv")
    mixed = read_csv("failure_aware_vppv_mixed_priority_summary.csv")
    model_derived = read_csv("failure_aware_vppv_model_derived_summary.csv")
    true = read_csv("failure_aware_vppv_true_mixed_rollout_summary.csv")

    composite_step = metric_lookup(step, model="composite_step_route")
    visual_step = metric_lookup(step, model="visual_only")
    depth_step = metric_lookup(step, model="depth_only")
    policy_step = metric_lookup(step, model="policy_only")
    single_step = metric_lookup(step, model="single_score")

    cross_np_to_g = metric_lookup(cross, split="test_on_GauzeRetrieve")
    cross_g_to_np = metric_lookup(cross, split="test_on_NeedlePick")

    sev_high = metric_lookup(severity, model="boundary_router", split="high_holdout")
    sev_uniform_high = metric_lookup(severity, model="uniform_retry", split="high_holdout")

    mixed_priority = metric_lookup(mixed, model="priority_router")
    mixed_max = metric_lookup(mixed, model="max_signal_router")
    mixed_uniform = metric_lookup(mixed, model="uniform_retry")
    model_derived_test = metric_lookup(model_derived, split="test")

    true_weighted = true.copy()
    true_weighted["success_count"] = (
        true_weighted["success_mean"] * true_weighted["episodes"]
    ).round().astype(int)
    true_weighted["final_distance_sum"] = (
        true_weighted["final_distance_mean"] * true_weighted["episodes"]
    )
    true_by_controller = true_weighted.groupby("controller", as_index=False).agg(
        episodes=("episodes", "sum"),
        success=("success_count", "sum"),
        final_distance_sum=("final_distance_sum", "sum"),
    )
    true_by_controller["final_distance_mean"] = (
        true_by_controller["final_distance_sum"] / true_by_controller["episodes"]
    )
    true_clean = metric_lookup(true_by_controller, controller="clean")
    true_perturbed = metric_lookup(true_by_controller, controller="perturbed")
    true_routed = metric_lookup(true_by_controller, controller="priority_routed")

    total_true = int(true_routed["episodes"])

    return {
        "step_rows": str(int(composite_step["step_rows"])),
        "step_composite_macro_f1": f3(composite_step["macro_f1"]),
        "step_composite_accuracy": f3(composite_step["accuracy"]),
        "step_composite_missed_high_risk": f3(composite_step["missed_high_risk_step_rate"]),
        "step_composite_nominal_false_alarm": f3(composite_step["false_alarm_on_nominal_step_rate"]),
        "step_visual_macro_f1": f3(visual_step["macro_f1"]),
        "step_depth_macro_f1": f3(depth_step["macro_f1"]),
        "step_policy_macro_f1": f3(policy_step["macro_f1"]),
        "step_single_score_macro_f1": f3(single_step["macro_f1"]),
        "cross_np_to_g_macro_f1": f3(cross_np_to_g["macro_f1"]),
        "cross_g_to_np_macro_f1": f3(cross_g_to_np["macro_f1"]),
        "cross_g_to_np_false_alarm": f3(cross_g_to_np["false_alarm_on_continue_rate"]),
        "severity_high_macro_f1": f3(sev_high["macro_f1"]),
        "severity_high_rows": str(int(sev_high["rows"])),
        "severity_high_seeds": str(int(sev_high["seeds_total"])),
        "severity_uniform_high_macro_f1": f3(sev_uniform_high["macro_f1"]),
        "mixed_rows": str(int(mixed_priority["rows"])),
        "mixed_scenarios": str(int(mixed_priority["scenarios"])),
        "mixed_priority_macro_f1": f3(mixed_priority["macro_f1"]),
        "mixed_max_signal_macro_f1": f3(mixed_max["macro_f1"]),
        "mixed_uniform_macro_f1": f3(mixed_uniform["macro_f1"]),
        "behavior_derived_test_rows": str(int(model_derived_test["step_rows"])),
        "behavior_derived_test_episodes": str(int(model_derived_test["episodes"])),
        "behavior_derived_test_accuracy": f3(model_derived_test["accuracy"]),
        "behavior_derived_test_macro_f1": f3(model_derived_test["macro_f1"]),
        "behavior_derived_test_missed_high_risk": f3(model_derived_test["missed_high_risk_step_rate"]),
        "behavior_derived_test_false_alarm": f3(model_derived_test["false_alarm_on_nominal_step_rate"]),
        "true_total_episodes": str(total_true),
        "true_clean_success": pct_success(int(true_clean["success"]), int(true_clean["episodes"])),
        "true_perturbed_success": pct_success(int(true_perturbed["success"]), int(true_perturbed["episodes"])),
        "true_routed_success": pct_success(int(true_routed["success"]), int(true_routed["episodes"])),
        "true_clean_distance": f3(true_clean["final_distance_mean"]),
        "true_perturbed_distance": f3(true_perturbed["final_distance_mean"]),
        "true_routed_distance": f3(true_routed["final_distance_mean"]),
        "true_seeds_per_cell": str(int(true["seeds"].max())),
    }


def write_key_numbers(numbers: dict[str, str]) -> None:
    KEY_NUMBERS.parent.mkdir(parents=True, exist_ok=True)
    with KEY_NUMBERS.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["key", "value"])
        for key in sorted(numbers):
            writer.writerow([key, numbers[key]])


def write_evidence_matrix(numbers: dict[str, str]) -> None:
    rows = [
        {
            "stage": "VPPV mechanism framework",
            "research_question": "What is the real SurRoL/VPPV pain point?",
            "evidence_type": "conceptual map",
            "task_scope": "NeedlePick, GauzeRetrieve, target approach and handoff",
            "key_result": "Visual-state, depth, policy-approach, action-outcome, progress, and unsafe-continuation evidence are separated before routing.",
            "claim_supported": "The project targets reliability around visual estimation and approach policy, not low-level gripper mechanics.",
            "limitation": "Framework evidence; not a learned-policy benchmark by itself.",
            "primary_report": "docs/FAILURE_AWARE_VPPV_MULTIEVIDENCE_FRAMEWORK.md",
            "primary_table": "reports/tables/failure_aware_vppv_multievidence_framework.csv",
            "primary_figure_or_media": "",
            "reproduction_command": "python scripts\\build_failure_aware_vppv_composite_router.py",
        },
        {
            "stage": "Step-level mechanism evidence",
            "research_question": "Can runtime evidence distinguish mechanism families at the step level?",
            "evidence_type": "weak-label consistency and ablation",
            "task_scope": f"{numbers['step_rows']} SurRoL-style step rows",
            "key_result": (
                f"Composite route macro-F1={numbers['step_composite_macro_f1']} "
                f"versus visual={numbers['step_visual_macro_f1']}, "
                f"depth={numbers['step_depth_macro_f1']}, policy={numbers['step_policy_macro_f1']}, "
                f"single-score={numbers['step_single_score_macro_f1']}."
            ),
            "claim_supported": "Multiple evidence families are needed; one generic score loses mechanism identity.",
            "limitation": "Weak labels are simulator-derived routing rules, not independent expert annotations.",
            "primary_report": "reports/failure_aware_vppv_step_evidence.md",
            "primary_table": "reports/tables/failure_aware_vppv_step_route_summary.csv",
            "primary_figure_or_media": "reports/figures/failure_aware_vppv/failure_aware_vppv_step_evidence.png",
            "reproduction_command": "python scripts\\build_failure_aware_vppv_step_evidence.py",
        },
        {
            "stage": "Cross-task frozen thresholds",
            "research_question": "Do mechanism thresholds transfer between two SurRoL tasks?",
            "evidence_type": "train-one-task/test-other-task threshold transfer",
            "task_scope": "NeedlePick <-> GauzeRetrieve",
            "key_result": (
                f"NeedlePick->GauzeRetrieve macro-F1={numbers['cross_np_to_g_macro_f1']}; "
                f"GauzeRetrieve->NeedlePick macro-F1={numbers['cross_g_to_np_macro_f1']} "
                f"with false alarm={numbers['cross_g_to_np_false_alarm']}."
            ),
            "claim_supported": "The route logic is not only memorizing one task's traces.",
            "limitation": "Only two tasks and simulator-derived mechanisms.",
            "primary_report": "reports/failure_aware_vppv_cross_task_generalization.md",
            "primary_table": "reports/tables/failure_aware_vppv_cross_task_summary.csv",
            "primary_figure_or_media": "",
            "reproduction_command": "python scripts\\evaluate_failure_aware_vppv_cross_task.py",
        },
        {
            "stage": "Severity-held-out boundaries",
            "research_question": "Do low/medium-calibrated boundaries handle high-severity failures?",
            "evidence_type": "held-out severity check",
            "task_scope": f"{numbers['severity_high_rows']} high-severity task/failure rows, {numbers['severity_high_seeds']} seed aggregates",
            "key_result": (
                f"Boundary router high-holdout macro-F1={numbers['severity_high_macro_f1']}; "
                f"uniform retry macro-F1={numbers['severity_uniform_high_macro_f1']}."
            ),
            "claim_supported": "Mechanism boundaries can be more informative than uniform retry when severity shifts.",
            "limitation": "Aggregate smoke-scale check, not full external validation.",
            "primary_report": "reports/failure_aware_vppv_severity_holdout.md",
            "primary_table": "reports/tables/failure_aware_vppv_severity_holdout_summary.csv",
            "primary_figure_or_media": "reports/figures/failure_aware_vppv/failure_aware_vppv_severity_holdout.png",
            "reproduction_command": "python scripts\\evaluate_failure_aware_vppv_severity_holdout.py",
        },
        {
            "stage": "Offline mixed-priority audit",
            "research_question": "When visual, depth, and policy evidence are co-active, does route priority matter?",
            "evidence_type": "composed mixed-evidence audit",
            "task_scope": f"{numbers['mixed_rows']} rows over {numbers['mixed_scenarios']} mixed scenarios",
            "key_result": (
                f"Priority router macro-F1={numbers['mixed_priority_macro_f1']}; "
                f"max-signal={numbers['mixed_max_signal_macro_f1']}; "
                f"uniform retry={numbers['mixed_uniform_macro_f1']}."
            ),
            "claim_supported": "Compound failures need mechanism-priority routing, not retry-after-failure.",
            "limitation": "Offline compositional audit from existing traces, not true rollout by itself.",
            "primary_report": "reports/failure_aware_vppv_mixed_perturbation_priority.md",
            "primary_table": "reports/tables/failure_aware_vppv_mixed_priority_summary.csv",
            "primary_figure_or_media": "reports/figures/failure_aware_vppv/failure_aware_vppv_mixed_priority_evidence.png",
            "reproduction_command": "python scripts\\evaluate_failure_aware_vppv_mixed_priority.py",
        },
        {
            "stage": "Behavior-derived routing assignment",
            "research_question": "Can routes be derived from policy/rollout behavior regions rather than pre-written mechanism labels?",
            "evidence_type": "episode-split PCA/cluster route assignment",
            "task_scope": f"{numbers['behavior_derived_test_rows']} held-out step rows over {numbers['behavior_derived_test_episodes']} episodes",
            "key_result": (
                f"Held-out macro-F1={numbers['behavior_derived_test_macro_f1']}; "
                f"accuracy={numbers['behavior_derived_test_accuracy']}; "
                f"missed high-risk={numbers['behavior_derived_test_missed_high_risk']}; "
                f"nominal false alarm={numbers['behavior_derived_test_false_alarm']}."
            ),
            "claim_supported": "The ECG-style loop now connects rollout behavior representation regions to route assignment.",
            "limitation": "Still simulator rollout data and weak labels; not teacher-model hidden-layer analysis or independent real-world discovery.",
            "primary_report": "reports/failure_aware_vppv_model_derived_routing.md",
            "primary_table": "reports/tables/failure_aware_vppv_model_derived_summary.csv",
            "primary_figure_or_media": "reports/figures/failure_aware_vppv/failure_aware_vppv_model_derived_pca.png",
            "reproduction_command": "python scripts\\build_failure_aware_vppv_model_derived_routing.py",
        },
        {
            "stage": "True mixed-fault SurRoL rollouts",
            "research_question": "Does the priority route recover when mixed faults are actually executed in PyBullet?",
            "evidence_type": "SurRoL/PyBullet smoke rollout",
            "task_scope": f"2 tasks, 4 mixed fault combinations, {numbers['true_total_episodes']} episodes per controller",
            "key_result": (
                f"Clean={numbers['true_clean_success']} success; "
                f"perturbed={numbers['true_perturbed_success']} success; "
                f"priority-routed={numbers['true_routed_success']} success. "
                f"Mean final distance: perturbed={numbers['true_perturbed_distance']}, "
                f"routed={numbers['true_routed_distance']}."
            ),
            "claim_supported": "In a smoke-scale SurRoL rollout, route-specific re-estimation restores success under injected mixed faults.",
            "limitation": "Scripted-oracle simulation; not learned-policy, real-robot, or clinical validation.",
            "primary_report": "reports/failure_aware_vppv_true_mixed_rollouts.md",
            "primary_table": "reports/tables/failure_aware_vppv_true_mixed_rollout_paired.csv",
            "primary_figure_or_media": "reports/figures/failure_aware_vppv/failure_aware_vppv_true_mixed_success.png",
            "reproduction_command": ".\\scripts\\run_surrol_true_mixed_faults.ps1 -Seeds 5 -Episodes 1 -MaxSteps 180; python scripts\\build_failure_aware_vppv_true_mixed_rollout_report.py",
        },
    ]
    pd.DataFrame(rows).to_csv(EVIDENCE_MATRIX, index=False)


def write_teacher_brief(numbers: dict[str, str]) -> None:
    text = f"""# Failure-Aware VPPV Final Teacher Brief

## One-Sentence Contribution

This project adds an ECG-style, mechanism-specific reliability router around the
VPPV surgical-simulation pipeline: instead of treating every failure as "try
again", it separates visual-state bias, depth error, policy approach drift,
action-outcome mismatch, progress loss, and unsafe continuation, then routes the
episode to continue, re-estimate/recover, review, or abort-candidate behavior.

## What The Project Does Not Claim

- It does not claim a real surgical robot policy trained from clinical data.
- It does not claim that low-level jaw or gripper mechanics are the main learned
  component in VPPV.
- It does not claim hardware, clinical, or real-patient validation.

The useful claim is narrower: in SurRoL/PyBullet-style surgical simulation, the
project tests whether runtime evidence can identify why VPPV-style execution is
becoming unreliable and choose a mechanism-matched correction.

## Why This Fits The VPPV Pain Point

The relevant VPPV failure is not simply "the gripper opens or closes wrong".
The more important reliability problem is that the visual estimate or
high-level approach target can be wrong, the policy can move toward a biased
position, or the near-target handoff can continue unsafely. A uniform retry is
weak because visual bias, depth-scale error, and approach drift need different
responses.

## Evidence Ladder

| Stage | Key result | What it supports |
|---|---:|---|
| Step-level mechanism evidence | {numbers['step_rows']} rows; composite macro-F1={numbers['step_composite_macro_f1']}; missed high-risk={numbers['step_composite_missed_high_risk']} | Multi-evidence routing preserves mechanism identity better than one signal |
| Single-evidence ablation | visual={numbers['step_visual_macro_f1']}, depth={numbers['step_depth_macro_f1']}, policy={numbers['step_policy_macro_f1']}, single-score={numbers['step_single_score_macro_f1']} macro-F1 | One generic evidence channel is insufficient |
| Cross-task frozen thresholds | NeedlePick->GauzeRetrieve={numbers['cross_np_to_g_macro_f1']}; GauzeRetrieve->NeedlePick={numbers['cross_g_to_np_macro_f1']} macro-F1 | The route logic transfers across two SurRoL tasks |
| Severity holdout | boundary router={numbers['severity_high_macro_f1']}; uniform retry={numbers['severity_uniform_high_macro_f1']} macro-F1 on high severity | Mechanism boundaries survive a held-out severity shift |
| Offline mixed-priority audit | priority={numbers['mixed_priority_macro_f1']}; max-signal={numbers['mixed_max_signal_macro_f1']}; uniform={numbers['mixed_uniform_macro_f1']} macro-F1 | Compound faults need priority routing |
| Behavior-derived route assignment | held-out macro-F1={numbers['behavior_derived_test_macro_f1']}; missed high-risk={numbers['behavior_derived_test_missed_high_risk']}; false alarm={numbers['behavior_derived_test_false_alarm']} | Route assignment can be derived from rollout behavior regions |
| True mixed SurRoL rollouts | clean={numbers['true_clean_success']}; perturbed={numbers['true_perturbed_success']}; priority-routed={numbers['true_routed_success']} success | Route-specific re-estimation restores success in smoke-scale PyBullet rollouts |

## Final Result Snapshot

In the true mixed-fault SurRoL smoke run, the perturbed controller fails all
mixed visual/depth/near-target cases ({numbers['true_perturbed_success']}
success, mean final distance {numbers['true_perturbed_distance']}). The
priority-routed controller succeeds in all matched cases
({numbers['true_routed_success']} success, mean final distance
{numbers['true_routed_distance']}). This is the strongest current simulation
evidence, but it remains scripted-oracle PyBullet evidence.

## Current Limitations

- Labels and expected routes are weak labels from simulator perturbations and
  routing rules.
- The behavior-derived routing analysis uses policy/rollout behavior features.
  It is not a hidden-layer analysis of the teacher's original VPPV model and is
  still evaluated against simulator weak labels rather than independent expert
  labels.
- The true mixed rollout is a smoke-scale scripted-oracle run, not a deployment
  of a learned VPPV policy.
- The evidence is internal simulation evidence over NeedlePick and
  GauzeRetrieve, not external clinical or hardware validation.
- Visual media and figures demonstrate failure/recovery behavior, but they do
  not prove surgical autonomy.

## Next Strongest Experiments

1. Scale true mixed rollouts beyond the current {numbers['true_seeds_per_cell']}-seed smoke run.
2. Replace the scripted oracle in the true mixed run with the closest available
   learned or teacher-provided VPPV policy path.
3. Add camera/image corruptions and state-estimation perturbations that more
   closely match VPPV's visual module.
4. Report confidence intervals and failure cases, not only success means.
"""
    TEACHER_BRIEF.write_text(text, encoding="utf-8")


def write_readiness_audit(numbers: dict[str, str]) -> None:
    text = f"""# Failure-Aware VPPV GitHub Readiness Audit

## Overall Status

**Ready as a research-prototype evidence package, with explicit scope
limitations.** The repository now has a coherent VPPV-specific story, traceable
tables, figures, scripts, and a final evidence matrix.

## Checks

| Area | Status | Notes |
|---|---|---|
| Entry framing | PASS | README and docs explain that this is runtime reliability supervision, not clinical autonomy. |
| VPPV relevance | PASS | The final framing targets visual-state estimation, high-level approach policy, near-target handoff, and unsafe continuation. |
| Evidence traceability | PASS | Each major claim links to a report, CSV table, figure, and rebuild command. |
| Mechanism specificity | PASS | Step, cross-task, severity, mixed-priority, and true-rollout evidence all preserve visual/depth/policy route distinctions. |
| Claim calibration | PASS | Current reports state simulator-only, weak-label, and scripted-oracle limitations. |
| Reproducibility | PASS WITH WATCH | Rebuild scripts exist; true SurRoL rollout still depends on local SurRoL/PyBullet environment setup. |
| Visual evidence | PASS WITH WATCH | Figures and recovery media exist; the strongest VPPV result is figure/table based, not a polished learned-policy video. |
| Statistical maturity | NEEDS WATCH | True mixed rollouts are {numbers['true_total_episodes']} episodes per controller; scale seeds before stronger claims. |

## Evidence Files To Highlight

- `reports/failure_aware_vppv_final_teacher_brief.md`
- `reports/tables/failure_aware_vppv_final_evidence_matrix.csv`
- `reports/failure_aware_vppv_true_mixed_rollouts.md`
- `reports/tables/failure_aware_vppv_true_mixed_rollout_paired.csv`
- `reports/figures/failure_aware_vppv/failure_aware_vppv_true_mixed_success.png`
- `reports/failure_aware_vppv_step_evidence.md`
- `reports/failure_aware_vppv_cross_task_generalization.md`
- `reports/failure_aware_vppv_severity_holdout.md`
- `reports/failure_aware_vppv_mixed_perturbation_priority.md`
- `reports/failure_aware_vppv_model_derived_routing.md`

## Claims That Are Safe To Make

- The project implements a mechanism-specific runtime router for simulated
  VPPV-style surgical manipulation failures.
- In weak-label step evidence, composite routing reaches macro-F1
  {numbers['step_composite_macro_f1']} over {numbers['step_rows']} rows and
  outperforms single-family evidence.
- Frozen thresholds transfer between NeedlePick and GauzeRetrieve with
  macro-F1 {numbers['cross_np_to_g_macro_f1']} and
  {numbers['cross_g_to_np_macro_f1']}.
- Behavior-derived route assignment reaches held-out macro-F1
  {numbers['behavior_derived_test_macro_f1']} over
  {numbers['behavior_derived_test_rows']} step rows without using mechanism labels
  to form the route clusters.
- In smoke-scale true mixed SurRoL rollouts, priority routing recovers
  {numbers['true_routed_success']} cases while the perturbed controller recovers
  {numbers['true_perturbed_success']}.

## Claims To Avoid

- Do not claim real surgical safety.
- Do not claim clinical validation.
- Do not claim the VPPV low-level gripper action policy was retrained or fixed.
- Do not claim independent expert labels.
- Do not claim the true mixed rollout proves end-to-end learned autonomy.

## Remaining Cleanup Before A Public Push

- Keep `scripts/run_surrol_ppo_failure_aware.ps1` separate if it contains
  unrelated local edits.
- Make sure generated files are intentionally added together so the evidence
  package is not half-committed.
- If time allows, rerun true mixed rollouts with more seeds and regenerate this
  package.
"""
    READINESS_AUDIT.write_text(text, encoding="utf-8")


def main() -> None:
    numbers = build_numbers()
    write_key_numbers(numbers)
    write_evidence_matrix(numbers)
    write_teacher_brief(numbers)
    write_readiness_audit(numbers)
    print(f"Wrote {KEY_NUMBERS.relative_to(ROOT)}")
    print(f"Wrote {EVIDENCE_MATRIX.relative_to(ROOT)}")
    print(f"Wrote {TEACHER_BRIEF.relative_to(ROOT)}")
    print(f"Wrote {READINESS_AUDIT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
