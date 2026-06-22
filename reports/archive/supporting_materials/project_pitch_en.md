# Project Pitch: Failure-Aware Runtime Recovery for Surgical Embodied Intelligence

## Title

Failure-Aware Runtime Recovery for Simulation-Trained Surgical Autonomy

## Short Summary

This project studies a lightweight reliability layer for surgical robot learning systems. Instead of replacing the main policy or controller, it asks whether abnormal execution can be detected, diagnosed, and partially recovered at runtime. The current prototype started from abstract 3D surgical tool navigation and has now been extended to SurRoL `NeedlePick`, where clean oracle execution succeeds but action-corrupted execution fails.

## Motivation

Surgical embodied intelligence systems are often evaluated by task success under nominal conditions. However, surgical autonomy also needs runtime assurance:

- When is the policy becoming unreliable?
- What type of failure is occurring?
- Should the system continue, recover, stop, or ask for human review?
- How can recovery be triggered without excessive unnecessary intervention?

This project focuses on that reliability gap. It is not a full surgical autonomy system; it is an early-stage runtime recovery layer intended to complement simulation-trained surgical policies.

## Current SurRoL Evidence

A clean SurRoL SR-VPPV environment has been deployed and smoke-tested on multiple tasks:

- `ECMReach`
- `NeedleReach`
- `NeedlePick`
- `GauzeRetrieve`
- `BiPegTransfer`
- `NeedleRegrasp`

The main experiment currently uses `NeedlePick`, because it provides a clear failure-aware benchmark:

| Condition | Success |
|---|---:|
| clean oracle | 3/3 |
| action-noise oracle | 0/3 |
| action-dropout oracle | 0/3 |
| execution-slip oracle | 0/3 |

With a coarse runtime trigger and 32-step recovery window, a generic oracle-override recovery gives:

| Failure | Perturbed Success | Monitor-Corrected Success |
|---|---:|---:|
| action_noise | 0/5 | 5/5 |
| action_dropout | 0/5 | 1/5 |
| execution_slip | 0/5 | 3/5 |

A phase-aware recovery policy then improves the harder failures:

| Failure | Perturbed Success | Phase-Aware Recovery Success |
|---|---:|---:|
| action_noise | 0/5 | 5/5 |
| action_dropout | 0/5 | 5/5 |
| execution_slip | 0/5 | 5/5 |

The strongest current result is not that a generic monitor solves every failure. Rather, it shows that recovery effectiveness depends on failure type and task phase: action noise can be recovered by action override, while dropout/slip require grasp-stage retry. This turns the project into a concrete study of failure taxonomy, selective recovery, and intervention policy.

## Method Sketch

The current runtime loop can be summarized as:

```text
policy action -> failure injection -> runtime risk trigger -> recovery override -> evaluation
```

The logged metrics include:

- task success;
- final distance and distance reduction;
- risk event rate;
- monitor trigger count;
- recovery override rate;
- step-level distance, trigger, and action-deviation traces.

## Research Framing

The project is best framed as:

> extending surgical embodied intelligence from task autonomy to failure-aware autonomy.

It complements, rather than replaces, full surgical autonomy systems:

| Full system component | Reliability-layer extension |
|---|---|
| surgical simulator | failure injection benchmark |
| RL policy | runtime reliability monitor |
| control / servoing | recovery trigger and intervention policy |
| task success | success + recovery + false intervention |
| automation | selective autonomy / human review |

## Limitations

The current prototype is still preliminary:

- 5 seeds only;
- one main SurRoL task with full recovery experiments;
- rule-based trigger rather than calibrated uncertainty;
- oracle/phase-aware rule-based recovery rather than learned recovery;
- no real-robot or sim-to-real claim.

These limitations define the next research steps rather than invalidating the direction.

## Next Steps

1. Expand from 3 seeds to 5-10 seeds on `NeedlePick`.
2. Add phase-aware recovery for approach, grasp, and lift/transfer stages.
3. Extend the same evaluation to `GauzeRetrieve`, `NeedleRegrasp`, and `PegTransfer`.
4. Replace hard-coded trigger rules with learned or calibrated risk scores.
5. Add human-review trigger metrics for unrecoverable cases.
