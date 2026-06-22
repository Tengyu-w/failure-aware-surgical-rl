# SurRoL NeedlePick Monitor Recovery

## Takeaway

This experiment tests whether a simple runtime monitor can supervise NeedlePick under action, perception-state, or near-target drift corruptions. The monitor triggers on distance regression, moving farther than the initial state, action anomaly, clipping, or sustained stalls, then temporarily overrides the corrupted action with the clean scripted oracle.

## Setup

- Task: NeedlePick
- Failures: none, action_noise, action_dropout, execution_slip
- Max steps: 200
- Recovery override window: 32 steps
- Trigger mode: goalaware
- Recovery policy: phase_replan
- Controllers: clean, perturbed, monitor_corrected

## Episode Summary

| Failure | Controller | Episodes | Success | Final Distance | Distance Reduction | Risk Event | Monitor Triggers | Replans | Override Rate | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| none | clean | 10 | 1.000 | 0.020 | 0.187 | 0.000 | 0.000 | 0.000 | 0.000 | 40.800 |
| none | monitor_corrected | 10 | 1.000 | 0.020 | 0.187 | 0.000 | 0.000 | 0.000 | 0.000 | 40.800 |
| action_noise | clean | 10 | 1.000 | 0.020 | 0.187 | 0.000 | 0.000 | 0.000 | 0.000 | 40.800 |
| action_noise | perturbed | 10 | 0.000 | 0.208 | -0.001 | 0.884 | 0.000 | 0.000 | 0.000 | 200.000 |
| action_noise | monitor_corrected | 10 | 0.900 | 0.043 | 0.165 | 0.043 | 16.800 | 14.700 | 0.954 | 62.400 |
| action_dropout | clean | 10 | 1.000 | 0.020 | 0.187 | 0.000 | 0.000 | 0.000 | 0.000 | 40.800 |
| action_dropout | perturbed | 10 | 0.000 | 0.195 | 0.012 | 0.310 | 0.000 | 0.000 | 0.000 | 200.000 |
| action_dropout | monitor_corrected | 10 | 1.000 | 0.021 | 0.187 | 0.024 | 3.000 | 1.000 | 0.882 | 84.400 |
| execution_slip | clean | 10 | 1.000 | 0.020 | 0.187 | 0.000 | 0.000 | 0.000 | 0.000 | 40.800 |
| execution_slip | perturbed | 10 | 0.000 | 0.206 | 0.001 | 0.252 | 0.000 | 0.000 | 0.000 | 200.000 |
| execution_slip | monitor_corrected | 10 | 1.000 | 0.021 | 0.186 | 0.025 | 3.500 | 1.200 | 0.935 | 94.100 |

## Interpretation

- If monitor_corrected improves success over perturbed, the risk trigger is doing useful control work.
- If monitor_corrected only lowers final distance but not success, the recovery action is partially helpful but the case may need review or re-estimation rather than blind retry.
- If clean succeeds and perturbed fails, NeedlePick is a valid failure-aware benchmark.
