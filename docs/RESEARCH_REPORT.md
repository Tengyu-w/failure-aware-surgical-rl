# Research Report

Failure-Aware Surgical RL Under Runtime Uncertainty

This report summarizes the public, research-safe version of the project. It is
written for a reader who has not seen the local experiment archive and needs to
understand the full experimental logic: why the project was designed, what was
tested, what improved, what failed, and what remains unproven.

The project is a research prototype only. It is not a surgical device, not a
clinical validation package, and not evidence of hardware-validated autonomy.

## How To Read This GitHub Version

The public repository preserves the research evolution, so some tables and
figures come from earlier proxy, SurRoL, and embedding-risk experiment stages.
Those earlier results are useful as historical evidence, but they are not all
final claims.

For final GitHub interpretation, use the following hierarchy:

- risk-gated tangent is the strongest proxy controller result;
- mechanism-routed tangent is the ECG-inspired upgrade of that controller into
  a mechanism-separated reliability router;
- SurRoL recovery tables show route-specific recovery under injected faults;
- learned and observable supervisors are reliability-routing prototypes;
- embedding-risk PPO is preliminary training-loop evidence and should not be
  used as the main claim.
- the full experimental arc is a learning-to-routing pipeline: train, label
  failures, analyze embeddings, try retraining, then route unreliable execution.

## Project Logic At A Glance

The project did not begin as a full reliability-routing system. It began as a
small constrained surgical-tool RL proxy, then gradually changed shape as the
failure evidence became clearer.

The first observation was that a learned or scripted policy can fail for
different reasons: it may drift toward a forbidden region, exhaust a safety
budget, stall before reaching the goal, suffer a visual-state error, or enter a
grasp/contact state where automatic recovery is no longer trustworthy. Treating
all of those as one generic failure is not useful.

The second step was to build a tangent backup controller. This controller
showed that safety-budget failures can be suppressed in the proxy, but always
activating the backup controller creates unnecessary intervention.

The third step was risk-gated tangent backup. Instead of applying tangent
backup at every timestep, the supervisor first evaluates interpretable risk
signals such as proposed forbidden-zone proximity, current clearance, remaining
budget, force proxy, action magnitude, and stalled progress.

The fourth step was the ECG-inspired mechanism-routed upgrade. The supervisor
was changed from one total risk score into a two-stage route system. Stage 1
handles boundary safety risks that should trigger tangent backup. Stage 2
records residual mechanisms such as low remaining budget or stagnation as
review evidence. This makes the controller more like a reliability router than
a simple shield.

The fifth step was migration into SurRoL/PyBullet tasks. The same reliability
question was tested on rendered surgical simulation rollouts for NeedleReach,
NeedlePick, and GauzeRetrieve.

The sixth step was route-specific recovery. The project formalized four
runtime routes: continue, recover, review, and abort candidate. Multi-seed
SurRoL experiments then tested whether injected action, perception, and
jaw-stuck failures can be recovered or routed.

The final step was to test whether instability analysis can also affect
training. Embedding/KNN risk was fed into PPO through reward shaping and
hard-negative curriculum. This changed learned behavior and improved some
return/distance metrics, but did not yet produce robust success/safety gains.

That negative result is part of the final argument. The project does not stop
at "make the RL model better." It shows that risk-aware retraining alone is not
enough in the present setup, so the stronger design is to add runtime routing
around the learned policy.

This is the final project narrative:

```text
constrained surgical proxy
  -> tangent backup control
  -> risk-gated tangent supervisor
  -> mechanism-routed tangent supervisor
  -> SurRoL reliability migration
  -> route-specific recovery and review
  -> learned / observable route supervision
  -> preliminary embedding-risk-guided PPO training
  -> runtime routing after retraining limits are observed
```

## Main Evidence Snapshot

| Evidence block | Main result | Interpretation | Limitation |
| --- | --- | --- | --- |
| Risk-gated tangent | Budget exhaustion remains 0.000 while activation falls from 1.000 to 0.450/0.426. | Reliability analysis can gate backup control. | Custom proxy only. |
| Mechanism-routed tangent | Budget exhaustion remains 0.000 while activation falls further to 0.443/0.416. | The controller now separates boundary and residual mechanisms. | Improvement over risk-gated is modest. |
| SurRoL recovery | Key injected faults recover from 0/10 perturbed success to 9/10 or 10/10 recovered success. | Route-specific recovery works in current simulation harness. | Scripted/oracle components remain. |
| Learned route classifier | Held-out accuracy 0.846, macro-F1 0.828, missed review-or-abort 0.000. | Route decisions are learnable from episode features. | Labels are distilled from current rules. |
| Observable supervisor | Jaw-stuck perturbations detected in 10/10 episodes for NeedlePick and GauzeRetrieve. | Privileged-state dependence is reduced for the decision trigger. | Recovery execution remains scripted. |
| Embedding-risk PPO | Curriculum fine-tuning improves return and strict final distance but not success/budget outcomes. | Instability analysis can enter training. | Preliminary and not robust policy improvement. |
| Learning-to-routing flow | PPO is trained from reward; reliability labels are built afterward from rollout logs and failure design. | The project explains how labels, embeddings, failed retraining, and routing connect. | Labels remain weak/proxy labels, not expert clinical annotations. |

## How RL, Labels, And Error Classes Connect

### RL Training Signal

The policy is trained primarily through simulator interaction. It observes
state or visual features, outputs an action, receives reward and a termination
signal, and updates through PPO. The proxy reward includes distance-to-goal,
force/contact proxy, motion cost, forbidden-region and workspace penalties,
success bonus, and safety-budget termination. The SurRoL wrapper adds options
for progress reward, distance shaping, near-target action damping, danger-zone
penalty, pseudo-vision, and rendered visual features.

### Weak Risk Labels

After rollouts are generated, timestep risk labels are built from logs. A
timestep can be labeled risky because it is near a forbidden zone, has high
force/contact proxy, has low remaining budget, is stalled while far from the
goal, has explicit monitor/unsafe events, or belongs to a failed or
budget-exhausted episode.

### Failure And Route Labels

Errors are then organized into routeable families:

| Failure family | Examples | Runtime route |
| --- | --- | --- |
| nominal execution | no injected failure | `auto_execute` |
| reversible execution drift | action noise, dropout, execution slip | `auto_recovery` |
| visual-state error | perception bias, depth scale error | `human_review` or re-estimation |
| grasp/contact uncertainty | jaw stuck open | review or observable retry |
| unsafe recovery proxy | danger-zone abort | `abort_candidate` |

This is the bridge from "the model made an error" to "the system knows what
kind of intervention is appropriate."

### Visual Reliability Signals

The visual branch adds clean/corrupt visual-feature pairs for denoising and
policy-vs-oracle action-gap labels for a visual action-risk head. These modules
are closer to surgical embodied-intelligence concerns because they ask whether
visual parsing and perception-to-action behavior remain reliable under
occlusion, noise, brightness shift, frame lag, or corrupted rendered features.

## Stage 1: Custom Constrained Surgical Proxy

### What Was Done

A lightweight 3D surgical-tool navigation environment was built. The tool must
reach a target while avoiding a forbidden region, workspace boundary, force
proxy, and per-episode safety budget exhaustion.

### Why It Was Done

The proxy provides a fast environment for testing safety-control ideas before
moving to heavier SurRoL/PyBullet experiments. It makes it easy to run many
controller comparisons and inspect failure mechanisms.

### Evidence

The proxy supports PPO training, random/heuristic policies, safety shields,
tangent backup, risk-gated tangent, mechanism-routed tangent, and embedding-risk
training wrappers.

### Limitation

The proxy is not realistic surgery. It is a method-development environment.

## Stage 2: Tangent Backup Control

### What Was Done

The tangent backup controller modifies unsafe actions so that the tool moves
around the forbidden region boundary rather than stopping or pushing into the
unsafe zone.

### Why It Was Done

In a surgical setting, an emergency stop may be safe but can stall the task.
Tangential motion models a more useful backup strategy: stay near the boundary
but move around it.

### Evidence

Always-tangent backup reaches 0.000 budget exhaustion in prototype and strict
proxy settings.

### Limitation

Always-on tangent backup is too active. It supervises every timestep and
therefore becomes a heavy-handed correction layer.

## Stage 3: Risk-Gated Tangent Backup

### What Was Done

An interpretable risk gate was placed before tangent backup. It evaluates
runtime features before deciding whether the backup controller should be active.

Risk reasons include:

- proposed forbidden-zone proximity;
- current forbidden-zone clearance;
- workspace boundary risk;
- force proxy;
- low remaining safety budget;
- progress stagnation;
- large action magnitude.

### Why It Was Done

This turns reliability analysis from post-hoc explanation into a runtime
decision signal.

### Evidence

| Preset | Method | Budget exhaustion | Supervisor activation |
| --- | --- | ---: | ---: |
| prototype | always tangent | 0.000 | 1.000 |
| prototype | risk-gated tangent | 0.000 | 0.450 |
| strict | always tangent | 0.000 | 1.000 |
| strict | risk-gated tangent | 0.000 | 0.426 |

### Interpretation

Risk-gated tangent preserves the 0.000 budget-exhaustion safety of always
tangent while reducing supervisor-on timesteps by roughly half.

### Limitation

The risk gate still compresses multiple mechanisms into one risk decision.

## Stage 4: Mechanism-Routed Tangent Backup

### What Was Done

The controller was upgraded into
`MechanismRoutedTangentSafetyShieldAction`. The environment variant is
`conditioned_mechanism_routed_tangent_shielded`.

The route logic is:

1. Stage 1 boundary tangent backup handles forbidden-zone, workspace, and force
   boundary risks.
2. Stage 2 residual review records low-budget, stagnation, late-progress, and
   abnormal-action mechanisms.

### Why It Was Done

This is the direct structural transfer from the ECG project. The lesson is that
different failure mechanisms should not be collapsed into one total risk score.

### Evidence

| Preset | Method | Budget exhaustion | Supervisor activation | Non-correction activation |
| --- | --- | ---: | ---: | ---: |
| prototype | risk-gated tangent | 0.000 | 0.450 | 0.027 |
| prototype | mechanism-routed tangent | 0.000 | 0.443 | 0.020 |
| strict | risk-gated tangent | 0.000 | 0.426 | 0.030 |
| strict | mechanism-routed tangent | 0.000 | 0.416 | 0.021 |

The new router records mean Stage 1 and Stage 2 activity:

| Preset | Stage 1 boundary activations | Stage 2 residual activations |
| --- | ---: | ---: |
| prototype | 68.190 | 2.057 |
| strict | 48.417 | 1.507 |

### Interpretation

The numerical gain over risk-gated tangent is modest, but the system is more
interpretable. It reports whether a route came from boundary risk or residual
mechanism risk.

### Limitation

Stage 2 currently logs review evidence. It does not yet trigger a separate
learned residual recovery policy.

## Stage 5: SurRoL Migration

### What Was Done

The reliability-supervision idea was migrated into SurRoL/PyBullet surgical
simulation tasks:

- NeedleReach;
- NeedlePick;
- GauzeRetrieve.

Rendered GIF/MP4 rollouts, selected frames, and trace CSVs are committed under
`reports/media/surrol_render_evidence/`.

### Why It Was Done

The custom proxy is useful but insufficient for a surgical robotics story.
SurRoL migration shows that the project can be connected to a recognized
surgical simulation environment.

### Limitation

This is still simulation evidence. It should not be interpreted as hardware
deployment.

## Stage 6: Fault Taxonomy And Runtime Routes

### What Was Done

The project defines four route families:

| Route | Meaning |
| --- | --- |
| `auto_execute` | Continue nominal execution. |
| `auto_recovery` | Apply automatic recovery for reversible drift. |
| `human_review` | Route uncertain visual, grasp, or contact states to review or re-estimation. |
| `abort_candidate` | Stop or flag recovery when an unsafe proxy is triggered. |

### Why It Was Done

Without route labels, recovery results look like isolated demos. With route
labels, the project becomes a reliability system.

### Limitation

The labels are engineered from the current experimental setup, not independent
expert annotations.

## Stage 7: Multi-Seed SurRoL Recovery

### What Was Done

The project evaluates recovery under injected action, perception, and jaw-stuck
faults.

### Evidence

| Task | Fault family | Perturbed | Recovered |
| --- | --- | ---: | ---: |
| NeedlePick | action noise/dropout/slip | 0/10 | 9/10 or 10/10 |
| GauzeRetrieve | action noise/dropout/slip | 0/10 | 10/10 |
| NeedlePick | perception bias/depth error | 0/10 | 10/10 |
| GauzeRetrieve | perception bias/depth error | 0/10 | 10/10 |
| NeedlePick | jaw-stuck open | 0/10 | 10/10 |
| GauzeRetrieve | jaw-stuck open | 0/10 | 10/10 |

### Interpretation

Route-specific recovery can recover several injected fault families in the
current simulation harness.

### Limitation

Some recovery primitives are scripted or oracle-assisted. This is not
end-to-end learned recovery.

## Stage 8: Learned Route Classifier

### What Was Done

A safety-biased route classifier was trained to predict runtime routes from
episode features.

### Evidence

| Metric | Value |
| --- | ---: |
| held-out episodes | 460 |
| accuracy | 0.846 |
| macro-F1 | 0.828 |
| missed review-or-abort rate | 0.000 |
| false review-or-abort rate | 0.162 |

### Interpretation

Route prediction is learnable in the current dataset, and the classifier avoids
missing review-or-abort cases in the held-out split.

### Limitation

The training labels are distilled from the project routing logic, not from
independent expert review.

## Stage 9: Observable Supervisor

### What Was Done

The jaw-stuck replan trigger was moved away from privileged phase/contact state
toward observable command/progress signals:

- jaw close command count;
- goal-distance stagnation;
- minimum-distance improvement;
- offline observable risk score.

### Evidence

At threshold 3.0, the observable risk score detects 10/10 jaw-stuck perturbed
episodes for both NeedlePick and GauzeRetrieve, with 0/10 nominal
monitor-corrected alarms in current logs.

### Limitation

The decision trigger is more observable, but the executed recovery primitive
still uses scripted waypoint regeneration.

## Stage 10: Embedding-Risk PPO Training

### What Was Done

Embedding/KNN instability risk was fed back into PPO through:

- risk-aware reward penalties;
- hard-negative curriculum reset;
- two-stage curriculum fine-tuning.

### Evidence

The three-seed follow-up shows:

- curriculum fine-tuning improves mean return;
- strict final distance improves;
- success rate and budget exhaustion do not reliably improve.

### Interpretation

Embedding risk has become a training signal, not only an explanation tool.

### Limitation

This is preliminary. It should not be claimed as robust model improvement.

## Stage 11: Why Runtime Routing Remains Necessary

### What Was Done

The project interprets the embedding-risk PPO result as a training-loop test,
not as the final system. Because risk-aware reward shaping and hard-negative
curriculum do not reliably improve success rate or safety-budget exhaustion,
the final architecture keeps a runtime reliability supervisor around the
policy.

### Why It Matters

This mirrors the practical limitation in surgical embodied intelligence:
better visual parsing, spatial priors, or RL training can improve the base
policy, but final-step occlusion, grasp-point error, tissue deformation,
stagnation, and action-outcome mismatch can still occur. A surgical autonomy
system needs an execution-time decision layer.

### Final Route

```text
baseline policy
  -> risk and visual reliability evidence
  -> failure family / mechanism inference
  -> auto execute, auto recovery, human review, or abort candidate
```

### Limitation

The current routing labels and recovery policies remain research prototypes.
They are distilled from simulator logs, injected failures, and proxy rules.
They are not independent surgeon annotations.

## Final Claim

The strongest safe claim is:

> Failure-aware runtime supervision can turn surgical RL reliability analysis
> into mechanism-specific execution routes in simulation.

The project supports this through proxy controller evidence, SurRoL recovery
evidence, learned route classification, observable supervision, and preliminary
embedding-risk training experiments.

## What Remains Unproven

- real-robot validation;
- clinical validation;
- formal safety guarantees;
- independent expert route labels;
- fully learned recovery primitives;
- robust policy improvement from embedding-risk training.

## Recommended Wording

We propose a failure-aware runtime reliability supervisor for simulated
surgical robot learning. The system combines proxy-level safety control,
SurRoL-based recovery routing, learned route classification, observable
supervision, and mechanism-separated tangent backup. The evidence supports
internal simulation reliability: risky states can be detected, routed, and in
several injected fault settings recovered. The project should not be presented
as real-robot validation or complete surgical autonomy.
