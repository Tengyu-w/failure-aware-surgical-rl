# SurRoL NeedleReach Monitor Recovery

## Takeaway

This experiment tests whether a simple runtime monitor can recover NeedleReach from action corruption. The monitor triggers on distance regression, moving farther than the initial state, action anomaly, clipping, or sustained stalls, then temporarily overrides the corrupted action with the clean scripted oracle.

## Setup

- Task: NeedleReach
- Failures: none, action_freeze
- Max steps: 120
- Recovery override window: 16 steps
- Trigger mode: coarse
- Recovery policy: oracle_override
- Controllers: clean, perturbed, monitor_corrected

## Episode Summary

| Failure | Controller | Episodes | Success | Final Distance | Distance Reduction | Risk Event | Monitor Triggers | Replans | Override Rate | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| none | clean | 1 | 1.000 | 0.016 | 0.462 | 0.000 | 0.000 | 0.000 | 0.000 | 23.000 |
| none | monitor_corrected | 1 | 1.000 | 0.016 | 0.462 | 0.000 | 0.000 | 0.000 | 0.000 | 23.000 |
| action_freeze | clean | 1 | 1.000 | 0.016 | 0.462 | 0.000 | 0.000 | 0.000 | 0.000 | 23.000 |
| action_freeze | perturbed | 1 | 1.000 | 0.016 | 0.462 | 0.777 | 0.000 | 0.000 | 0.000 | 103.000 |
| action_freeze | monitor_corrected | 1 | 1.000 | 0.016 | 0.462 | 0.080 | 2.000 | 0.000 | 0.920 | 25.000 |

## Interpretation

- If monitor_corrected improves success over perturbed, the risk trigger is doing useful control work.
- If monitor_corrected only lowers final distance but not success, the recovery action is partially helpful but the trigger/window needs tuning.
- If clean succeeds and perturbed fails, NeedleReach is a valid failure-aware benchmark.
