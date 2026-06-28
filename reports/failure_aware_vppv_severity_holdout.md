# Failure-Aware VPPV Severity-Held-Out Evaluation

This report uses the existing SurRoL severity sweep as a lightweight
boundary test. Low and medium severity rows are used to learn, for each
task/failure pair, the first severity level where intervention becomes
necessary. High severity is then held out and evaluated with frozen
boundaries.

## High-Severity Held-Out Results

| model | split | rows | seeds_total | accuracy | macro_f1 | missed_intervention_rate | false_intervention_rate | route_diversity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| boundary_router | high_holdout | 6 | 30 | 1.000 | 1.000 | 0.000 | 0.000 | 3 |
| family_only | high_holdout | 6 | 30 | 1.000 | 1.000 | 0.000 | 0.000 | 3 |
| uniform_retry | high_holdout | 6 | 30 | 0.333 | 0.167 | 0.000 | 0.000 | 1 |

## Learned Low/Medium Intervention Boundaries

| task | failure | learned_min_intervention_rank | learned_min_intervention_severity |
| --- | --- | --- | --- |
| GauzeRetrieve | depth_scale_error | 0 | low |
| GauzeRetrieve | near_target_drift | 1 | medium |
| GauzeRetrieve | perception_bias | 1 | medium |
| NeedlePick | depth_scale_error | 0 | low |
| NeedlePick | near_target_drift | 0 | low |
| NeedlePick | perception_bias | 0 | low |

## High-Severity Route Details

| task | failure | severity | seeds | perturbed_success | monitor_success | expected_route | boundary_router_route | family_only_route |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GauzeRetrieve | depth_scale_error | high | 5 | 0.000 | 0.000 | depth_reestimate_or_cautious_approach | depth_reestimate_or_cautious_approach | depth_reestimate_or_cautious_approach |
| NeedlePick | depth_scale_error | high | 5 | 0.000 | 0.000 | depth_reestimate_or_cautious_approach | depth_reestimate_or_cautious_approach | depth_reestimate_or_cautious_approach |
| GauzeRetrieve | near_target_drift | high | 5 | 0.000 | 1.000 | low_gain_correction_or_replan | low_gain_correction_or_replan | low_gain_correction_or_replan |
| NeedlePick | near_target_drift | high | 5 | 0.000 | 1.000 | low_gain_correction_or_replan | low_gain_correction_or_replan | low_gain_correction_or_replan |
| GauzeRetrieve | perception_bias | high | 5 | 0.000 | 0.000 | reobserve_reestimate | reobserve_reestimate | reobserve_reestimate |
| NeedlePick | perception_bias | high | 5 | 0.000 | 0.000 | reobserve_reestimate | reobserve_reestimate | reobserve_reestimate |

## Interpretation

- Depth-scale and visual/perception bias should not be treated as ordinary
  execution drift. In the severity sweep, medium/high state-estimation
  errors usually remain failed after monitor correction, so the safer route
  is re-estimation or review.
- Near-target drift is different: medium/high drift is recovered by the
  monitor in both tasks, matching the route `low_gain_correction_or_replan`.
- Low NeedlePick drift is a boundary case: it is already risky, but the
  existing monitor does not trigger enough. That is useful calibration
  evidence rather than a success claim.

## Scope Boundary

This is not an independent image-corruption benchmark. It is a severity
sweep over simulator-injected mechanism proxies with 5 seeds per
task/failure/severity. It strengthens the routing argument by checking
whether the mechanism boundary found at low/medium severity remains
valid at held-out high severity.

## Output Tables And Figures

- `reports/tables/failure_aware_vppv_severity_holdout_detailed.csv`
- `reports/tables/failure_aware_vppv_severity_holdout_boundaries.csv`
- `reports/tables/failure_aware_vppv_severity_holdout_summary.csv`
- `reports/tables/failure_aware_vppv_severity_holdout_confusion.csv`
- `reports/figures/failure_aware_vppv/failure_aware_vppv_severity_holdout.png`
- `reports/figures/failure_aware_vppv/failure_aware_vppv_severity_holdout_routes.png`
