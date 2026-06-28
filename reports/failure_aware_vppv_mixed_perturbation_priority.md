# Failure-Aware VPPV Mixed-Perturbation Priority Test

This is an offline compositional stress test. It does not claim that new
mixed-fault SurRoL rollouts were executed. Instead, it combines existing
single-mechanism step evidence traces by task and step using a max
composition rule, then checks whether the router preserves the intended
priority order when multiple evidence families are active together.

Priority order: `depth_scale_error` -> `visual_estimation_bias` ->
`policy_approach_drift`.

## Route Metrics

| model | rows | scenarios | accuracy | macro_f1 | missed_intervention_rate | wrong_priority_rate | route_diversity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| priority_router | 1440 | 8 | 1.000 | 1.000 | 0.000 | 0.000 | 2 |
| max_signal_router | 1440 | 8 | 0.051 | 0.033 | 0.000 | 0.949 | 2 |
| uniform_retry | 1440 | 8 | 0.000 | 0.000 | 0.000 | 1.000 | 1 |
| single_score_retry | 1440 | 8 | 0.000 | 0.000 | 0.250 | 1.000 | 2 |

## Scenario-Level Evidence And Route Match

| task | mixed_components | expected_route | mean_visual_evidence | mean_depth_evidence | mean_policy_evidence | priority_router_match | max_signal_match | uniform_retry_match |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GauzeRetrieve | depth_scale_error+policy_approach_drift | depth_reestimate_or_cautious_approach | 1.000 | 1.000 | 0.685 | 1.000 | 0.000 | 0.000 |
| GauzeRetrieve | visual_estimation_bias+depth_scale_error | depth_reestimate_or_cautious_approach | 1.000 | 1.000 | 0.286 | 1.000 | 0.000 | 0.000 |
| GauzeRetrieve | visual_estimation_bias+depth_scale_error+policy_approach_drift | depth_reestimate_or_cautious_approach | 1.000 | 1.000 | 0.689 | 1.000 | 0.000 | 0.000 |
| GauzeRetrieve | visual_estimation_bias+policy_approach_drift | reobserve_reestimate | 0.759 | 0.078 | 0.688 | 1.000 | 0.178 | 0.000 |
| NeedlePick | depth_scale_error+policy_approach_drift | depth_reestimate_or_cautious_approach | 1.000 | 1.000 | 0.672 | 1.000 | 0.000 | 0.000 |
| NeedlePick | visual_estimation_bias+depth_scale_error | depth_reestimate_or_cautious_approach | 1.000 | 1.000 | 0.204 | 1.000 | 0.000 | 0.000 |
| NeedlePick | visual_estimation_bias+depth_scale_error+policy_approach_drift | depth_reestimate_or_cautious_approach | 1.000 | 1.000 | 0.672 | 1.000 | 0.000 | 0.000 |
| NeedlePick | visual_estimation_bias+policy_approach_drift | reobserve_reestimate | 0.759 | 0.078 | 0.671 | 1.000 | 0.233 | 0.000 |

## Interpretation

- A generic retry route fails because mixed visual/depth faults should not
  be treated as approach drift.
- A max-signal router is unstable under visual-depth confounding: when depth
  error also produces a large visual residual, simply picking the largest
  evidence family can select the wrong mechanism.
- The priority router keeps the intended route because depth is evaluated
  before visual residuals, and visual state is evaluated before policy
  correction.

## Scope Boundary

This is not a replacement for real mixed-fault simulation. It is a
mechanism-priority audit over already generated step evidence. The next
stronger experiment is to run true mixed perturbation rollouts in SurRoL
and compare their traces against this offline priority prediction.

## Output Tables And Figures

- `reports/tables/failure_aware_vppv_mixed_priority_dataset.csv`
- `reports/tables/failure_aware_vppv_mixed_priority_summary.csv`
- `reports/tables/failure_aware_vppv_mixed_priority_scenarios.csv`
- `reports/tables/failure_aware_vppv_mixed_priority_confusion.csv`
- `reports/figures/failure_aware_vppv/failure_aware_vppv_mixed_priority_evidence.png`
- `reports/figures/failure_aware_vppv/failure_aware_vppv_mixed_priority_routes.png`
