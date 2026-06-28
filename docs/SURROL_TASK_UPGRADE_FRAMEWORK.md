# SurRoL Task Upgrade Framework

This document defines how the project moves beyond the CircleRL proxy into
task-specific surgical simulation reliability experiments. CircleRL remains the
minimal controller proof-of-concept. The task framework below is the surgical
simulation layer: each task has a failure mechanism, interpretable evidence,
route decision, recovery action, and explicit limitation.

## Task-Level Reliability Matrix

| Task | Surgical-reliability question | Injected or audited failure | Explanation signals | Route | Recovery or response | Current evidence |
| --- | --- | --- | --- | --- | --- | --- |
| NeedleReach | Can a reaching policy remain reliable when final localization or approach becomes unstable? | action freeze, near-target drift, visual localization drift | final distance, progress slope, target proximity, recovery trigger timing | `auto_recovery` when drift is recoverable; `human_review` when localization is unreliable | short-window oracle/monitor correction or state re-estimation | rendered rollout media and third-task recovery smoke |
| NeedlePick | Can needle pickup recover from execution faults without blindly retrying unsafe motions? | action noise, action dropout, execution slip, perception bias, jaw-stuck-open, unsafe-zone near target | distance curve, grasp phase, jaw command/progress mismatch, visual-state error, unsafe-zone proximity | `auto_recovery`, `human_review`, or `abort_candidate` depending on mechanism | phase-aware recovery, review/re-estimation, observable jaw retry, abort-candidate routing | 10-seed action-fault recovery, visual-state re-estimation, observable jaw-stuck recovery, severity sweep |
| GauzeRetrieve | Can soft-object retrieval distinguish recoverable action drift from perception/depth uncertainty? | action noise, action dropout, execution slip, depth-scale error, jaw-stuck-open | object progress proxy, final distance, depth-error severity, observable jaw outcome, stagnation | `auto_recovery` for action drift; `human_review` for depth/state uncertainty; observable retry for grasp uncertainty | phase-aware recovery, review/re-estimation, observable grasp retry | 10-seed action-fault recovery, depth-error re-estimation, jaw-stuck recovery, severity sweep |
| PickAndPlace | Can object manipulation failures be routed by state and grasp reliability rather than treated as navigation errors? | object-state bias, contact loss, object dropout, execution slip | object-target distance, contact/grasp proxy, object state consistency, low progress after command | `auto_recovery` for reversible execution slip; `human_review` for object-state or contact uncertainty | monitor recovery and planned learned route extension | custom manipulation recovery evidence; SurRoL PPO wrapper smoke/readiness evidence |
| Unsafe-zone near target | Can recovery itself be stopped when the correction path becomes unsafe? | near-target drift plus forbidden/danger-zone proxy | danger-zone distance, unsafe violation, remaining budget, recovery trajectory risk | `abort_candidate` | stop recovery or flag unsafe continuation rather than forcing success | unsafe-zone abort proxy and reliability-memory evidence |

## How The Framework Starts

The upgrade starts by mapping every task to the same reliability interface:

```text
task rollout
  -> injected or observed failure mechanism
  -> interpretable evidence signals
  -> route label
  -> recovery / review / abort response
  -> table, figure, and media evidence
```

This means the project is no longer framed as a single navigation-avoidance
demo. It becomes a cross-task reliability-routing study:

- NeedleReach tests final approach and localization drift.
- NeedlePick tests needle grasp, execution drift, perception error, jaw-stuck
  uncertainty, and unsafe recovery.
- GauzeRetrieve tests soft-object retrieval, depth error, and grasp/contact
  uncertainty.
- PickAndPlace tests object-state and contact reliability in manipulation.
- Unsafe-zone near target tests whether the supervisor can refuse unsafe
  recovery.

## Route Semantics

| Route | Meaning in these tasks |
| --- | --- |
| `auto_execute` | Continue normal policy execution when no major reliability signal is active. |
| `auto_recovery` | Apply a bounded recovery primitive for reversible execution faults such as action drift, dropout, slip, or near-target control error. |
| `human_review` | Pause, re-estimate state, or request review when visual/depth/object/grasp state is unreliable. |
| `abort_candidate` | Stop or flag continuation when automatic recovery may enter an unsafe zone or exhaust the safety budget. |

## Evidence Boundary

The current framework is still a simulation reliability prototype. It uses
rendered SurRoL/PyBullet rollouts, proxy visual/state corruptions, simulator
logs, and weak route labels. It should not be described as clinical validation,
surgeon-labeled learning, or real-robot deployment.

