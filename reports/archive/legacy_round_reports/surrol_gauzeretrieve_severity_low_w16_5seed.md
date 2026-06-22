# SurRoL GauzeRetrieve Monitor Recovery

## Takeaway

This experiment tests whether a simple runtime monitor can supervise GauzeRetrieve under action, perception-state, or near-target drift corruptions. The monitor triggers on distance regression, moving farther than the initial state, action anomaly, clipping, or sustained stalls, then temporarily overrides the corrupted action with the clean scripted oracle.

## Setup

- Task: GauzeRetrieve
- Failures: none, perception_bias, depth_scale_error, near_target_drift
- Max steps: 180
- Recovery override window: 16 steps
- Trigger mode: goalaware
- Recovery policy: oracle_override
- Controllers: clean, perturbed, monitor_corrected

## Episode Summary

| Failure | Controller | Episodes | Success | Final Distance | Distance Reduction | Risk Event | Monitor Triggers | Replans | Override Rate | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| none | clean | 5 | 1.000 | 0.013 | 0.252 | 0.000 | 0.000 | 0.000 | 0.000 | 34.600 |
| none | monitor_corrected | 5 | 1.000 | 0.013 | 0.252 | 0.000 | 0.000 | 0.000 | 0.000 | 34.600 |
| perception_bias | clean | 5 | 1.000 | 0.013 | 0.252 | 0.000 | 0.000 | 0.000 | 0.000 | 34.600 |
| perception_bias | perturbed | 5 | 1.000 | 0.013 | 0.252 | 0.000 | 0.000 | 0.000 | 0.000 | 34.600 |
| perception_bias | monitor_corrected | 5 | 1.000 | 0.013 | 0.252 | 0.000 | 0.000 | 0.000 | 0.000 | 34.600 |
| depth_scale_error | clean | 5 | 1.000 | 0.013 | 0.252 | 0.000 | 0.000 | 0.000 | 0.000 | 34.600 |
| depth_scale_error | perturbed | 5 | 0.000 | 0.268 | -0.004 | 0.163 | 0.000 | 0.000 | 0.000 | 180.000 |
| depth_scale_error | monitor_corrected | 5 | 0.000 | 0.268 | -0.003 | 0.163 | 2.000 | 0.000 | 0.162 | 180.000 |
| near_target_drift | clean | 5 | 1.000 | 0.013 | 0.252 | 0.000 | 0.000 | 0.000 | 0.000 | 34.600 |
| near_target_drift | perturbed | 5 | 1.000 | 0.018 | 0.246 | 0.000 | 0.000 | 0.000 | 0.000 | 35.000 |
| near_target_drift | monitor_corrected | 5 | 1.000 | 0.018 | 0.246 | 0.000 | 0.000 | 0.000 | 0.000 | 35.000 |

## Interpretation

- If monitor_corrected improves success over perturbed, the risk trigger is doing useful control work.
- If monitor_corrected only lowers final distance but not success, the recovery action is partially helpful but the case may need review or re-estimation rather than blind retry.
- If clean succeeds and perturbed fails, GauzeRetrieve is a valid failure-aware benchmark.
