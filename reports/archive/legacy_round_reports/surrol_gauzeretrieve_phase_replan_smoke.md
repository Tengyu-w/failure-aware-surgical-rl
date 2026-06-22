# SurRoL GauzeRetrieve Monitor Recovery

## Takeaway

This experiment tests whether a simple runtime monitor can recover GauzeRetrieve from action corruption. The monitor triggers on distance regression, moving farther than the initial state, action anomaly, clipping, or sustained stalls, then temporarily overrides the corrupted action with the clean scripted oracle.

## Setup

- Task: GauzeRetrieve
- Failures: none, action_noise, action_dropout, execution_slip
- Max steps: 160
- Recovery override window: 32 steps
- Trigger mode: coarse
- Recovery policy: phase_replan
- Controllers: clean, perturbed, monitor_corrected

## Episode Summary

| Failure | Controller | Episodes | Success | Final Distance | Distance Reduction | Risk Event | Monitor Triggers | Replans | Override Rate | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| none | clean | 1 | 1.000 | 0.012 | 0.228 | 0.457 | 0.000 | 0.000 | 0.000 | 35.000 |
| none | monitor_corrected | 1 | 1.000 | 0.012 | 0.228 | 0.457 | 1.000 | 0.000 | 0.829 | 35.000 |
| action_noise | clean | 1 | 1.000 | 0.012 | 0.228 | 0.457 | 0.000 | 0.000 | 0.000 | 35.000 |
| action_noise | perturbed | 1 | 0.000 | 0.284 | -0.043 | 1.000 | 0.000 | 0.000 | 0.000 | 160.000 |
| action_noise | monitor_corrected | 1 | 1.000 | 0.012 | 0.229 | 0.500 | 2.000 | 0.000 | 0.941 | 34.000 |
| action_dropout | clean | 1 | 1.000 | 0.012 | 0.228 | 0.457 | 0.000 | 0.000 | 0.000 | 35.000 |
| action_dropout | perturbed | 1 | 0.000 | 0.241 | 0.000 | 0.969 | 0.000 | 0.000 | 0.000 | 160.000 |
| action_dropout | monitor_corrected | 1 | 1.000 | 0.012 | 0.228 | 0.500 | 1.000 | 0.000 | 0.889 | 36.000 |
| execution_slip | clean | 1 | 1.000 | 0.012 | 0.228 | 0.457 | 0.000 | 0.000 | 0.000 | 35.000 |
| execution_slip | perturbed | 1 | 0.000 | 0.241 | 0.000 | 0.894 | 0.000 | 0.000 | 0.000 | 160.000 |
| execution_slip | monitor_corrected | 1 | 1.000 | 0.009 | 0.231 | 0.500 | 1.000 | 0.000 | 0.889 | 36.000 |

## Interpretation

- If monitor_corrected improves success over perturbed, the risk trigger is doing useful control work.
- If monitor_corrected only lowers final distance but not success, the recovery action is partially helpful but the trigger/window needs tuning.
- If clean succeeds and perturbed fails, GauzeRetrieve is a valid failure-aware benchmark.
