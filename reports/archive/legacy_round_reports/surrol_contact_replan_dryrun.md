# SurRoL NeedlePick Monitor Recovery

## Takeaway

This experiment tests whether a simple runtime monitor can recover NeedlePick from action corruption. The monitor triggers on distance regression, moving farther than the initial state, action anomaly, clipping, or sustained stalls, then temporarily overrides the corrupted action with the clean scripted oracle.

## Setup

- Task: NeedlePick
- Failures: action_dropout
- Max steps: 80
- Recovery override window: 32 steps
- Trigger mode: coarse
- Recovery policy: contact_replan
- Controllers: clean, perturbed, monitor_corrected

## Episode Summary

| Failure | Controller | Episodes | Success | Final Distance | Distance Reduction | Risk Event | Monitor Triggers | Replans | Override Rate | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| action_dropout | clean | 1 | 1.000 | 0.021 | 0.204 | 0.727 | 0.000 | 0.000 | 0.000 | 44.000 |
| action_dropout | perturbed | 1 | 0.000 | 0.225 | 0.000 | 0.950 | 0.000 | 0.000 | 0.000 | 80.000 |
| action_dropout | monitor_corrected | 1 | 1.000 | 0.021 | 0.204 | 0.756 | 2.000 | 0.000 | 0.956 | 45.000 |

## Interpretation

- If monitor_corrected improves success over perturbed, the risk trigger is doing useful control work.
- If monitor_corrected only lowers final distance but not success, the recovery action is partially helpful but the trigger/window needs tuning.
- If clean succeeds and perturbed fails, NeedlePick is a valid failure-aware benchmark.
