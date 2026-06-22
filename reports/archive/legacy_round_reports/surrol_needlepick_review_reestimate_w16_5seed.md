# SurRoL NeedlePick Monitor Recovery

## Takeaway

This experiment tests whether a simple runtime monitor can supervise NeedlePick under action, perception-state, or near-target drift corruptions. The monitor triggers on distance regression, moving farther than the initial state, action anomaly, clipping, or sustained stalls, then temporarily overrides the corrupted action with the clean scripted oracle.

## Setup

- Task: NeedlePick
- Failures: none, perception_bias, depth_scale_error
- Max steps: 180
- Recovery override window: 16 steps
- Trigger mode: goalaware
- Recovery policy: review_reestimate
- Controllers: clean, perturbed, monitor_corrected

## Episode Summary

| Failure | Controller | Episodes | Success | Final Distance | Distance Reduction | Risk Event | Monitor Triggers | Replans | Override Rate | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| none | clean | 5 | 1.000 | 0.020 | 0.199 | 0.000 | 0.000 | 0.000 | 0.000 | 40.000 |
| none | monitor_corrected | 5 | 1.000 | 0.020 | 0.199 | 0.000 | 0.000 | 0.000 | 0.000 | 40.000 |
| perception_bias | clean | 5 | 1.000 | 0.020 | 0.199 | 0.000 | 0.000 | 0.000 | 0.000 | 40.000 |
| perception_bias | perturbed | 5 | 0.000 | 0.226 | -0.008 | 0.140 | 0.000 | 0.000 | 0.000 | 180.000 |
| perception_bias | monitor_corrected | 5 | 1.000 | 0.020 | 0.199 | 0.000 | 1.000 | 1.000 | 0.000 | 40.000 |
| depth_scale_error | clean | 5 | 1.000 | 0.020 | 0.199 | 0.000 | 0.000 | 0.000 | 0.000 | 40.000 |
| depth_scale_error | perturbed | 5 | 0.000 | 0.218 | -0.000 | 0.142 | 0.000 | 0.000 | 0.000 | 180.000 |
| depth_scale_error | monitor_corrected | 5 | 1.000 | 0.020 | 0.199 | 0.000 | 1.000 | 1.000 | 0.000 | 40.000 |

## Interpretation

- If monitor_corrected improves success over perturbed, the risk trigger is doing useful control work.
- If monitor_corrected only lowers final distance but not success, the recovery action is partially helpful but the case may need review or re-estimation rather than blind retry.
- If clean succeeds and perturbed fails, NeedlePick is a valid failure-aware benchmark.
