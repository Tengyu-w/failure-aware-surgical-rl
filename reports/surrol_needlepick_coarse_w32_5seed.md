# SurRoL NeedlePick Monitor Recovery

## Takeaway

This experiment tests whether a simple runtime monitor can recover NeedlePick from action corruption. The monitor triggers on distance regression, moving farther than the initial state, action anomaly, clipping, or sustained stalls, then temporarily overrides the corrupted action with the clean scripted oracle.

## Setup

- Task: NeedlePick
- Failures: none, action_noise, action_dropout, execution_slip
- Max steps: 200
- Recovery override window: 32 steps
- Trigger mode: coarse
- Controllers: clean, perturbed, monitor_corrected

## Episode Summary

| Failure | Controller | Episodes | Success | Final Distance | Distance Reduction | Risk Event | Monitor Triggers | Override Rate | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| none | clean | 5 | 1.000 | 0.020 | 0.199 | 0.694 | 0.000 | 0.000 | 40.000 |
| none | monitor_corrected | 5 | 1.000 | 0.020 | 0.199 | 0.694 | 1.000 | 0.799 | 40.000 |
| action_noise | clean | 5 | 1.000 | 0.020 | 0.199 | 0.694 | 0.000 | 0.000 | 40.000 |
| action_noise | perturbed | 5 | 0.000 | 0.217 | 0.001 | 0.995 | 0.000 | 0.000 | 200.000 |
| action_noise | monitor_corrected | 5 | 1.000 | 0.020 | 0.198 | 0.735 | 2.000 | 0.964 | 40.000 |
| action_dropout | clean | 5 | 1.000 | 0.020 | 0.199 | 0.694 | 0.000 | 0.000 | 40.000 |
| action_dropout | perturbed | 5 | 0.000 | 0.195 | 0.024 | 0.966 | 0.000 | 0.000 | 200.000 |
| action_dropout | monitor_corrected | 5 | 0.200 | 0.131 | 0.088 | 0.893 | 5.800 | 0.962 | 169.000 |
| execution_slip | clean | 5 | 1.000 | 0.020 | 0.199 | 0.694 | 0.000 | 0.000 | 40.000 |
| execution_slip | perturbed | 5 | 0.000 | 0.220 | -0.001 | 0.964 | 0.000 | 0.000 | 200.000 |
| execution_slip | monitor_corrected | 5 | 0.600 | 0.075 | 0.144 | 0.815 | 4.000 | 0.976 | 106.000 |

## Interpretation

- If monitor_corrected improves success over perturbed, the risk trigger is doing useful control work.
- If monitor_corrected only lowers final distance but not success, the recovery action is partially helpful but the trigger/window needs tuning.
- If clean succeeds and perturbed fails, NeedlePick is a valid failure-aware benchmark.
