# Failure-Aware VPPV Cross-Task Generalization

This report tests whether the step-level evidence router transfers across
SurRoL tasks. Thresholds are calibrated on one task and frozen when testing
on the other task. This is stronger than within-task weak-label consistency,
but still uses simulator-derived mechanism labels.

## Cross-Task Router Results

| split | rows | threshold_visual | threshold_depth | threshold_policy | threshold_action | accuracy | macro_f1 | missed_high_risk_step_rate | false_alarm_on_continue_rate | route_diversity | train_task | test_task |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| test_on_GauzeRetrieve | 5365 | 0.450 | 0.450 | 0.350 | 0.450 | 1.000 | 1.000 | 0.000 | 0.000 | 4 | NeedlePick | GauzeRetrieve |
| test_on_NeedlePick | 5362 | 0.450 | 0.450 | 0.350 | 0.250 | 0.997 | 0.996 | 0.000 | 0.009 | 4 | GauzeRetrieve | NeedlePick |

## Mechanism-Gated Evidence Transfer At 10% Budget

| task | evidence | target_mechanism | budget | ranking_policy | selected_steps | capture_rate | precision_at_budget |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GauzeRetrieve | policy_embedding_proxy_evidence | policy_approach_drift | 0.100 | mechanism_gated_rank | 537 | 0.719 | 1.000 |
| GauzeRetrieve | action_outcome_mismatch_evidence | policy_approach_drift | 0.100 | mechanism_gated_rank | 537 | 0.719 | 1.000 |
| GauzeRetrieve | visual_state_evidence | visual_estimation_bias | 0.100 | mechanism_gated_rank | 537 | 0.298 | 1.000 |
| GauzeRetrieve | depth_scale_evidence | depth_scale_error | 0.100 | mechanism_gated_rank | 537 | 0.298 | 1.000 |
| NeedlePick | policy_embedding_proxy_evidence | policy_approach_drift | 0.100 | mechanism_gated_rank | 537 | 1.000 | 0.985 |
| NeedlePick | action_outcome_mismatch_evidence | policy_approach_drift | 0.100 | mechanism_gated_rank | 537 | 1.000 | 0.985 |
| NeedlePick | depth_scale_evidence | depth_scale_error | 0.100 | mechanism_gated_rank | 537 | 0.321 | 1.000 |
| NeedlePick | visual_state_evidence | visual_estimation_bias | 0.100 | mechanism_gated_rank | 537 | 0.321 | 1.000 |

## Visual Evidence Confounding Check

| task | evidence | target_mechanism | ranking_policy | capture_rate | precision_at_budget |
| --- | --- | --- | --- | --- | --- |
| GauzeRetrieve | visual_state_evidence | visual_estimation_bias | global_rank | 0.000 | 0.000 |
| NeedlePick | visual_state_evidence | visual_estimation_bias | global_rank | 0.000 | 0.000 |

## Interpretation

- Visual evidence is useful only after the depth gate. As a global ranker,
  it is confounded because depth-scale corruption also creates large
  visual-state residuals.
- Depth evidence is the first-stage gate. This is why the router does not
  treat every visual residual as the same recovery mechanism.
- Policy approach drift transfers through action-outcome and policy-proxy
  evidence, but the signal strength differs by task.
- This still is not an independent expert-label benchmark. It tests whether
  the same mechanism evidence can be calibrated on one surgical task and
  remain useful on another.

## Output Tables

- `reports/tables/failure_aware_vppv_cross_task_summary.csv`
- `reports/tables/failure_aware_vppv_cross_task_threshold_sweep.csv`
- `reports/tables/failure_aware_vppv_cross_task_evidence_transfer.csv`
- `reports/tables/failure_aware_vppv_cross_task_confusion.csv`
