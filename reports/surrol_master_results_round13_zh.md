# SurRoL Reliability-Supervised Recovery Master Results

## Takeaway

The current prototype now separates recoverable execution drift from visual-state uncertainty. Across NeedlePick and GauzeRetrieve, standard action corruptions and near-target drift can be handled by short-window monitor recovery, while perception-bias and depth-scale errors remain unrecovered and should be routed to review or visual-state re-estimation. The strongest hard-fault evidence remains the 10-seed observable-proxy jaw-stuck test, where both core tasks recover from 0/10 perturbed success to 10/10 monitor-corrected success.

## Key Paired Results

| Suite | Task | Failure | Policy | Seeds | Perturbed | Recovered | Triggers | Phase Replans | Steps |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| silent_jaw_stuck | GauzeRetrieve | jaw_stuck_open | internal_phase_replan | 5 | 0.000 | 1.000 | 5.000 | 2.000 | 108.600 |
| silent_jaw_stuck | NeedlePick | jaw_stuck_open | internal_phase_replan | 5 | 0.000 | 1.000 | 3.400 | 1.200 | 91.200 |
| silent_jaw_stuck_observable_proxy | GauzeRetrieve | jaw_stuck_open | observable_phase_replan | 5 | 0.000 | 1.000 | 3.000 | 2.000 | 102.000 |
| silent_jaw_stuck_observable_proxy | NeedlePick | jaw_stuck_open | observable_phase_replan | 5 | 0.000 | 1.000 | 3.000 | 1.800 | 102.400 |
| silent_jaw_stuck_observable_proxy_10seed | GauzeRetrieve | jaw_stuck_open | observable_phase_replan | 10 | 0.000 | 1.000 | 3.000 | 2.000 | 101.800 |
| silent_jaw_stuck_observable_proxy_10seed | NeedlePick | jaw_stuck_open | observable_phase_replan | 10 | 0.000 | 1.000 | 3.000 | 1.700 | 102.600 |
| standard_corruptions | GauzeRetrieve | action_dropout | internal_phase_replan | 5 | 0.000 | 1.000 | 1.000 | 0.000 | 35.600 |
| standard_corruptions | GauzeRetrieve | action_noise | internal_phase_replan | 5 | 0.000 | 1.000 | 1.800 | 0.000 | 34.600 |
| standard_corruptions | GauzeRetrieve | execution_slip | internal_phase_replan | 5 | 0.000 | 1.000 | 1.000 | 0.000 | 35.800 |
| standard_corruptions | NeedlePick | action_dropout | internal_phase_replan | 5 | 0.000 | 1.000 | 2.800 | 0.800 | 74.200 |
| standard_corruptions | NeedlePick | action_noise | internal_phase_replan | 5 | 0.000 | 1.000 | 2.000 | 0.000 | 40.000 |
| standard_corruptions | NeedlePick | execution_slip | internal_phase_replan | 5 | 0.000 | 1.000 | 2.400 | 0.400 | 58.000 |
| standard_corruptions_10seed | GauzeRetrieve | action_dropout | internal_phase_replan | 10 | 0.000 | 1.000 | 1.000 | 0.000 | 35.500 |
| standard_corruptions_10seed | GauzeRetrieve | action_noise | internal_phase_replan | 10 | 0.000 | 1.000 | 1.800 | 0.000 | 34.700 |
| standard_corruptions_10seed | GauzeRetrieve | execution_slip | internal_phase_replan | 10 | 0.000 | 1.000 | 1.400 | 0.200 | 43.900 |
| standard_corruptions_10seed | NeedlePick | action_dropout | internal_phase_replan | 10 | 0.000 | 1.000 | 3.000 | 1.000 | 84.400 |
| standard_corruptions_10seed | NeedlePick | action_noise | internal_phase_replan | 10 | 0.000 | 0.900 | 16.800 | 14.700 | 62.400 |
| standard_corruptions_10seed | NeedlePick | execution_slip | internal_phase_replan | 10 | 0.000 | 1.000 | 3.500 | 1.200 | 94.100 |
| third_task_reach_freeze | NeedleReach | action_freeze | oracle_override | 5 | 0.000 | 1.000 | 2.000 | 0.000 | 21.200 |
| visual_state_drift_5seed | GauzeRetrieve | depth_scale_error | risk_triage_oracle_override | 5 | 0.000 | 0.000 | 0.000 | 0.000 | 180.000 |
| visual_state_drift_5seed | GauzeRetrieve | near_target_drift | risk_triage_oracle_override | 5 | 0.000 | 1.000 | 1.000 | 0.000 | 34.600 |
| visual_state_drift_5seed | GauzeRetrieve | perception_bias | risk_triage_oracle_override | 5 | 0.000 | 0.000 | 0.000 | 0.000 | 180.000 |
| visual_state_drift_5seed | NeedlePick | depth_scale_error | risk_triage_oracle_override | 5 | 0.000 | 0.000 | 1.600 | 0.000 | 180.000 |
| visual_state_drift_5seed | NeedlePick | near_target_drift | risk_triage_oracle_override | 5 | 0.200 | 1.000 | 1.000 | 0.000 | 39.800 |
| visual_state_drift_5seed | NeedlePick | perception_bias | risk_triage_oracle_override | 5 | 0.000 | 0.000 | 1.600 | 0.000 | 180.000 |
| visual_state_reestimate_10seed | GauzeRetrieve | depth_scale_error | review_reestimate | 10 | 0.000 | 1.000 | 1.000 | 0.000 | 34.600 |
| visual_state_reestimate_10seed | GauzeRetrieve | perception_bias | review_reestimate | 10 | 0.000 | 1.000 | 1.000 | 0.000 | 34.600 |
| visual_state_reestimate_10seed | NeedlePick | depth_scale_error | review_reestimate | 10 | 0.000 | 1.000 | 1.000 | 0.000 | 40.800 |
| visual_state_reestimate_10seed | NeedlePick | perception_bias | review_reestimate | 10 | 0.000 | 1.000 | 1.000 | 0.000 | 40.800 |
| visual_state_reestimate_5seed | GauzeRetrieve | depth_scale_error | review_reestimate | 5 | 0.000 | 1.000 | 1.000 | 0.000 | 34.600 |
| visual_state_reestimate_5seed | GauzeRetrieve | perception_bias | review_reestimate | 5 | 0.000 | 1.000 | 1.000 | 0.000 | 34.600 |
| visual_state_reestimate_5seed | NeedlePick | depth_scale_error | review_reestimate | 5 | 0.000 | 1.000 | 1.000 | 0.000 | 40.000 |
| visual_state_reestimate_5seed | NeedlePick | perception_bias | review_reestimate | 5 | 0.000 | 1.000 | 1.000 | 0.000 | 40.000 |

## Visual-State Error And Near-Target Drift

| Task | Failure | Perturbed | Monitor | Suggested Route |
|---|---|---:|---:|---|
| GauzeRetrieve | depth_scale_error | 0.000 | 0.000 | human review / re-estimate state |
| GauzeRetrieve | near_target_drift | 0.000 | 1.000 | auto recovery |
| GauzeRetrieve | perception_bias | 0.000 | 0.000 | human review / re-estimate state |
| NeedlePick | depth_scale_error | 0.000 | 0.000 | human review / re-estimate state |
| NeedlePick | near_target_drift | 0.200 | 1.000 | auto recovery |
| NeedlePick | perception_bias | 0.000 | 0.000 | human review / re-estimate state |

## Review-Triggered Visual-State Re-Estimation

| Task | Failure | Perturbed | Blind Monitor | Re-Estimate |
|---|---|---:|---:|---:|
| GauzeRetrieve | depth_scale_error | 0.000 | 0.000 | 1.000 |
| GauzeRetrieve | perception_bias | 0.000 | 0.000 | 1.000 |
| NeedlePick | depth_scale_error | 0.000 | 0.000 | 1.000 |
| NeedlePick | perception_bias | 0.000 | 0.000 | 1.000 |

## 10-Seed Observable Proxy Result

| Task | Failure | Perturbed | Observable Recovery | Mean Grasp Retries | Mean Steps |
|---|---|---:|---:|---:|---:|
| GauzeRetrieve | jaw_stuck_open | 0.000 | 1.000 | 2.000 | 101.800 |
| NeedlePick | jaw_stuck_open | 0.000 | 1.000 | 1.700 | 102.600 |

## Interpretation

- Standard action corruptions show that runtime correction can recover corrupted rollouts across NeedlePick and GauzeRetrieve.
- VPPV-aligned visual-state proxy errors are not solved by blind recovery; they motivate review or re-estimation.
- Review-triggered visual-state re-estimation closes this loop in simulation, recovering perception/depth failures that blind override cannot recover.
- Near-target drift is recoverable with a short monitor override, matching the intended scope of a low-intrusion supervisor.
- Silent jaw-stuck faults show that grasp-stage failures require phase-aware retry rather than only short-horizon action correction.
- Observable proxy recovery keeps the 10-seed hard-fault success at 10/10 for both tasks while moving the replan decision away from direct waypoint/activation checks.

## Limitations

- This is still a simulation-only SurRoL prototype.
- The observable proxy is rule-based, not learned uncertainty estimation.
- Recovery primitives still call SurRoL waypoint generation, even when the replan decision uses proxy signals.
- The broader standard-corruption suite remains 5 seed; only the key observable hard-fault setting is currently 10 seed.