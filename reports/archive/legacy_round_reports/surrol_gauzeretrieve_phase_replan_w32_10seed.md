# SurRoL GauzeRetrieve Monitor Recovery

## Takeaway

This experiment tests whether a simple runtime monitor can supervise GauzeRetrieve under action, perception-state, or near-target drift corruptions. The monitor triggers on distance regression, moving farther than the initial state, action anomaly, clipping, or sustained stalls, then temporarily overrides the corrupted action with the clean scripted oracle.

## Setup

- Task: GauzeRetrieve
- Failures: none, action_noise, action_dropout, execution_slip
- Max steps: 200
- Recovery override window: 32 steps
- Trigger mode: goalaware
- Recovery policy: phase_replan
- Controllers: clean, perturbed, monitor_corrected

## Episode Summary

| Failure | Controller | Episodes | Success | Final Distance | Distance Reduction | Risk Event | Monitor Triggers | Replans | Override Rate | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| none | clean | 10 | 1.000 | 0.013 | 0.261 | 0.000 | 0.000 | 0.000 | 0.000 | 34.600 |
| none | monitor_corrected | 10 | 1.000 | 0.013 | 0.261 | 0.000 | 0.000 | 0.000 | 0.000 | 34.600 |
| action_noise | clean | 10 | 1.000 | 0.013 | 0.261 | 0.000 | 0.000 | 0.000 | 0.000 | 34.600 |
| action_noise | perturbed | 10 | 0.000 | 0.279 | -0.005 | 0.871 | 0.000 | 0.000 | 0.000 | 200.000 |
| action_noise | monitor_corrected | 10 | 1.000 | 0.016 | 0.258 | 0.052 | 1.800 | 0.000 | 0.945 | 34.700 |
| action_dropout | clean | 10 | 1.000 | 0.013 | 0.261 | 0.000 | 0.000 | 0.000 | 0.000 | 34.600 |
| action_dropout | perturbed | 10 | 0.000 | 0.270 | 0.004 | 0.310 | 0.000 | 0.000 | 0.000 | 200.000 |
| action_dropout | monitor_corrected | 10 | 1.000 | 0.013 | 0.261 | 0.028 | 1.000 | 0.000 | 0.844 | 35.500 |
| execution_slip | clean | 10 | 1.000 | 0.013 | 0.261 | 0.000 | 0.000 | 0.000 | 0.000 | 34.600 |
| execution_slip | perturbed | 10 | 0.000 | 0.275 | -0.001 | 0.250 | 0.000 | 0.000 | 0.000 | 200.000 |
| execution_slip | monitor_corrected | 10 | 1.000 | 0.013 | 0.262 | 0.028 | 1.400 | 0.200 | 0.900 | 43.900 |

## Interpretation

- If monitor_corrected improves success over perturbed, the risk trigger is doing useful control work.
- If monitor_corrected only lowers final distance but not success, the recovery action is partially helpful but the case may need review or re-estimation rather than blind retry.
- If clean succeeds and perturbed fails, GauzeRetrieve is a valid failure-aware benchmark.
