# Reliability-Supervised VPPV Framework

This document is the cleaned project spine. It turns the project away from a
generic "RL recovery" story and into a mechanism-aware reliability-supervision
story for VPPV-style surgical embodied intelligence.

## 1. Project Problem

New title:

> Reliability-Supervised VPPV: Mechanism-Aware Failure Detection and Routing
> for Surgical Embodied Intelligence

Core problem:

> VPPV can move from visual state estimation to policy movement and then to
> visual servoing, but the system lacks a mechanism layer that decides where a
> failure comes from and when it should re-observe, re-estimate, recover, or
> request human takeover.

The contribution is not "make the robot better at grasping." The contribution
is to let the system recognize when its own visual estimate, approach movement,
or near-target servoing has become unreliable.

## 2. Three Mechanisms

The current version keeps three mechanisms because they are closest to the
VPPV pipeline.

| Mechanism | Controlled perturbation | Evidence symptom | Route |
| --- | --- | --- | --- |
| `visual_estimation_bias` | shift the estimated target as if segmentation, depth, or a regressor is biased | visual residual or target disagreement rises; the action is plausible for the wrong target | re-observe / re-estimate |
| `policy_approach_drift` | bias the approach movement into a wrong near-target region | progress toward the observed target stalls or action-outcome mismatch rises | low-gain corrective movement / replan |
| `near_target_occlusion_or_servo_failure` | degrade near-target observation or servo evidence | uncertainty rises after the tool is close enough that blind continuation is unsafe | pause / camera reposition / human review |

Safety override:

| Condition | Route |
| --- | --- |
| unsafe near-target continuation | abort / human takeover |

## 3. Weak-Label Data Generation

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

## 4. Evidence And Embedding Analysis

The ECG-style part of the project is the analysis-to-routing loop:

| Analysis | Question |
| --- | --- |
| actor or rollout embedding | do the three failure mechanisms separate in representation space? |
| visual-state uncertainty | does visual/depth evidence rise before final failure? |
| action-outcome mismatch | can the system detect that commanded movement is not producing expected progress? |
| KNN / prototype conflict | is the current rollout atypical compared with normal or known mechanism prototypes? |
| composite risk score | can risk alarm earlier than final success/failure? |

Because the teacher's original checkpoint, training data, and hidden
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

## 5. Policy-Side Mechanism Separability Test

The project does include a model-side separability test, with a careful
boundary.

It is not a hidden-layer audit of the teacher's original VPPV model. The
teacher checkpoint, training data, raw hidden activations, and confidence
outputs are not available. Instead, the project uses the closest available
policy-side evidence:

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

> full hidden-layer discovery of failure mechanisms in the teacher's original
> VPPV model.

## 6. Composite Routing

The router is mechanism-specific:

| Mechanism | Route |
| --- | --- |
| `visual_estimation_bias` | re-observe / re-estimate |
| `policy_approach_drift` | low-gain corrective movement / replan |
| `near_target_occlusion_or_servo_failure` | pause / camera reposition / human review |
| unsafe near-target | abort / human takeover |
| normal | continue |

This should be described as compound routing, not retry. A generic retry is
weak because different mechanisms need different interventions.

## 7. Evaluation Metrics

The main metrics should be reliability metrics, not only success rate:

| Metric | Meaning |
| --- | --- |
| mechanism classification accuracy / macro-F1 | whether the system identifies the failure source |
| high-risk failure capture at fixed intervention budget | whether limited review/recovery budget catches important risk |
| residual unsafe failure rate | how much unsafe failure remains after routing |
| route-specific recovery success | whether the selected route works for that mechanism |
| early warning lead time | how early risk is detected before terminal failure |
| false alarm rate on normal rollouts | whether normal behavior is interrupted too often |

## 8. Current Minimal Experiment

The most valuable next experiment is:

```text
SurRoL / VPPV NeedlePick or GauzeRetrieve
  -> generate normal, visual bias, policy drift, near-target failure rollouts
  -> extract state-action-progress behavior features
  -> train a light mechanism classifier and router
  -> evaluate 10-20 seeds with fixed-budget failure capture
```

This experiment is more valuable than another recovery video because it tests
the core claim:

> The system knows when it is unreliable, why it is unreliable, and which
> intervention matches the mechanism.
