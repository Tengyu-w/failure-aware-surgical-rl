# SurRoL NeedlePick Monitor Recovery

## Takeaway

This experiment tests whether a simple runtime monitor can recover NeedlePick from action corruption. The monitor triggers on distance regression, moving farther than the initial state, action anomaly, clipping, or sustained stalls, then temporarily overrides the corrupted action with the clean scripted oracle.

## Setup

- Task: NeedlePick
- Failures: none, perception_bias, perception_jitter, depth_scale_error, near_target_drift
- Max steps: 180
- Recovery override window: 16 steps
- Trigger mode: goalaware
- Recovery policy: oracle_override
- Controllers: clean, perturbed, monitor_corrected

## Episode Summary

| Failure | Controller | Episodes | Success | Final Distance | Distance Reduction | Risk Event | Monitor Triggers | Replans | Override Rate | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| none | clean | 2 | 1.000 | 0.022 | 0.175 | 0.000 | 0.000 | 0.000 | 0.000 | 40.000 |
| none | monitor_corrected | 2 | 1.000 | 0.022 | 0.175 | 0.000 | 0.000 | 0.000 | 0.000 | 40.000 |
| perception_bias | clean | 2 | 1.000 | 0.022 | 0.175 | 0.000 | 0.000 | 0.000 | 0.000 | 40.000 |
| perception_bias | perturbed | 2 | 0.000 | 0.211 | -0.014 | 0.350 | 0.000 | 0.000 | 0.000 | 180.000 |
| perception_bias | monitor_corrected | 2 | 0.000 | 0.211 | -0.015 | 0.350 | 4.000 | 0.000 | 0.347 | 180.000 |
| perception_jitter | clean | 2 | 1.000 | 0.022 | 0.175 | 0.000 | 0.000 | 0.000 | 0.000 | 40.000 |
| perception_jitter | perturbed | 2 | 0.000 | 0.196 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 180.000 |
| perception_jitter | monitor_corrected | 2 | 0.000 | 0.196 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 180.000 |
| depth_scale_error | clean | 2 | 1.000 | 0.022 | 0.175 | 0.000 | 0.000 | 0.000 | 0.000 | 40.000 |
| depth_scale_error | perturbed | 2 | 0.000 | 0.204 | -0.007 | 0.356 | 0.000 | 0.000 | 0.000 | 180.000 |
| depth_scale_error | monitor_corrected | 2 | 0.000 | 0.241 | -0.044 | 0.356 | 4.000 | 0.000 | 0.353 | 180.000 |
| near_target_drift | clean | 2 | 1.000 | 0.022 | 0.175 | 0.000 | 0.000 | 0.000 | 0.000 | 40.000 |
| near_target_drift | perturbed | 2 | 0.000 | 0.113 | 0.083 | 0.725 | 0.000 | 0.000 | 0.000 | 180.000 |
| near_target_drift | monitor_corrected | 2 | 1.000 | 0.019 | 0.177 | 0.025 | 1.000 | 0.000 | 0.076 | 40.000 |

## Interpretation

- If monitor_corrected improves success over perturbed, the risk trigger is doing useful control work.
- If monitor_corrected only lowers final distance but not success, the recovery action is partially helpful but the trigger/window needs tuning.
- If clean succeeds and perturbed fails, NeedlePick is a valid failure-aware benchmark.
