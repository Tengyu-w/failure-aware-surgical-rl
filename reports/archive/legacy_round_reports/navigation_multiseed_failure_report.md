# Navigation Multi-Seed Failure-Recovery Report

## Takeaway

This report evaluates the navigation failure-recovery suite across multiple trained PPO seeds, rather than relying on a single policy checkpoint. It strengthens the evidence for the runtime monitor/recovery layer while still remaining an abstract proxy experiment.

## Aggregate Across Model Seeds

| Failure Mode | Controller | Model Seeds | Episodes/Seed | Success Mean | Success Std | Recovery Trigger | False Trigger | Class Correct | Detection Delay |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| none | policy_only | 3 | 10 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 |
| none | monitor_recovery | 3 | 10 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 |
| state_target_bias | policy_only | 3 | 10 | 0.033 | 0.047 | 0.000 | 0.000 | 1.000 | 0.000 |
| state_target_bias | monitor_recovery | 3 | 10 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 |
| state_dropout | policy_only | 3 | 10 | 0.033 | 0.047 | 0.000 | 0.000 | 1.000 | 0.000 |
| state_dropout | monitor_recovery | 3 | 10 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 |
| execution_slip | policy_only | 3 | 10 | 0.533 | 0.205 | 0.000 | 0.000 | 1.000 | 4.000 |
| execution_slip | monitor_recovery | 3 | 10 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 4.000 |

## Reading Notes

- Model seeds refer to independently trained navigation PPO checkpoints.
- Episodes/Seed is intentionally modest for a fast multi-seed reliability pass.
- Manipulation PPO multi-seed training is not included here yet; current manipulation failure results are controller/proxy evaluations.

## Next Breadth Step

After this multi-seed navigation pass, the next useful breadth expansion is to add more surgical proxy task families, then rerun the same failure taxonomy and risk reports over those presets.
