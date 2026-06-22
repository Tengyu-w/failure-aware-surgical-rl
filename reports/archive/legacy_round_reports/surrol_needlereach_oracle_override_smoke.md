# SurRoL NeedleReach Monitor Recovery

## Takeaway

This experiment tests whether a simple runtime monitor can recover NeedleReach from action corruption. The monitor triggers on distance regression, moving farther than the initial state, action anomaly, clipping, or sustained stalls, then temporarily overrides the corrupted action with the clean scripted oracle.

## Setup

- Task: NeedleReach
- Failures: none, action_noise, action_dropout, execution_slip
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
| action_noise | clean | 1 | 1.000 | 0.016 | 0.462 | 0.000 | 0.000 | 0.000 | 0.000 | 23.000 |
| action_noise | perturbed | 1 | 1.000 | 0.023 | 0.456 | 0.923 | 0.000 | 0.000 | 0.000 | 26.000 |
| action_noise | monitor_corrected | 1 | 1.000 | 0.003 | 0.475 | 0.087 | 2.000 | 0.000 | 0.913 | 23.000 |
| action_dropout | clean | 1 | 1.000 | 0.016 | 0.462 | 0.000 | 0.000 | 0.000 | 0.000 | 23.000 |
| action_dropout | perturbed | 1 | 1.000 | 0.016 | 0.462 | 0.233 | 0.000 | 0.000 | 0.000 | 30.000 |
| action_dropout | monitor_corrected | 1 | 1.000 | 0.016 | 0.462 | 0.042 | 1.000 | 0.000 | 0.667 | 24.000 |
| execution_slip | clean | 1 | 1.000 | 0.016 | 0.462 | 0.000 | 0.000 | 0.000 | 0.000 | 23.000 |
| execution_slip | perturbed | 1 | 1.000 | 0.013 | 0.465 | 0.250 | 0.000 | 0.000 | 0.000 | 36.000 |
| execution_slip | monitor_corrected | 1 | 1.000 | 0.017 | 0.462 | 0.080 | 2.000 | 0.000 | 0.800 | 25.000 |

## Interpretation

- If monitor_corrected improves success over perturbed, the risk trigger is doing useful control work.
- If monitor_corrected only lowers final distance but not success, the recovery action is partially helpful but the trigger/window needs tuning.
- If clean succeeds and perturbed fails, NeedleReach is a valid failure-aware benchmark.
