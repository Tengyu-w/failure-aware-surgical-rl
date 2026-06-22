# SurRoL NeedlePick Monitor Recovery

## Takeaway

This experiment tests whether a simple runtime monitor can recover NeedlePick from action corruption. The monitor triggers on distance regression, moving farther than the initial state, action anomaly, clipping, or sustained stalls, then temporarily overrides the corrupted action with the clean scripted oracle.

## Setup

- Task: NeedlePick
- Failures: action_dropout, execution_slip
- Max steps: 200
- Recovery override window: 16 steps
- Trigger mode: coarse
- Controllers: clean, perturbed, monitor_corrected

## Episode Summary

| Failure | Controller | Episodes | Success | Final Distance | Distance Reduction | Risk Event | Monitor Triggers | Override Rate | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| action_dropout | clean | 3 | 1.000 | 0.021 | 0.202 | 0.704 | 0.000 | 0.000 | 40.667 |
| action_dropout | perturbed | 3 | 0.000 | 0.197 | 0.026 | 0.960 | 0.000 | 0.000 | 200.000 |
| action_dropout | monitor_corrected | 3 | 0.333 | 0.112 | 0.111 | 0.872 | 9.333 | 0.960 | 148.333 |
| execution_slip | clean | 3 | 1.000 | 0.021 | 0.202 | 0.704 | 0.000 | 0.000 | 40.667 |
| execution_slip | perturbed | 3 | 0.000 | 0.223 | 0.000 | 0.985 | 0.000 | 0.000 | 200.000 |
| execution_slip | monitor_corrected | 3 | 0.667 | 0.066 | 0.157 | 0.802 | 6.333 | 0.977 | 96.000 |

## Interpretation

- If monitor_corrected improves success over perturbed, the risk trigger is doing useful control work.
- If monitor_corrected only lowers final distance but not success, the recovery action is partially helpful but the trigger/window needs tuning.
- If clean succeeds and perturbed fails, NeedlePick is a valid failure-aware benchmark.
