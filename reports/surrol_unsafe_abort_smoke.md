# SurRoL NeedlePick Monitor Recovery

## Takeaway

This experiment tests whether a simple runtime monitor can supervise NeedlePick under action, perception-state, or near-target drift corruptions. The monitor triggers on distance regression, moving farther than the initial state, action anomaly, clipping, or sustained stalls, then temporarily overrides the corrupted action with the clean scripted oracle.

## Setup

- Task: NeedlePick
- Failures: none, near_target_drift
- Max steps: 120
- Recovery override window: 16 steps
- Trigger mode: goalaware
- Recovery policy: risk_aware_abort
- Controllers: clean, perturbed, monitor_corrected

## Episode Summary

| Failure | Controller | Episodes | Success | Final Distance | Distance Reduction | Risk Event | Monitor Triggers | Replans | Override Rate | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| none | clean | 1 | 1.000 | 0.021 | 0.204 | 0.000 | 0.000 | 0.000 | 0.000 | 44.000 |
| none | monitor_corrected | 1 | 1.000 | 0.021 | 0.204 | 0.000 | 0.000 | 0.000 | 0.000 | 44.000 |
| near_target_drift | clean | 1 | 1.000 | 0.021 | 0.204 | 0.000 | 0.000 | 0.000 | 0.000 | 44.000 |
| near_target_drift | perturbed | 1 | 0.000 | 0.126 | 0.099 | 0.417 | 0.000 | 0.000 | 0.000 | 120.000 |
| near_target_drift | monitor_corrected | 1 | 1.000 | 0.020 | 0.205 | 0.023 | 1.000 | 0.000 | 0.068 | 44.000 |

## Interpretation

- If monitor_corrected improves success over perturbed, the risk trigger is doing useful control work.
- If monitor_corrected only lowers final distance but not success, the recovery action is partially helpful but the case may need review or re-estimation rather than blind retry.
- If clean succeeds and perturbed fails, NeedlePick is a valid failure-aware benchmark.
