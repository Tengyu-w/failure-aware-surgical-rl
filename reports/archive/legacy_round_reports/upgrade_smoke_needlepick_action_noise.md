# SurRoL NeedlePick Monitor Recovery

## Takeaway

This experiment tests whether a simple runtime monitor can supervise NeedlePick under action, perception-state, or near-target drift corruptions. The monitor triggers on distance regression, moving farther than the initial state, action anomaly, clipping, or sustained stalls, then temporarily overrides the corrupted action with the clean scripted oracle.

## Setup

- Task: NeedlePick
- Failures: action_noise
- Max steps: 20
- Recovery override window: 8 steps
- Trigger mode: goalaware
- Recovery policy: phase_replan
- Controllers: clean, perturbed, monitor_corrected

## Episode Summary

| Failure | Controller | Episodes | Success | Final Distance | Distance Reduction | Risk Event | Monitor Triggers | Replans | Override Rate | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| action_noise | clean | 1 | 0.000 | 0.225 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 20.000 |
| action_noise | perturbed | 1 | 0.000 | 0.225 | 0.000 | 0.950 | 0.000 | 0.000 | 0.000 | 20.000 |
| action_noise | monitor_corrected | 1 | 0.000 | 0.225 | 0.000 | 0.150 | 3.000 | 0.000 | 0.850 | 20.000 |

## Interpretation

- If monitor_corrected improves success over perturbed, the risk trigger is doing useful control work.
- If monitor_corrected only lowers final distance but not success, the recovery action is partially helpful but the case may need review or re-estimation rather than blind retry.
- If clean succeeds and perturbed fails, NeedlePick is a valid failure-aware benchmark.
