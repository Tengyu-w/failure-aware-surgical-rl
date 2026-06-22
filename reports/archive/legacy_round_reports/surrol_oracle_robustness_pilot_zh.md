# SurRoL Oracle Robustness Pilot

## Takeaway

This is the first formal SurRoL simulation experiment for this project: we run multi-seed scripted-oracle rollouts across surgical task entry points, then inject action noise/dropout to measure success, distance convergence, and risk events. The result is a baseline for later risk-monitor and recovery-policy experiments, not a trained-policy claim.

## Setup

- Tasks: ECMReach, NeedlePick, BiPegTransfer
- Conditions: none, action_noise, action_dropout
- Seeds: 3
- Episodes per seed-condition-task: 1
- Max steps per episode: 25
- Policy: SurRoL scripted oracle, with optional action perturbation.
- Risk proxy: distance regression, moving farther than initial state, or action clipping.

## Summary Table

| Task | Condition | Episodes | Success | Success Std | Final Dist | Distance Reduction | Risk Event | Regress | Stalled | Action Deviation |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ECMReach | none | 3 | 0.000 | 0.000 | 0.028 | 0.054 | 0.000 | 0.000 | 0.000 | 0.000 |
| ECMReach | action_noise | 3 | 0.000 | 0.000 | 0.038 | 0.044 | 0.227 | 0.227 | 0.013 | 0.384 |
| ECMReach | action_dropout | 3 | 0.000 | 0.000 | 0.042 | 0.040 | 0.000 | 0.000 | 0.267 | 0.063 |
| NeedlePick | none | 3 | 0.000 | 0.000 | 0.180 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 |
| NeedlePick | action_noise | 3 | 0.000 | 0.000 | 0.180 | 0.000 | 0.027 | 0.000 | 1.000 | 0.515 |
| NeedlePick | action_dropout | 3 | 0.000 | 0.000 | 0.180 | 0.000 | 0.000 | 0.000 | 1.000 | 0.178 |
| BiPegTransfer | none | 3 | 0.000 | 0.000 | 0.232 | -0.027 | 0.347 | 0.280 | 0.653 | 0.000 |
| BiPegTransfer | action_noise | 3 | 0.000 | 0.000 | 0.205 | -0.000 | 0.133 | 0.000 | 1.000 | 0.752 |
| BiPegTransfer | action_dropout | 3 | 0.000 | 0.000 | 0.209 | -0.005 | 0.067 | 0.067 | 0.920 | 0.305 |

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
