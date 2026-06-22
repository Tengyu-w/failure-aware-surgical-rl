# SurRoL NeedlePick Monitor Recovery

## Takeaway

This experiment tests whether a simple runtime monitor can supervise NeedlePick under action, perception-state, or near-target drift corruptions. The monitor triggers on distance regression, moving farther than the initial state, action anomaly, clipping, or sustained stalls, then temporarily overrides the corrupted action with the clean scripted oracle.

## Setup

- Task: NeedlePick
- Failures: none, near_target_drift
- Max steps: 180
- Recovery override window: 16 steps
- Trigger mode: goalaware
- Recovery policy: risk_aware_abort
- Controllers: clean, perturbed, monitor_corrected

## Episode Summary

| Failure | Controller | Episodes | Success | Final Distance | Distance Reduction | Risk Event | Monitor Triggers | Replans | Override Rate | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| none | clean | 5 | 1.000 | 0.020 | 0.199 | 0.000 | 0.000 | 0.000 | 0.000 | 40.000 |
| none | monitor_corrected | 5 | 0.800 | 0.023 | 0.195 | 0.000 | 0.200 | 0.000 | 0.000 | 39.800 |
| near_target_drift | clean | 5 | 1.000 | 0.020 | 0.199 | 0.000 | 0.000 | 0.000 | 0.000 | 40.000 |
| near_target_drift | perturbed | 5 | 0.000 | 0.123 | 0.096 | 0.490 | 0.000 | 0.000 | 0.000 | 180.000 |
| near_target_drift | monitor_corrected | 5 | 0.400 | 0.049 | 0.169 | 0.026 | 1.600 | 0.000 | 0.035 | 38.200 |

## Interpretation

- If monitor_corrected improves success over perturbed, the risk trigger is doing useful control work.
- If monitor_corrected only lowers final distance but not success, the recovery action is partially helpful but the case may need review or re-estimation rather than blind retry.
- If clean succeeds and perturbed fails, NeedlePick is a valid failure-aware benchmark.
