# SurRoL Third Complex Task Status

## Takeaway

PickAndPlace was tested as the preferred complex third task, but it is not ready for formal failure/recovery experiments in this local setup. The non-haptic class can be imported only after mocking the unused haptic SWIG module, and clean oracle success is unstable.

## PickAndPlace Clean Oracle Smoke

| Seed | Success | Steps | Final Distance |
|---:|---:|---:|---:|
| 45000 | 0.000 | 260 | 0.315 |
| 45001 | 0.000 | 260 | 0.322 |
| 45002 | 1.000 | 52 | 0.017 |

Clean success: 0.333 (1/3)

## Decision

- Do not use PickAndPlace yet for formal risk/recovery claims.
- Treat it as an unstable candidate until clean oracle reaches a reliable baseline.
- NeedleRegrasp remains blocked by success/goal semantics from the earlier smoke.
- The current formal task set should remain NeedlePick + GauzeRetrieve, with NeedleReach only as a simple sanity task.