# Human-Review Trigger Report

## Takeaway

Treating the runtime monitor as a human-review trigger, the current proxy suites show high recall on injected failures and zero observed false triggers under nominal episodes. This is still a prototype-level result because failures are synthetic and the trigger logic is rule-based.

## Trigger Summary

| Group | Episodes | Precision | Recall | False Trigger Rate | Mean Detection Delay | TP | FP | FN | TN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Overall | 900 | 1.000 | 1.000 | 0.000 | 1.429 | 700 | 0 | 0 | 200 |
| Navigation | 400 | 1.000 | 1.000 | 0.000 | 1.333 | 300 | 0 | 0 | 100 |
| Manipulation | 500 | 1.000 | 1.000 | 0.000 | 1.500 | 400 | 0 | 0 | 100 |

## Per-Failure Trigger Table

| Task | Failure Mode | Episodes | Trigger Rate | Recall | False Trigger Rate | Mean Detection Delay | TP | FP | FN | TN |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| navigation | none | 100 | 0.000 | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 100 |
| navigation | state_target_bias | 100 | 1.000 | 1.000 | 0.000 | 0.000 | 100 | 0 | 0 | 0 |
| navigation | state_dropout | 100 | 1.000 | 1.000 | 0.000 | 0.000 | 100 | 0 | 0 | 0 |
| navigation | execution_slip | 100 | 1.000 | 1.000 | 0.000 | 4.000 | 100 | 0 | 0 | 0 |
| manipulation | none | 100 | 0.000 | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 100 |
| manipulation | object_state_bias | 100 | 1.000 | 1.000 | 0.000 | 0.000 | 100 | 0 | 0 | 0 |
| manipulation | object_dropout | 100 | 1.000 | 1.000 | 0.000 | 0.000 | 100 | 0 | 0 | 0 |
| manipulation | execution_slip | 100 | 1.000 | 1.000 | 0.000 | 0.000 | 100 | 0 | 0 | 0 |
| manipulation | contact_loss | 100 | 1.000 | 1.000 | 0.000 | 6.000 | 100 | 0 | 0 | 0 |

## Reading Notes

- TP means an injected failure was detected and would trigger review/recovery.
- FP means a nominal episode triggered review unnecessarily.
- FN means an injected failure was missed.
- Detection delay is averaged only over detected abnormal episodes.

## Limitations

- This report uses synthetic failures in abstract proxy environments.
- Current trigger logic is deterministic instrumentation, not a learned uncertainty model.
- Real human-review usefulness would require higher-fidelity tasks and human-in-the-loop thresholds.
