# SurRoL NeedlePick Monitor Recovery

## Takeaway

This experiment tests whether a simple runtime monitor can recover NeedlePick from action corruption. The monitor triggers on distance regression, moving farther than the initial state, action anomaly, clipping, or sustained stalls, then temporarily overrides the corrupted action with the clean scripted oracle.

## Setup

- Task: NeedlePick
- Failures: none, action_noise, action_dropout, execution_slip
- Max steps: 200
- Recovery override window: 8 steps
- Controllers: clean, perturbed, monitor_corrected

## Episode Summary

| Failure | Controller | Episodes | Success | Final Distance | Distance Reduction | Risk Event | Monitor Triggers | Override Rate | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| none | clean | 3 | 1.000 | 0.021 | 0.202 | 0.000 | 0.000 | 0.000 | 40.667 |
| none | monitor_corrected | 3 | 1.000 | 0.021 | 0.202 | 0.000 | 0.000 | 0.000 | 40.667 |
| action_noise | clean | 3 | 1.000 | 0.021 | 0.202 | 0.000 | 0.000 | 0.000 | 40.667 |
| action_noise | perturbed | 3 | 0.000 | 0.210 | 0.013 | 0.890 | 0.000 | 0.000 | 200.000 |
| action_noise | monitor_corrected | 3 | 0.333 | 0.156 | 0.067 | 0.112 | 16.667 | 0.867 | 152.000 |
| action_dropout | clean | 3 | 1.000 | 0.021 | 0.202 | 0.000 | 0.000 | 0.000 | 40.667 |
| action_dropout | perturbed | 3 | 0.000 | 0.197 | 0.026 | 0.313 | 0.000 | 0.000 | 200.000 |
| action_dropout | monitor_corrected | 3 | 0.000 | 0.189 | 0.034 | 0.083 | 16.667 | 0.653 | 200.000 |
| execution_slip | clean | 3 | 1.000 | 0.021 | 0.202 | 0.000 | 0.000 | 0.000 | 40.667 |
| execution_slip | perturbed | 3 | 0.000 | 0.223 | 0.000 | 0.250 | 0.000 | 0.000 | 200.000 |
| execution_slip | monitor_corrected | 3 | 0.000 | 0.190 | 0.033 | 0.085 | 17.000 | 0.675 | 200.000 |

## Interpretation

- If monitor_corrected improves success over perturbed, the risk trigger is doing useful control work.
- If monitor_corrected only lowers final distance but not success, the recovery action is partially helpful but the trigger/window needs tuning.
- If clean succeeds and perturbed fails, NeedlePick is a valid failure-aware benchmark.
