# Reliability-Supervised Surgical Embodied AI Framework

This document is the cleaned project spine. It turns the project away from a
generic "RL recovery" story and into a mechanism-aware reliability-supervision
story for surgical embodied intelligence. A VPPV-style
perception-policy-servoing loop is used as one motivating case study, but the
framework is not tied to a private or unreleased model.

## 1. Project Problem

Public-facing title:

> Reliability-Supervised Surgical Embodied AI: Mechanism-Aware Failure
> Detection and Routing

Core problem:

> A surgical embodied-AI pipeline can move from visual state estimation to
> policy-level movement and then to visual servoing or controller execution,
> but the system lacks a mechanism layer that decides where a failure comes
> from and when it should re-observe, re-estimate, recover, pause for review,
> or request human takeover.

The contribution is not a new low-level grasp controller. The contribution is
a reliability-supervision layer that detects when visual estimation, approach
movement, or near-target servoing has become unreliable.

## 2. Full Project Structure

The project is organized as a sequence of increasingly realistic checks:

| Step | Role in the project |
| --- | --- |
| perception-policy problem identification | identify that the key failure is unreliable target estimation, approach movement, or near-target servoing, not low-level jaw learning |
| self-built proxy simulator | isolate the failure mechanism in a small environment where biased targets, obstacle risk, and recovery can be controlled |
| proxy recovery/routing | show that the system can detect biased movement and route to recovery/re-estimation instead of uniform retry |
| SurRoL migration | move the same reliability idea into rendered surgical-simulation rollouts |
| policy/actor surrogate | create a policy-side rollout representation when the upstream reference checkpoint and hidden activations are unavailable |
| mechanism perturbation dataset | generate weak labels through controlled perturbations rather than manual action labels |
| internal separability analysis | test whether actor/rollout embeddings, PCA, KNN/prototype conflict, and action-outcome evidence separate mechanisms |
| three-level route design | map visual bias, approach drift, and near-target servo failure to different interventions |
| route validation | check ablation, transfer, severity holdout, mixed-priority behavior, early warning, false alarms, and true mixed SurRoL rollouts |

Research sequence:

```text
problem discovery
  -> proxy mechanism proof
  -> SurRoL migration
  -> policy/actor-surrogate evidence
  -> internal mechanism separability
  -> three-level routing
  -> multi-angle validation
```

## 3. Three Mechanisms

The current version keeps three mechanisms because they are closest to the
common perception-policy-servoing pipeline used in many surgical simulation
and robot-learning systems.

| Mechanism | Controlled perturbation | Evidence symptom | Route |
| --- | --- | --- | --- |
| `visual_estimation_bias` | shift the estimated target as if segmentation, depth, or a regressor is biased | visual residual or target disagreement rises; the action is plausible for the wrong target | re-observe / re-estimate |
| `policy_approach_drift` | bias the approach movement into a wrong near-target region | progress toward the observed target stalls or action-outcome mismatch rises | low-gain corrective movement / replan |
| `near_target_occlusion_or_servo_failure` | degrade near-target observation or servo evidence | uncertainty rises after the tool is close enough that blind continuation is unsafe | pause / camera reposition / human review |

Safety override:

| Condition | Route |
| --- | --- |
| unsafe near-target continuation | abort / human takeover |

## 4. Weak-Label Data Generation

The project does not require manual action labels. Labels come from controlled
perturbations:

```text
normal rollout
visual bias rollout
policy drift rollout
near-target occlusion / servo-failure rollout
```

Each trajectory should expose:

| Data group | Fields |
| --- | --- |
| transition | `state_t`, `action_t`, `state_t+1` |
| geometry | `distance_to_goal`, `progress`, near-target status |
| visual estimate | `estimated_target`, `observed_target`, visual residual |
| policy behavior | action magnitude, action deviation, actor or rollout embedding |
| outcome | success/failure, final distance, unsafe continuation |
| label | mechanism label and expected route |

These are weak labels from simulator perturbations. They are useful for
research evidence, but they are not independent surgeon annotations.

## 5. Evidence And Embedding Analysis

The ECG-style part of the project is the analysis-to-routing loop:

| Analysis | Question |
| --- | --- |
| actor or rollout embedding | do the three failure mechanisms separate in representation space? |
| visual-state uncertainty | does visual/depth evidence rise before final failure? |
| action-outcome mismatch | can the system detect that commanded movement is not producing expected progress? |
| KNN / prototype conflict | is the current rollout atypical compared with normal or known mechanism prototypes? |
| composite risk score | can risk alarm earlier than final success/failure? |

Because the upstream reference checkpoint, training data, and hidden
activations are not available, the current implementation uses
behavior-derived rollout representations. This is weaker than full
model-internal ECG-style analysis, but it preserves the logic:

```text
rollout behavior
  -> representation / neighborhood evidence
  -> discovered risky regions
  -> route assignment
  -> held-out verification
```

## 6. Policy-Side Mechanism Separability Test

The project does include a model-side separability test, with a careful
boundary.

It is not a hidden-layer audit of an upstream private surgical policy model.
The reference checkpoint, training data, raw hidden activations, and confidence
outputs are not available. Instead, the project uses policy-side surrogate
evidence derived from simulator rollouts:

- policy-proxy evidence;
- action deviation;
- action-outcome mismatch;
- local neighborhood instability;
- progress regularity;
- visual/depth residuals;
- rollout behavior embeddings.

The test asks whether these features separate mechanisms before routes are
assigned:

```text
step trace features
  -> PCA / behavior embedding
  -> KNN and prototype conflict diagnostics
  -> k-means clusters on train episodes
  -> cluster evidence fingerprints
  -> route assignment
  -> held-out weak-label evaluation
```

The mechanism labels are not used to form the clusters. They are used afterward
to verify whether the discovered behavior regions align with expected routes.

Current result:

| Held-out quantity | Value |
| --- | ---: |
| step rows | 3,351 |
| episodes | 26 |
| route assignment accuracy | 0.996 |
| macro-F1 | 0.995 |
| missed high-risk step rate | 0.000 |
| nominal false alarm rate | 0.025 |

This result should be described as:

> policy-side / behavior-derived mechanism separability in simulator rollouts.

It should not be described as:

> full hidden-layer discovery of failure mechanisms in an upstream private
> surgical policy model.

## 7. Three-Level Composite Routing

The router is mechanism-specific and has three levels plus a safety override:

| Level | Mechanism | Route |
| --- | --- | --- |
| 1 | `visual_estimation_bias` | re-observe / re-estimate |
| 2 | `policy_approach_drift` | low-gain corrective movement / replan |
| 3 | `near_target_occlusion_or_servo_failure` | pause / camera reposition / human review |
| override | unsafe near-target | abort / human takeover |
| normal | no high-risk evidence | continue |

This should be described as compound routing rather than uniform retry,
because different mechanisms imply different interventions.

## 8. Route Self-Verification

The route is not validated by a single qualitative example. The current
project uses several complementary checks:

| Check | Evidence supported |
| --- | --- |
| step-level mechanism evidence | per-step signals identify the expected route |
| single-evidence ablation | one signal is weaker than composite evidence |
| cross-task frozen thresholds | route thresholds are not only tuned to one task |
| severity holdout | route boundaries survive stronger unseen perturbations |
| mixed-priority audit | compound failures require route priority rather than max-score or uniform retry |
| behavior-derived clustering | route assignment can come from policy/trajectory regions rather than direct label lookup |
| early-warning and false-alarm checks | risk is useful only if it warns early without over-interrupting normal rollouts |
| true mixed SurRoL rollouts | route logic still helps when mixed fault proxies execute in PyBullet |

Current headline results:

| Evidence | Result |
| --- | --- |
| step-level composite | 10,823 rows; macro-F1 0.998; missed high-risk 0.000 |
| behavior-derived routing | 3,351 held-out rows; macro-F1 0.995; nominal false alarm 0.025 |
| mixed-priority | priority 1.000 macro-F1; max-signal 0.033; uniform retry 0.000 |
| true mixed rollouts | perturbed 0/40 success; priority-routed 40/40 success |

## 9. Evaluation Metrics

The main metrics should be reliability metrics, not only success rate:

| Metric | Meaning |
| --- | --- |
| mechanism classification accuracy / macro-F1 | whether the system identifies the failure source |
| high-risk failure capture at fixed intervention budget | whether limited review/recovery budget catches important risk |
| residual unsafe failure rate | how much unsafe failure remains after routing |
| route-specific recovery success | whether the selected route works for that mechanism |
| early warning lead time | how early risk is detected before terminal failure |
| false alarm rate on normal rollouts | whether normal behavior is interrupted too often |

## 10. Current Minimal Experiment

The most valuable next experiment is:

```text
SurRoL NeedlePick or GauzeRetrieve with a VPPV-style perception-policy case study
  -> generate normal, visual bias, policy drift, near-target failure rollouts
  -> extract state-action-progress behavior features
  -> train a light mechanism classifier and router
  -> evaluate 10-20 seeds with fixed-budget failure capture
```

This experiment is more valuable than another recovery video because it tests
the core claim:

> The system knows when it is unreliable, why it is unreliable, and which
> intervention matches the mechanism.
