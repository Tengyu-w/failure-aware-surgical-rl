# Experiment Evidence Summary

This document is the compact research narrative behind the repository. It is
written for a supervisor who wants to understand what was done, why each step
was necessary, what the evidence shows, and where the work remains limited.

## 1. Starting Problem

The project begins with surgical robot learning in simulation. The initial
question could have been ordinary task success:

> Can an RL policy reach the target or finish the surgical proxy task?

The research question then became more specific:

> Can the system recognize unreliable execution and route it into automatic
> recovery, review, or abort-candidate decisions before the failure becomes
> unsafe or unrecoverable?

This matters because task success alone hides dangerous intermediate behavior.

## 2. Proxy Safety-Control Evidence

The custom proxy environment was built to test safety-control mechanisms
quickly. It includes:

- a tool and target;
- a forbidden region;
- a force/contact proxy;
- workspace boundaries;
- a per-episode safety budget.

Main result:

| Method | Prototype budget exhaustion | Strict budget exhaustion |
| --- | ---: | ---: |
| unshielded PPO | 0.907 | 0.977 |
| always tangent | 0.000 | 0.000 |
| risk-gated tangent | 0.000 | 0.000 |
| mechanism-routed tangent | 0.000 | 0.000 |

Main lesson: tangent backup can preserve safety-budget behavior, but always-on
backup over-intervenes.

## 3. Why Risk Gating Was Needed

Always tangent backup activates at every timestep. That is safe but too
conservative. Risk-gated tangent asks:

> Is this action actually risky enough to need backup control?

It uses interpretable features such as forbidden-zone clearance, force proxy,
remaining budget, progress, and action magnitude.

Result:

- prototype activation falls from 1.000 to 0.450;
- strict activation falls from 1.000 to 0.426;
- budget exhaustion remains 0.000.

Main lesson: reliability analysis can become a runtime decision signal.

## 4. Why Mechanism Routing Was Added

Risk-gated tangent still uses one total risk decision. The ECG-inspired upgrade
separates mechanisms:

- Stage 1 boundary risks trigger tangent backup;
- Stage 2 residual risks are logged as review evidence.

Result:

| Preset | Risk-gated activation | Mechanism-routed activation | Risk-gated non-correction | Mechanism-routed non-correction |
| --- | ---: | ---: | ---: | ---: |
| prototype | 0.450 | 0.443 | 0.027 | 0.020 |
| strict | 0.426 | 0.416 | 0.030 | 0.021 |

Main lesson: the improvement is modest, but the controller becomes more
explainable because it separates boundary risk from residual mechanism risk.

## 5. SurRoL Migration Evidence

The project then moved beyond the custom proxy into SurRoL/PyBullet surgical
simulation. Rendered evidence is provided for:

- NeedleReach;
- NeedlePick;
- GauzeRetrieve.

The repository includes GIF/MP4 rollouts, selected frame PNGs, and trace CSVs.

Main lesson: the project is not only a toy proxy. It includes surgical
simulation evidence.

## 6. Fault Taxonomy And Routes

The project formalized four routes:

| Route | Meaning |
| --- | --- |
| `auto_execute` | continue normal execution |
| `auto_recovery` | recover automatically from reversible drift |
| `human_review` | review or re-estimate uncertain visual/contact states |
| `abort_candidate` | stop or flag unsafe recovery |

Main lesson: different failure mechanisms need different runtime responses.

## 7. Multi-Seed Recovery Evidence

Selected 10-seed recovery evidence:

| Fault family | Perturbed | Recovered |
| --- | ---: | ---: |
| NeedlePick action faults | 0/10 | 9/10 or 10/10 |
| GauzeRetrieve action faults | 0/10 | 10/10 |
| perception bias/depth errors | 0/10 | 10/10 |
| jaw-stuck open | 0/10 | 10/10 |

Main lesson: route-specific recovery can be effective under injected faults in
the current simulation harness.

Limitation: some recovery primitives are scripted or oracle-assisted.

## 8. Learned And Observable Supervisors

The learned route classifier shows that route decisions can be predicted from
episode features:

| Metric | Value |
| --- | ---: |
| held-out episodes | 460 |
| accuracy | 0.846 |
| macro-F1 | 0.828 |
| missed review-or-abort rate | 0.000 |

The observable supervisor shows that jaw-stuck detection can use command and
progress signals rather than privileged phase/contact state.

Main lesson: the reliability router can move beyond purely hand-written
decisions.

Limitations:

- route labels are distilled from the current system;
- observable recovery execution still uses scripted primitives.

## 9. Embedding-Risk Training Evidence

Embedding/KNN instability analysis was connected to PPO through reward shaping
and hard-negative curriculum.

Main lesson: embedding risk can affect training behavior.

Limitation: multi-seed results do not show robust success-rate or
safety-budget improvement. This is preliminary.

## 10. Final Interpretation

The project should be presented as a runtime reliability-supervision system:

```text
execution evidence
  -> mechanism-specific risk analysis
  -> route decision
  -> execute / recover / review / abort-candidate
```

The strongest evidence is internal simulation reliability, not surgical
deployment.
