# SurRoL Oracle Robustness Pilot

## Takeaway

This is the first formal SurRoL simulation experiment for this project: we run multi-seed scripted-oracle rollouts across surgical task entry points, then inject action noise/dropout to measure success, distance convergence, and risk events. The result is a baseline for later risk-monitor and recovery-policy experiments, not a trained-policy claim.

## Setup

- Tasks: ECMReach, NeedlePick
- Conditions: none, action_noise, action_dropout, execution_slip
- Seeds: 3
- Episodes per seed-condition-task: 1
- Max steps per episode: 200
- Policy: SurRoL scripted oracle, with optional action perturbation.
- Risk proxy: distance regression, moving farther than initial state, or action clipping.

## Summary Table

| Task | Condition | Episodes | Success | Success Std | Final Dist | Distance Reduction | Risk Event | Regress | Stalled | Action Deviation |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ECMReach | none | 3 | 1.000 | 0.000 | 0.004 | 0.078 | 0.000 | 0.000 | 0.000 | 0.000 |
| ECMReach | action_noise | 3 | 1.000 | 0.000 | 0.004 | 0.078 | 0.269 | 0.269 | 0.021 | 0.385 |
| ECMReach | action_dropout | 3 | 1.000 | 0.000 | 0.004 | 0.078 | 0.000 | 0.000 | 0.314 | 0.069 |
| ECMReach | execution_slip | 3 | 1.000 | 0.000 | 0.004 | 0.077 | 0.176 | 0.176 | 0.012 | 0.078 |
| NeedlePick | none | 3 | 1.000 | 0.000 | 0.018 | 0.161 | 0.026 | 0.026 | 0.775 | 0.000 |
| NeedlePick | action_noise | 3 | 0.000 | 0.000 | 0.199 | -0.020 | 0.237 | 0.017 | 0.975 | 0.537 |
| NeedlePick | action_dropout | 3 | 0.000 | 0.000 | 0.165 | 0.014 | 0.260 | 0.008 | 0.975 | 0.165 |
| NeedlePick | execution_slip | 3 | 0.000 | 0.000 | 0.180 | -0.000 | 0.248 | 0.073 | 0.863 | 0.183 |

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
