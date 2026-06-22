# SurRoL NeedlePick Monitor Recovery

## Takeaway

This experiment tests whether a simple runtime monitor can recover NeedlePick from action corruption. The monitor triggers on distance regression, moving farther than the initial state, action anomaly, clipping, or sustained stalls, then temporarily overrides the corrupted action with the clean scripted oracle.

## Setup

- Task: NeedlePick
- Failures: none, jaw_stuck_open
- Max steps: 220
- Recovery override window: 32 steps
- Trigger mode: coarse
- Recovery policy: observable_phase_replan
- Controllers: clean, perturbed, monitor_corrected

## Episode Summary

| Failure | Controller | Episodes | Success | Final Distance | Distance Reduction | Risk Event | Monitor Triggers | Replans | Override Rate | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| none | clean | 10 | 1.000 | 0.020 | 0.187 | 0.702 | 0.000 | 0.000 | 0.000 | 40.800 |
| none | monitor_corrected | 10 | 1.000 | 0.020 | 0.187 | 0.702 | 1.100 | 0.000 | 0.804 | 40.800 |
| jaw_stuck_open | clean | 10 | 1.000 | 0.020 | 0.187 | 0.702 | 0.000 | 0.000 | 0.000 | 40.800 |
| jaw_stuck_open | perturbed | 10 | 0.000 | 0.207 | 0.000 | 0.982 | 0.000 | 0.000 | 0.000 | 220.000 |
| jaw_stuck_open | monitor_corrected | 10 | 1.000 | 0.020 | 0.187 | 0.882 | 3.000 | 1.700 | 0.935 | 102.600 |

## Interpretation

- If monitor_corrected improves success over perturbed, the risk trigger is doing useful control work.
- If monitor_corrected only lowers final distance but not success, the recovery action is partially helpful but the trigger/window needs tuning.
- If clean succeeds and perturbed fails, NeedlePick is a valid failure-aware benchmark.
