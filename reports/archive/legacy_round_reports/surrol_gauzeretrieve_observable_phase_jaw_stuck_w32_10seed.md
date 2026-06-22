# SurRoL GauzeRetrieve Monitor Recovery

## Takeaway

This experiment tests whether a simple runtime monitor can recover GauzeRetrieve from action corruption. The monitor triggers on distance regression, moving farther than the initial state, action anomaly, clipping, or sustained stalls, then temporarily overrides the corrupted action with the clean scripted oracle.

## Setup

- Task: GauzeRetrieve
- Failures: none, jaw_stuck_open
- Max steps: 220
- Recovery override window: 32 steps
- Trigger mode: coarse
- Recovery policy: observable_phase_replan
- Controllers: clean, perturbed, monitor_corrected

## Episode Summary

| Failure | Controller | Episodes | Success | Final Distance | Distance Reduction | Risk Event | Monitor Triggers | Replans | Override Rate | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| none | clean | 10 | 1.000 | 0.013 | 0.261 | 0.468 | 0.000 | 0.000 | 0.000 | 34.600 |
| none | monitor_corrected | 10 | 1.000 | 0.013 | 0.261 | 0.471 | 1.000 | 0.000 | 0.827 | 34.600 |
| jaw_stuck_open | clean | 10 | 1.000 | 0.013 | 0.261 | 0.468 | 0.000 | 0.000 | 0.000 | 34.600 |
| jaw_stuck_open | perturbed | 10 | 0.000 | 0.274 | 0.000 | 0.977 | 0.000 | 0.000 | 0.000 | 220.000 |
| jaw_stuck_open | monitor_corrected | 10 | 1.000 | 0.014 | 0.260 | 0.818 | 3.000 | 2.000 | 0.941 | 101.800 |

## Interpretation

- If monitor_corrected improves success over perturbed, the risk trigger is doing useful control work.
- If monitor_corrected only lowers final distance but not success, the recovery action is partially helpful but the trigger/window needs tuning.
- If clean succeeds and perturbed fails, GauzeRetrieve is a valid failure-aware benchmark.
