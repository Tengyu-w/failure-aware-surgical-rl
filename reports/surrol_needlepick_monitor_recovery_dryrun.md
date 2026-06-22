# SurRoL NeedlePick Monitor Recovery

## Takeaway

This experiment tests whether a simple runtime monitor can recover NeedlePick from action corruption. The monitor triggers on distance regression, moving farther than the initial state, action anomaly, clipping, or sustained stalls, then temporarily overrides the corrupted action with the clean scripted oracle.

## Setup

- Task: NeedlePick
- Failures: action_noise
- Max steps: 50
- Recovery override window: 8 steps
- Controllers: clean, perturbed, monitor_corrected

## Episode Summary

| Failure | Controller | Episodes | Success | Final Distance | Distance Reduction | Risk Event | Monitor Triggers | Override Rate | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| action_noise | clean | 1 | 1.000 | 0.021 | 0.204 | 0.727 | 0.000 | 0.000 | 44.000 |
| action_noise | perturbed | 1 | 0.000 | 0.227 | -0.002 | 1.000 | 0.000 | 0.000 | 50.000 |
| action_noise | monitor_corrected | 1 | 1.000 | 0.023 | 0.202 | 0.773 | 6.000 | 0.955 | 44.000 |

## Interpretation

- If monitor_corrected improves success over perturbed, the risk trigger is doing useful control work.
- If monitor_corrected only lowers final distance but not success, the recovery action is partially helpful but the trigger/window needs tuning.
- If clean succeeds and perturbed fails, NeedlePick is a valid failure-aware benchmark.
