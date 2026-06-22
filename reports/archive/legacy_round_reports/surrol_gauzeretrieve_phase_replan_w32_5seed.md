# SurRoL GauzeRetrieve Monitor Recovery

## Takeaway

This experiment tests whether a simple runtime monitor can recover GauzeRetrieve from action corruption. The monitor triggers on distance regression, moving farther than the initial state, action anomaly, clipping, or sustained stalls, then temporarily overrides the corrupted action with the clean scripted oracle.

## Setup

- Task: GauzeRetrieve
- Failures: none, action_noise, action_dropout, execution_slip
- Max steps: 200
- Recovery override window: 32 steps
- Trigger mode: coarse
- Recovery policy: phase_replan
- Controllers: clean, perturbed, monitor_corrected

## Episode Summary

| Failure | Controller | Episodes | Success | Final Distance | Distance Reduction | Risk Event | Monitor Triggers | Replans | Override Rate | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| none | clean | 5 | 1.000 | 0.013 | 0.252 | 0.456 | 0.000 | 0.000 | 0.000 | 34.600 |
| none | monitor_corrected | 5 | 1.000 | 0.013 | 0.252 | 0.456 | 1.000 | 0.000 | 0.826 | 34.600 |
| action_noise | clean | 5 | 1.000 | 0.013 | 0.252 | 0.456 | 0.000 | 0.000 | 0.000 | 34.600 |
| action_noise | perturbed | 5 | 0.000 | 0.271 | -0.006 | 0.983 | 0.000 | 0.000 | 0.000 | 200.000 |
| action_noise | monitor_corrected | 5 | 1.000 | 0.017 | 0.248 | 0.508 | 1.800 | 0.000 | 0.948 | 34.600 |
| action_dropout | clean | 5 | 1.000 | 0.013 | 0.252 | 0.456 | 0.000 | 0.000 | 0.000 | 34.600 |
| action_dropout | perturbed | 5 | 0.000 | 0.257 | 0.008 | 0.952 | 0.000 | 0.000 | 0.000 | 200.000 |
| action_dropout | monitor_corrected | 5 | 1.000 | 0.012 | 0.252 | 0.500 | 1.000 | 0.000 | 0.882 | 35.600 |
| execution_slip | clean | 5 | 1.000 | 0.013 | 0.252 | 0.456 | 0.000 | 0.000 | 0.000 | 34.600 |
| execution_slip | perturbed | 5 | 0.000 | 0.265 | -0.000 | 0.952 | 0.000 | 0.000 | 0.000 | 200.000 |
| execution_slip | monitor_corrected | 5 | 1.000 | 0.013 | 0.252 | 0.508 | 1.000 | 0.000 | 0.894 | 35.800 |

## Interpretation

- If monitor_corrected improves success over perturbed, the risk trigger is doing useful control work.
- If monitor_corrected only lowers final distance but not success, the recovery action is partially helpful but the trigger/window needs tuning.
- If clean succeeds and perturbed fails, GauzeRetrieve is a valid failure-aware benchmark.
