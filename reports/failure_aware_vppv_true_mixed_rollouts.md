# Failure-Aware VPPV True Mixed-Fault SurRoL Rollouts

This report runs actual SurRoL/PyBullet oracle rollouts with multiple
failure proxies injected in the same episode. It closes the gap left by
the offline mixed-priority audit: the previous audit composed evidence
traces; this run executes mixed faults through the simulator dynamics.
The current run is smoke-scale: 5 seeds per task/fault/controller cell.

## Overall Controller Comparison

| controller | episodes | success_mean | final_distance_mean | monitor_triggers_mean | recovery_override_rate_mean |
| --- | --- | --- | --- | --- | --- |
| clean | 40 | 1.000 | 0.015 | 0.000 | 0.000 |
| perturbed | 40 | 0.000 | 0.224 | 0.000 | 0.000 |
| priority_routed | 40 | 1.000 | 0.016 | 1.750 | 0.048 |

## Paired Mixed-Fault Results

| task | failure_combo | components | expected_priority_route | priority_recovery_policy | episodes | seeds | clean_success | perturbed_success | priority_routed_success | perturbed_final_distance | priority_routed_final_distance | success_gain_vs_perturbed | distance_gain_vs_perturbed | monitor_triggers_mean | visual_reestimate_triggers_mean | recovery_override_rate_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GauzeRetrieve | depth_scale_error+near_target_drift | depth_scale_error+near_target_drift | depth_reestimate_or_cautious_approach | review_reestimate | 5 | 5 | 1.000 | 0.000 | 1.000 | 0.258 | 0.013 | 1.000 | 0.245 | 2.000 | 1.000 | 0.058 |
| GauzeRetrieve | perception_bias+depth_scale_error | perception_bias+depth_scale_error | depth_reestimate_or_cautious_approach | review_reestimate | 5 | 5 | 1.000 | 0.000 | 1.000 | 0.258 | 0.013 | 1.000 | 0.245 | 1.000 | 1.000 | 0.000 |
| GauzeRetrieve | perception_bias+depth_scale_error+near_target_drift | perception_bias+depth_scale_error+near_target_drift | depth_reestimate_or_cautious_approach | review_reestimate | 5 | 5 | 1.000 | 0.000 | 1.000 | 0.258 | 0.013 | 1.000 | 0.245 | 2.000 | 1.000 | 0.058 |
| GauzeRetrieve | perception_bias+near_target_drift | perception_bias+near_target_drift | reobserve_reestimate | review_reestimate | 5 | 5 | 1.000 | 0.000 | 1.000 | 0.259 | 0.013 | 1.000 | 0.246 | 2.000 | 1.000 | 0.058 |
| NeedlePick | depth_scale_error+near_target_drift | depth_scale_error+near_target_drift | depth_reestimate_or_cautious_approach | review_reestimate | 5 | 5 | 1.000 | 0.000 | 1.000 | 0.190 | 0.021 | 1.000 | 0.169 | 2.000 | 1.000 | 0.071 |
| NeedlePick | perception_bias+depth_scale_error | perception_bias+depth_scale_error | depth_reestimate_or_cautious_approach | review_reestimate | 5 | 5 | 1.000 | 0.000 | 1.000 | 0.187 | 0.019 | 1.000 | 0.168 | 1.000 | 1.000 | 0.000 |
| NeedlePick | perception_bias+depth_scale_error+near_target_drift | perception_bias+depth_scale_error+near_target_drift | depth_reestimate_or_cautious_approach | review_reestimate | 5 | 5 | 1.000 | 0.000 | 1.000 | 0.187 | 0.021 | 1.000 | 0.166 | 2.000 | 1.000 | 0.071 |
| NeedlePick | perception_bias+near_target_drift | perception_bias+near_target_drift | reobserve_reestimate | review_reestimate | 5 | 5 | 1.000 | 0.000 | 1.000 | 0.198 | 0.021 | 1.000 | 0.177 | 2.000 | 1.000 | 0.071 |

## Priority-Routed Step Signals

| task | failure_combo | steps | expected_priority_route | recovery_policy | monitor_trigger_rate | risk_event_rate | visual_reestimate_trigger_rate | recovery_override_rate | mean_perception_error_norm | mean_action_deviation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GauzeRetrieve | depth_scale_error+near_target_drift | 173 | depth_reestimate_or_cautious_approach | review_reestimate | 0.058 | 0.029 | 0.029 | 0.058 | 0.012 | 0.015 |
| GauzeRetrieve | perception_bias+depth_scale_error | 173 | depth_reestimate_or_cautious_approach | review_reestimate | 0.029 | 0.000 | 0.029 | 0.000 | 0.013 | 0.000 |
| GauzeRetrieve | perception_bias+depth_scale_error+near_target_drift | 173 | depth_reestimate_or_cautious_approach | review_reestimate | 0.058 | 0.029 | 0.029 | 0.058 | 0.013 | 0.015 |
| GauzeRetrieve | perception_bias+near_target_drift | 173 | reobserve_reestimate | review_reestimate | 0.058 | 0.029 | 0.029 | 0.058 | 0.000 | 0.015 |
| NeedlePick | depth_scale_error+near_target_drift | 198 | depth_reestimate_or_cautious_approach | review_reestimate | 0.051 | 0.025 | 0.025 | 0.071 | 0.011 | 0.013 |
| NeedlePick | perception_bias+depth_scale_error | 201 | depth_reestimate_or_cautious_approach | review_reestimate | 0.025 | 0.000 | 0.025 | 0.000 | 0.011 | 0.000 |
| NeedlePick | perception_bias+depth_scale_error+near_target_drift | 198 | depth_reestimate_or_cautious_approach | review_reestimate | 0.051 | 0.025 | 0.025 | 0.071 | 0.011 | 0.013 |
| NeedlePick | perception_bias+near_target_drift | 198 | reobserve_reestimate | review_reestimate | 0.051 | 0.025 | 0.025 | 0.071 | 0.000 | 0.013 |

## Interpretation

- `perturbed` applies the mixed observation/action faults without a routing
  response.
- `priority_routed` selects the recovery policy from the mechanism priority
  order: depth before visual, visual before policy drift.
- All tested mixed combinations contain visual or depth state unreliability,
  so the priority route uses `review_reestimate` before allowing
  near-target drift correction to matter.
- This remains scripted-oracle simulation evidence. It is not a learned
  surgical policy or hardware validation.

## Output Tables And Figures

- `reports/tables/failure_aware_vppv_true_mixed_rollout_summary.csv`
- `reports/tables/failure_aware_vppv_true_mixed_rollout_paired.csv`
- `reports/tables/failure_aware_vppv_true_mixed_rollout_steps.csv`
- `reports/figures/failure_aware_vppv/failure_aware_vppv_true_mixed_success.png`
- `reports/figures/failure_aware_vppv/failure_aware_vppv_true_mixed_distance.png`
- `reports/figures/failure_aware_vppv/failure_aware_vppv_true_mixed_distance_traces.png`
