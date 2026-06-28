# Documentation Guide

This folder contains the supervisor-facing documentation for the project. The
repository is intentionally organized as a research portfolio, not as a raw
experiment dump.

## Recommended Reading Order

| Time | File | Purpose |
| --- | --- | --- |
| 2 min | [Project README](../README.md) | Main contribution, result snapshot, and limitations. |
| 8 min | [Teacher-facing experiment process](TEACHER_EXPERIMENT_PROCESS.md) | The clearest narrative of what the project actually does and why the VPPV focus changed. |
| 5 min | [Project index](PROJECT_INDEX.md) | Public entry point and evidence snapshot. |
| 10 min | [Experiment evidence summary](EXPERIMENT_EVIDENCE_SUMMARY.md) | Compact story of what was tested, why, what worked, and what failed. |
| 15 min | [Evidence index](evidence_index.md) | Claim-by-claim pointers to figures, tables, and reports. |
| 15 min | [Learning-to-routing flow](LEARNING_TO_ROUTING_FLOW.md) | How RL training, weak labels, embedding/KNN analysis, failed retraining, visual risk, and runtime routing connect. |
| 15 min | [SurRoL task upgrade framework](SURROL_TASK_UPGRADE_FRAMEWORK.md) | How NeedleReach, NeedlePick, GauzeRetrieve, PickAndPlace, and unsafe-zone recovery extend the CircleRL proxy. |
| 15 min | [SurRoL ECG-style mechanism routing](SURROL_ECG_STYLE_MECHANISM_ROUTING.md) | How the reliable-ECG error-mechanism framework maps to SurRoL failure injection, evidence signals, and v5d-style routing. |
| 15 min | [Failure-aware VPPV multi-evidence framework](FAILURE_AWARE_VPPV_MULTIEVIDENCE_FRAMEWORK.md) | Reframes the project around VPPV visual-state, approach-policy, servoing-handoff, and unsafe-continuation mechanisms. |
| 5 min | [Failure-aware VPPV supervisor brief](../reports/failure_aware_vppv_supervisor_brief.md) | One-page teacher-facing explanation of the VPPV pain point, mechanism routes, evidence, and limits. |
| 15 min | [Failure-aware VPPV step evidence](../reports/failure_aware_vppv_step_evidence.md) | Step-level normal/visual-bias/depth-error/policy-drift dataset, single-evidence ablation, early warning, and mechanism evidence figure. |
| 15 min | [Failure-aware VPPV cross-task generalization](../reports/failure_aware_vppv_cross_task_generalization.md) | Freezes mechanism-router thresholds on one SurRoL task and tests whether they transfer to another. |
| 15 min | [Failure-aware VPPV severity holdout](../reports/failure_aware_vppv_severity_holdout.md) | Calibrates intervention boundaries on low/medium severity and tests held-out high severity. |
| 15 min | [Failure-aware VPPV mixed-priority audit](../reports/failure_aware_vppv_mixed_perturbation_priority.md) | Tests whether co-active visual/depth/policy evidence follows the intended route priority instead of a generic retry rule. |
| 15 min | [Failure-aware VPPV behavior-derived routing](../reports/failure_aware_vppv_model_derived_routing.md) | Derives route assignment from rollout behavior clusters and evaluates it on held-out episodes. |
| 15 min | [Failure-aware VPPV true mixed rollouts](../reports/failure_aware_vppv_true_mixed_rollouts.md) | Executes mixed visual/depth/near-target fault proxies in SurRoL/PyBullet and compares perturbed versus priority-routed controllers. |
| 5 min | [Failure-aware VPPV final teacher brief](../reports/failure_aware_vppv_final_teacher_brief.md) | Final VPPV evidence ladder, strongest claim, and limitations for a supervisor. |
| 10 min | [Failure-aware VPPV final evidence matrix](../reports/tables/failure_aware_vppv_final_evidence_matrix.csv) | Machine-readable claim-to-evidence matrix for reports, figures, tables, and rebuild commands. |
| 15 min | [ECG-style RL upgrade](ECG_STYLE_RL_UPGRADE.md) | Broad reliability analysis and model upgrade mapped from the ECG project. |
| 20 min | [Method overview](METHOD_OVERVIEW.md) | Method diagram and reliability signal families. |
| 30 min | [Research report](RESEARCH_REPORT.md) | Detailed stage-ordered final report. |
| Visual | [Figure atlas](FIGURE_ATLAS.md) | Public visual evidence inventory. |

## Core Documents

- [RESEARCH_REPORT.md](RESEARCH_REPORT.md): full stage-ordered final report.
- [TEACHER_EXPERIMENT_PROCESS.md](TEACHER_EXPERIMENT_PROCESS.md): supervisor-facing
  explanation of the project logic from proxy RL to ECG-style VPPV routing.
- [EXPERIMENT_EVIDENCE_SUMMARY.md](EXPERIMENT_EVIDENCE_SUMMARY.md): compact
  explanation for a supervisor.
- [METHOD_OVERVIEW.md](METHOD_OVERVIEW.md): method diagram and route logic.
- [LEARNING_TO_ROUTING_FLOW.md](LEARNING_TO_ROUTING_FLOW.md): full
  learning-to-routing explanation.
- [SURROL_TASK_UPGRADE_FRAMEWORK.md](SURROL_TASK_UPGRADE_FRAMEWORK.md):
  task-level upgrade framework beyond the CircleRL proxy.
- [SURROL_ECG_STYLE_MECHANISM_ROUTING.md](SURROL_ECG_STYLE_MECHANISM_ROUTING.md):
  ECG-style mechanism-aware routing blueprint for SurRoL failures.
- [FAILURE_AWARE_VPPV_MULTIEVIDENCE_FRAMEWORK.md](FAILURE_AWARE_VPPV_MULTIEVIDENCE_FRAMEWORK.md):
  VPPV-specific multi-evidence mechanism framework and composite-route plan.
- [failure_aware_vppv_supervisor_brief.md](../reports/failure_aware_vppv_supervisor_brief.md):
  one-page VPPV supervisor positioning brief with the main summary figure.
- [failure_aware_vppv_step_evidence.md](../reports/failure_aware_vppv_step_evidence.md):
  step-level VPPV-style evidence dataset, early-warning metrics, and mechanism
  evidence figure.
- [failure_aware_vppv_cross_task_generalization.md](../reports/failure_aware_vppv_cross_task_generalization.md):
  cross-task frozen-threshold check for the VPPV mechanism router.
- [failure_aware_vppv_severity_holdout.md](../reports/failure_aware_vppv_severity_holdout.md):
  low/medium-to-high severity holdout check for mechanism boundaries.
- [failure_aware_vppv_mixed_perturbation_priority.md](../reports/failure_aware_vppv_mixed_perturbation_priority.md):
  offline mixed-perturbation priority audit over composed step evidence.
- [failure_aware_vppv_model_derived_routing.md](../reports/failure_aware_vppv_model_derived_routing.md):
  rollout behavior clustering and route assignment analysis.
- [failure_aware_vppv_true_mixed_rollouts.md](../reports/failure_aware_vppv_true_mixed_rollouts.md):
  true SurRoL/PyBullet mixed-fault rollout report.
- [failure_aware_vppv_final_teacher_brief.md](../reports/failure_aware_vppv_final_teacher_brief.md):
  final teacher-facing VPPV evidence package.
- [failure_aware_vppv_github_readiness_audit.md](../reports/failure_aware_vppv_github_readiness_audit.md):
  claim calibration and public-repository readiness audit.
- [ECG_STYLE_RL_UPGRADE.md](ECG_STYLE_RL_UPGRADE.md): broad ECG-style
  reliability analysis and model-upgrade summary.
- [FIGURE_ATLAS.md](FIGURE_ATLAS.md): visual evidence inventory.
- [evidence_index.md](evidence_index.md): claim-to-evidence map.
- [PROJECT_INDEX.md](PROJECT_INDEX.md): short public entry point.

## Scope Boundary

This repository does not claim real-robot or clinical validation. It is a
simulation research prototype for runtime reliability supervision in surgical
robot learning.
