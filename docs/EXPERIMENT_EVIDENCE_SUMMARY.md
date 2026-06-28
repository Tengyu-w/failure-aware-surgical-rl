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

This is why the project does not claim that representation analysis alone
"fixes" RL training. In this repository, embedding evidence is useful, but it
is only one part of a larger reliability pipeline.

## 10. Visual Reliability Evidence

The SurRoL branch also tests visual-side reliability. Rendered or pseudo-visual
features can be corrupted with noise, brightness shifts, occlusion, blackout,
or mixed perturbations. The project includes:

- visual denoising adapter training from clean/corrupt feature pairs;
- visual action-risk head training from policy-vs-oracle action gaps;
- visual recovery memory using PCA/KNN over high-risk steps.

Main lesson: the project is not only classifying final episode outcomes. It is
also building pieces for perception-to-action reliability monitoring.

Limitation: these visual modules are still lightweight proxies, not full
surgical scene segmentation or clinical visual validation.

## 11. ECG-Style Broad RL Reliability Upgrade

The newest upgrade mirrors the ECG project's broader structure. It does not
stop at embedding. It checks multiple evidence families:

| Evidence family | Surgical RL implementation |
| --- | --- |
| representation structure | PCA, centroid distance, normalized centroid distance, silhouette, Davies-Bouldin |
| prototype/kNN evidence | nearest route prototype, prototype conflict, kNN distance, entropy, local purity, route mixing |
| confidence and boundary evidence | MSP, entropy, inverse margin, route-error AUROC, review-risk score |
| trajectory structure | progress, stagnation, final distance, monitor triggers, recovery replans, unsafe events |
| perturbation/OOD evidence | action noise/dropout/slip, perception bias, depth error, jaw-stuck, near-target drift |
| model intervention | multi-signal review/abort risk head and four-way mechanism router |

Main diagnostics:

| Metric | Value |
| --- | ---: |
| silhouette | 0.412 |
| mean local purity | 0.969 |
| kNN route conflict rate | 0.019 |
| review-score AUROC for review/abort | 1.000 |

The important discovery is that ordinary route softmax uncertainty is not
enough for review/abort decisions:

| Score | Route-error AUROC | Review/abort AUROC |
| --- | ---: | ---: |
| MSP | 0.993 | 0.079 |
| entropy | 0.993 | 0.089 |
| inverse margin | 0.993 | 0.065 |
| review score | 0.118 | 1.000 |

So the project trains a separate multi-signal reliability model instead of
trusting one classifier confidence score.

Model-side result:

| Component | Held-out result |
| --- | --- |
| all multi-signal review head | AUROC 1.000, AUPRC 1.000, recall 0.941, FPR 0.000 |
| four-way mechanism router | accuracy 0.973, macro-F1 0.981, missed review-or-abort 0.000 |

Main lesson: broad reliability analysis can be converted into a learned
supervisor. It improves the system by deciding the runtime route, even though
the current evidence does not prove a robust end-to-end PPO policy improvement.

Limitation: labels are weak/proxy labels from simulator logs and injected
failures, and some features are episode-level summaries.

## 12. Final Interpretation

The project should be presented as a runtime reliability-supervision system:

```text
execution evidence
  -> mechanism-specific risk analysis
  -> route decision
  -> execute / recover / review / abort-candidate
```

The strongest evidence is internal simulation reliability, not surgical
deployment.

The most honest experimental arc is:

```text
train baseline RL
  -> collect errors and weak labels
  -> run embedding, confidence, trajectory, visual, and perturbation analysis
  -> try risk-aware retraining
  -> find that retraining alone is not robust
  -> train multi-signal risk and mechanism-route models
  -> use multi-mechanism runtime recovery and review routing
```
