# SurRoL NeedlePick Monitor Recovery

## Takeaway

This experiment tests whether a simple runtime monitor can recover NeedlePick from action corruption. The monitor triggers on distance regression, moving farther than the initial state, action anomaly, clipping, or sustained stalls, then temporarily overrides the corrupted action with the clean scripted oracle.

## Setup

- Task: NeedlePick
- Failures: none, action_noise
- Max steps: 200
- Recovery override window: 32 steps
- Trigger mode: goalaware
- Controllers: clean, perturbed, monitor_corrected

## Episode Summary

| Failure | Controller | Episodes | Success | Final Distance | Distance Reduction | Risk Event | Monitor Triggers | Override Rate | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| none | clean | 3 | 1.000 | 0.021 | 0.202 | 0.000 | 0.000 | 0.000 | 40.667 |
| none | monitor_corrected | 3 | 1.000 | 0.021 | 0.202 | 0.000 | 0.000 | 0.000 | 40.667 |
| action_noise | clean | 3 | 1.000 | 0.021 | 0.202 | 0.000 | 0.000 | 0.000 | 40.667 |
| action_noise | perturbed | 3 | 0.000 | 0.210 | 0.013 | 0.890 | 0.000 | 0.000 | 200.000 |
| action_noise | monitor_corrected | 3 | 0.667 | 0.104 | 0.119 | 0.043 | 3.667 | 0.955 | 95.667 |

## Interpretation

- If monitor_corrected improves success over perturbed, the risk trigger is doing useful control work.
- If monitor_corrected only lowers final distance but not success, the recovery action is partially helpful but the trigger/window needs tuning.
- If clean succeeds and perturbed fails, NeedlePick is a valid failure-aware benchmark.
