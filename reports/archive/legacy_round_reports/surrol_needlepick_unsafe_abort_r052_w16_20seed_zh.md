# SurRoL NeedlePick Monitor Recovery

## Takeaway

This experiment tests whether a simple runtime monitor can supervise NeedlePick under action, perception-state, or near-target drift corruptions. The monitor triggers on distance regression, moving farther than the initial state, action anomaly, clipping, or sustained stalls, then temporarily overrides the corrupted action with the clean scripted oracle.

## Setup

- Task: NeedlePick
- Failures: none, near_target_drift
- Max steps: 160
- Recovery override window: 16 steps
- Trigger mode: goalaware
- Recovery policy: risk_aware_abort
- Controllers: clean, perturbed, monitor_corrected

## Episode Summary

| Failure | Controller | Episodes | Success | Final Distance | Distance Reduction | Risk Event | Monitor Triggers | Replans | Override Rate | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| none | clean | 20 | 1.000 | 0.019 | 0.194 | 0.000 | 0.000 | 0.000 | 0.000 | 40.750 |
| none | monitor_corrected | 20 | 0.850 | 0.026 | 0.187 | 0.000 | 0.150 | 0.000 | 0.000 | 40.350 |
| near_target_drift | clean | 20 | 1.000 | 0.019 | 0.194 | 0.000 | 0.000 | 0.000 | 0.000 | 40.750 |
| near_target_drift | perturbed | 20 | 0.000 | 0.111 | 0.103 | 0.472 | 0.000 | 0.000 | 0.000 | 160.000 |
| near_target_drift | monitor_corrected | 20 | 0.550 | 0.044 | 0.170 | 0.026 | 1.450 | 0.000 | 0.040 | 39.150 |

## Interpretation

- If monitor_corrected improves success over perturbed, the risk trigger is doing useful control work.
- If monitor_corrected only lowers final distance but not success, the recovery action is partially helpful but the case may need review or re-estimation rather than blind retry.
- If clean succeeds and perturbed fails, NeedlePick is a valid failure-aware benchmark.
