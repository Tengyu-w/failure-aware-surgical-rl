# Failure-Aware VPPV Composite Router

This report implements the fifth step of the VPPV reframing: a composite
mechanism router. It uses existing SurRoL simulator rollout evidence as
weak labels and should be read as a simulator reliability prototype, not
as clinical validation or surgeon-labeled route supervision.

## Router Logic

```text
Stage 1 boundary/unsafe risk -> abort_candidate_or_takeover
Stage 2 visual or depth state risk -> reobserve/reestimate route
Stage 3 policy approach drift -> low-gain correction or replan
Stage 4 near-target handoff failure -> human review or servo reset
Stage 5 low-risk state -> continue
```

## Composite Result

- Rows: 370
- Accuracy against weak VPPV route labels: 0.732
- Macro-F1: 0.713
- Missed non-continue rate: 0.344
- False intervention rate on nominal route: 0.010
- Missed severe-route rate: 0.328

## Baseline Comparison

| model | rows | accuracy | macro_f1 | missed_non_continue_rate | false_intervention_rate | missed_severe_rate | route_diversity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| uniform_retry | 370 | 0.670 | 0.285 | 0.000 | 0.000 | 0.000 | 2 |
| visual_only | 370 | 0.324 | 0.173 | 0.852 | 0.000 | 0.672 | 2 |
| embedding_only | 370 | 0.378 | 0.181 | 0.704 | 0.000 | 0.344 | 2 |
| single_score | 370 | 0.378 | 0.181 | 0.704 | 0.000 | 0.344 | 2 |
| composite_vppv | 370 | 0.732 | 0.713 | 0.344 | 0.010 | 0.328 | 6 |

## Mechanism Fingerprints

| mechanism_label | episodes | expected_route | observed_success_rate | mean_final_distance | top_evidence_families |
| --- | --- | --- | --- | --- | --- |
| depth_scale_error | 30 | depth_reestimate_or_cautious_approach | 0.333 | 0.169 | depth_evidence;progress_regularity_evidence;local_neighborhood_evidence |
| handoff_servo_failure | 60 | human_review_or_servo_reset | 0.667 | 0.092 | local_neighborhood_evidence;progress_regularity_evidence;handoff_evidence |
| nominal | 100 | continue | 1.000 | 0.017 | progress_regularity_evidence;local_neighborhood_evidence;composite_risk_score |
| policy_approach_drift | 148 | low_gain_correction_or_replan | 0.669 | 0.082 | progress_regularity_evidence;local_neighborhood_evidence;action_outcome_evidence |
| unsafe_near_target_continuation | 2 | abort_candidate_or_takeover | 0.000 | 0.076 | boundary_evidence;local_neighborhood_evidence;progress_regularity_evidence |
| visual_estimation_bias | 30 | reobserve_reestimate | 0.333 | 0.169 | progress_regularity_evidence;local_neighborhood_evidence;visual_evidence |

## Fixed-Budget Evidence Capture

At a 20% intervention budget, the strongest evidence families are:

| evidence | budget | selected | high_risk_capture_rate | precision_at_budget |
| --- | --- | --- | --- | --- |
| visual_evidence | 0.200 | 74 | 0.607 | 1.000 |
| depth_evidence | 0.200 | 74 | 0.607 | 1.000 |
| policy_embedding_evidence | 0.200 | 74 | 0.607 | 1.000 |
| local_neighborhood_evidence | 0.200 | 74 | 0.607 | 1.000 |
| composite_risk_score | 0.200 | 74 | 0.607 | 1.000 |

## Output Tables

- `reports/tables/failure_aware_vppv_scored_routes.csv`
- `reports/tables/failure_aware_vppv_route_summary.csv`
- `reports/tables/failure_aware_vppv_mechanism_fingerprints.csv`
- `reports/tables/failure_aware_vppv_evidence_budget_capture.csv`
- `reports/tables/failure_aware_vppv_composite_confusion.csv`

## Claim Boundary

The router uses simulator-derived mechanism labels and evidence signals.
Its value is to structure the VPPV reliability problem into visual-state,
policy-approach, handoff, and unsafe-continuation mechanisms. It does not
prove a real surgical controller, and it does not learn a new gripper or
surgical manipulation policy.
