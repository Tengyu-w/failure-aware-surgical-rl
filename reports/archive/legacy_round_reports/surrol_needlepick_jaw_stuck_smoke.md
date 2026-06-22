# SurRoL NeedlePick Monitor Recovery

## Takeaway

This experiment tests whether a simple runtime monitor can recover NeedlePick from action corruption. The monitor triggers on distance regression, moving farther than the initial state, action anomaly, clipping, or sustained stalls, then temporarily overrides the corrupted action with the clean scripted oracle.

## Setup

- Task: NeedlePick
- Failures: none, jaw_stuck_open
- Max steps: 220
- Recovery override window: 32 steps
- Trigger mode: coarse
- Recovery policy: phase_replan
- Controllers: clean, perturbed, monitor_corrected

## Episode Summary

| Failure | Controller | Episodes | Success | Final Distance | Distance Reduction | Risk Event | Monitor Triggers | Replans | Override Rate | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| none | clean | 1 | 1.000 | 0.021 | 0.204 | 0.727 | 0.000 | 0.000 | 0.000 | 44.000 |
| none | monitor_corrected | 1 | 1.000 | 0.021 | 0.204 | 0.727 | 1.000 | 0.000 | 0.727 | 44.000 |
| jaw_stuck_open | clean | 1 | 1.000 | 0.021 | 0.204 | 0.727 | 0.000 | 0.000 | 0.000 | 44.000 |
| jaw_stuck_open | perturbed | 1 | 0.000 | 0.225 | 0.000 | 0.982 | 0.000 | 0.000 | 0.000 | 220.000 |
| jaw_stuck_open | monitor_corrected | 1 | 1.000 | 0.021 | 0.204 | 0.862 | 3.000 | 1.000 | 0.920 | 87.000 |

## Interpretation

- If monitor_corrected improves success over perturbed, the risk trigger is doing useful control work.
- If monitor_corrected only lowers final distance but not success, the recovery action is partially helpful but the trigger/window needs tuning.
- If clean succeeds and perturbed fails, NeedlePick is a valid failure-aware benchmark.
