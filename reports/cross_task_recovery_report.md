# Cross-Task Failure-Recovery Report

## One-Paragraph Takeaway

Across the current abstract 3D navigation and multi-phase manipulation proxies, the runtime recovery layer preserves nominal success while recovering from injected state-estimation, execution, and contact-loss failures. This supports a prototype-level claim about failure-aware recovery across task families, not just a single reach/avoid action.

## Cross-Task Summary

| Group | Mean Success | Mean Recovery Trigger | Mean False Trigger | Mean Class Correct |
|---|---:|---:|---:|---:|
| Baseline controllers | 0.241 | 0.000 | 0.000 | 1.000 |
| Runtime monitor/recovery | 1.000 | 0.778 | 0.000 | 1.000 |
| Runtime monitor/recovery on abnormal cases | 1.000 | 1.000 | 0.000 | 1.000 |

## Detailed Table

| Task | Failure Mode | Controller | Success | Success Delta | Detected | Recovery Triggered | Detection Delay | False Trigger | Class Correct |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| navigation | none | policy_only | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 |
| navigation | none | monitor_recovery | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 |
| navigation | state_target_bias | policy_only | 0.030 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 |
| navigation | state_target_bias | monitor_recovery | 1.000 | 0.970 | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 |
| navigation | state_dropout | policy_only | 0.030 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 |
| navigation | state_dropout | monitor_recovery | 1.000 | 0.970 | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 |
| navigation | execution_slip | policy_only | 0.100 | 0.000 | 1.000 | 0.000 | 4.000 | 0.000 | 1.000 |
| navigation | execution_slip | monitor_recovery | 1.000 | 0.900 | 1.000 | 1.000 | 4.000 | 0.000 | 1.000 |
| manipulation | none | base | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 |
| manipulation | none | monitor | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 |
| manipulation | object_state_bias | base | 0.010 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 |
| manipulation | object_state_bias | monitor | 1.000 | 0.990 | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 |
| manipulation | object_dropout | base | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 |
| manipulation | object_dropout | monitor | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 |
| manipulation | execution_slip | base | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 |
| manipulation | execution_slip | monitor | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 |
| manipulation | contact_loss | base | 0.000 | 0.000 | 1.000 | 0.000 | 6.000 | 0.000 | 1.000 |
| manipulation | contact_loss | monitor | 1.000 | 1.000 | 1.000 | 1.000 | 6.000 | 0.000 | 1.000 |

## What Is Shown

- Navigation covers target/state bias, state dropout, and execution slip.
- Manipulation covers object-state bias, object dropout, execution slip, and contact loss.
- Nominal `none` cases estimate unnecessary intervention behavior.
- The current manipulation monitor reports explicit failure-type diagnosis.
- For older navigation CSVs without explicit classification fields, class correctness is inferred from the injected failure mode and detection flag.
- `N/A` means the metric was not logged and cannot be inferred for that task family yet.

## What Remains Unproven

- These are abstract proxy environments, not high-fidelity SurRoL or real robot experiments.
- Failure classification is currently rule-based instrumentation, not a learned classifier.
- The result is episode-level reliability evidence, not proof of sim-to-real robustness.

## Recommended Next Experiment

Move the same failure taxonomy into a SurRoL-style needle or gauze task, while keeping the same metrics: success, recovery success, detection delay, false trigger rate, and failure-type classification accuracy.
