# SurRoL Oracle Robustness Pilot

## Takeaway

This is the first formal SurRoL simulation experiment for this project: we run multi-seed scripted-oracle rollouts across surgical task entry points, then inject action noise/dropout to measure success, distance convergence, and risk events. The result is a baseline for later risk-monitor and recovery-policy experiments, not a trained-policy claim.

## Setup

- Tasks: ECMReach
- Conditions: none
- Seeds: 1
- Episodes per seed-condition-task: 1
- Max steps per episode: 3
- Policy: SurRoL scripted oracle, with optional action perturbation.
- Risk proxy: distance regression, moving farther than initial state, or action clipping.

## Summary Table

| Task | Condition | Episodes | Success | Success Std | Final Dist | Distance Reduction | Risk Event | Regress | Stalled | Action Deviation |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ECMReach | none | 1 | 0.000 | 0.000 | 0.060 | 0.006 | 0.000 | 0.000 | 0.000 | 0.000 |

## What This Shows

- The run estimates basic task reachability under SurRoL scripted oracle control.
- The perturbation conditions show whether action corruption creates measurable risk events.
- If a task is weak even under `none`, it is likely a task/environment difficulty rather than a monitor issue.
- If perturbations raise risk but still allow goal progress, that task is a good recovery/monitor benchmark.

## What This Does Not Prove

- This is not a learned-policy result.
- The current risk proxy is heuristic and not yet a calibrated uncertainty model.
- The seed count is still small, so this should be treated as a pilot.

## Next Step

Connect the same CSV interface to the existing failure-aware monitor and compare oracle-only, perturbed-oracle, and monitor-corrected rollouts before starting policy training.
