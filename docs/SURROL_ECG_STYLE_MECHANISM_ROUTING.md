# SurRoL ECG-Style Mechanism Routing

This document adapts the reliable-ECG uncertainty project method to the SurRoL
surgical-RL setting. The transfer is methodological, not a transfer of ECG
results.

## Core Translation

The ECG project does not only ask whether the classifier is accurate. It first
identifies the dangerous error boundary, builds evidence families for different
error mechanisms, tests whether model-side interventions actually improve
downstream reliability, and then converts validated evidence into a
mechanism-separated router.

For SurRoL, the equivalent framing is:

```text
SurRoL task policy or teacher policy
  -> injected execution / perception / contact / unsafe-recovery failures
  -> rollout evidence layer
  -> mechanism category
  -> route: continue, recover, re-estimate/review, abort-candidate
  -> fixed-budget high-risk failure capture and residual-risk evaluation
```

This means the project should not claim that CircleRL PPO weights are transferred
to SurRoL, or that a new surgical manipulation policy is learned from labels.
SurRoL already provides the task environment and scripted or RL policy substrate.
Our contribution is the reliability layer around that substrate.

## What We Can Do Without The Teacher Model Data

If the teacher's trained RL model or original demonstrations are not available,
the reliability layer can still be evaluated by wrapping the released SurRoL
environment:

- use the available scripted oracle, RL task API, or any released policy as the
  base action source;
- inject controlled failures before or after `env.step(action)`;
- log observable evidence from actions, observations, rewards, distances,
  gripper commands, object progress, rendered frames, and safety proxies;
- assign weak mechanism labels from the injected failure family and observed
  rollout symptoms;
- train or audit risk/route heads from those logs without needing surgeon labels
  or the teacher's private training set.

This mirrors the ECG project: mechanism labels are derived from validated
evidence and error analysis, not from copying raw expert labels.

## ECG-To-SurRoL Mechanism Map

| ECG reliability idea | SurRoL analogue | Evidence signals | Route |
| --- | --- | --- | --- |
| VT/VF boundary-first gate | high-risk surgical boundary: grasp/contact ambiguity or near-target unsafe recovery | jaw command/progress mismatch, object motion after close command, danger-zone distance, stalled progress near target | `human_review`, observable retry, or `abort_candidate` |
| representation conflict | policy/action evidence conflicts with observed task progress | action norm, policy-vs-oracle gap when available, expected progress vs actual progress, kNN/reliability-memory route conflict | `auto_recovery` or `human_review` |
| atypical signal evidence | observation or state is outside normal rollout pattern | rendered-frame corruption, depth/state bias, object dropout, high memory distance, abnormal visual features | `human_review` / re-estimation |
| hidden confident error | action source looks confident but outcome is wrong | low action uncertainty but no progress, repeated close command without grasp progress, high success expectation but object drops | `human_review` or recovery retry |
| signal quality / OOD | poor visual or state input | occlusion, brightness, depth-scale error, missing object, high visual adapter residual | re-estimation or review |
| fixed-budget review routing | limited intervention budget in surgical autonomy | capture of high-risk failures at 10/20/30% intervention budget, residual automatic-path error | evaluate router, not only task success |
| residual mechanism reserve | keep capacity for non-dominant failure types | boundary failures should not consume all review/recovery slots | v5d-style two-stage router |

## Recommended SurRoL Failure Families

1. `execution_drift`
   - Examples: action noise, dropout, freeze, slip.
   - Route: `auto_recovery`.
   - Evidence: distance regression, progress slope, action anomaly, stalled steps.

2. `grasp_contact_uncertainty`
   - Examples: jaw-stuck-open, weak grasp, object drop after lift.
   - Route: observable retry or `human_review`.
   - Evidence: close-command count, jaw command/progress mismatch, object height or
     object-target distance, no improvement after grasp phase.

3. `visual_state_error`
   - Examples: perception bias, depth-scale error, object-state bias, object
     dropout.
   - Route: `human_review` / re-estimation.
   - Evidence: state inconsistency, visual corruption score, depth residual,
     re-estimation delta, memory distance.

4. `unsafe_recovery_risk`
   - Examples: near-target drift plus danger-zone proxy, recovery path crossing
     forbidden tissue region.
   - Route: `abort_candidate`.
   - Evidence: danger-zone distance, predicted recovery path risk, remaining
     safety budget, unsafe-warning events.

5. `nominal_execution`
   - Examples: no injected failure.
   - Route: `auto_execute`.
   - Evidence: no alarm, normal progress, no unsafe warning.

## v5d-Style Router For SurRoL

Use a two-stage router rather than one monolithic threshold:

```text
Stage 1: boundary / irreversible-risk gate
  - unsafe-zone recovery
  - grasp/contact ambiguity at a critical phase
  - visual-state unreliability where blind recovery is unsafe

Stage 2: residual mechanism router
  - reversible execution drift
  - representation/memory conflict
  - atypical observation
  - hidden confident outcome failure
```

The router should reserve part of the intervention budget for residual
mechanisms. Otherwise, one common high-scoring failure type can consume all
interventions and hide rarer but important failures.

## Evaluation Metrics

SurRoL should be evaluated like the ECG project, by error capture and residual
risk, not only by success:

| Metric | Meaning |
| --- | --- |
| high-risk failure capture @ budget | How many important failures are caught when only a limited number of episodes/steps can be intervened on. |
| residual automatic-path failure rate | How many dangerous failures remain in `auto_execute`. |
| route-specific success | Whether `auto_recovery`, review/re-estimation, and abort-candidate routes behave as intended. |
| false trigger rate on nominal episodes | Whether the monitor over-intervenes. |
| mechanism alignment | Whether the explanation signal actually matches the failure type it claims to explain. |
| seed and task stress test | Whether results survive across seeds and tasks, not one lucky episode. |

## Implementation Boundary

The preferred implementation is a project-side SurRoL wrapper, not direct
destructive edits to the teacher's source tree:

```text
base_action = policy(obs) or env.get_oracle_action(obs)
faulted_action = failure_wrapper.before_step(base_action, obs)
next_obs, reward, done, info = env.step(faulted_action)
evidence = evidence_extractor(obs, faulted_action, next_obs, info)
route = mechanism_router(evidence)
```

Only modify SurRoL source files when a failure cannot be represented by a
wrapper, such as true contact-constraint or object-drop dynamics that must be
inserted inside the task environment.

## Next Concrete Experiments

1. NeedlePick jaw-stuck-open video and 10-seed table using observable command /
   progress evidence.
2. NeedlePick object-drop-after-grasp wrapper, with regrasp or review routing.
3. GauzeRetrieve depth-scale or object-state bias, routed to re-estimation
   rather than blind recovery.
4. Unsafe-zone near-target recovery, routed to abort-candidate.
5. A v5d-style summary table comparing boundary-first routing, residual routing,
   and one-score risk routing under fixed intervention budgets.

## Claim To Use

The SurRoL project should be described as:

> a failure-aware SurRoL reliability-routing layer that diagnoses execution,
> perception, contact, and unsafe-recovery mechanisms around existing surgical
> task policies, then routes them to recovery, re-estimation/review, or abort
> candidates under fixed intervention budgets.

It should not be described as a model that learns surgical manipulation from
unlabeled data or transfers CircleRL PPO weights into SurRoL.
