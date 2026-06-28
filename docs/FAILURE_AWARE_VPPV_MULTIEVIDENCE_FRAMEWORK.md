# Failure-Aware VPPV Multi-Evidence Framework

This document replaces the earlier "generic recovery demo" framing with a
VPPV-specific reliability question.

The target system is not a raw image-to-action VLA and not a gripper-learning
problem. In the Science Robotics VPPV pipeline, the key chain is:

```text
endoscopic image
  -> visual parsing: segmentation and depth
  -> perceptual regressor: visual state to low-dimensional physical state
  -> DDPG policy: state to high-level continuous approach action
  -> visual servoing or classic control: final precise manipulation
  -> robot execution
```

The project contribution should therefore be stated as:

> Reliability supervision for the VPPV perception-policy-servoing loop:
> detect when visual state estimation or high-level approach policy becomes
> unreliable, attribute the likely failure mechanism, and route the system to
> re-observation, re-estimation, corrective approach, human review, or abort.

It should not be stated as:

> Learning surgical grasping from scratch or fixing gripper mechanics.

## Step 1: Revised Research Problem

VPPV succeeds because it avoids raw image-to-action learning. It first converts
complex surgical images into a physical state representation, then uses a DDPG
policy to move the instrument toward the task target, with final manipulation
handled by visual servoing or classic control.

This creates a different reliability problem:

```text
If visual state estimation is wrong, the policy can move correctly toward the
wrong target.

If the approach policy drifts, the robot can arrive at the wrong near-target
region even when the visual state appears plausible.

If the handoff to visual servoing fails near the target, the system may keep
executing while occlusion, depth error, or contact deformation makes the final
step unreliable.
```

The research question becomes:

> Can multi-evidence reliability signals identify whether a VPPV failure comes
> from visual state estimation, high-level approach policy, or near-target
> servoing/contact handoff, and route each mechanism to the correct response
> before unsafe continuation?

## Step 2: Core Failure Mechanisms

The first version should use a small number of mechanisms that match the VPPV
pipeline. These mechanisms are more important than jaw-stuck or object-drop
examples, because they are closer to the paper's real bottleneck.

| Mechanism | Failure source | Typical symptom | Route |
| --- | --- | --- | --- |
| `visual_estimation_bias` | segmentation, depth, or perceptual regressor gives a biased target/contact state | action looks reasonable, but progress is toward the wrong state | `reobserve_reestimate` |
| `depth_scale_error` | depth estimate has a systematic z-axis or scale error | near-target approach is vertically wrong or oscillatory | `depth_reestimate_or_cautious_approach` |
| `segmentation_dropout_occlusion` | target mask becomes unstable or disappears near the tool | target state jumps, confidence collapses, progress stalls | `pause_reobserve_or_camera_reposition` |
| `policy_approach_drift` | DDPG actor maps a plausible state to a poor approach action | action direction and observed progress disagree | `low_gain_correction_or_replan` |
| `handoff_servo_failure` | final visual servoing or classic controller cannot complete manipulation | repeated near-target commands do not change outcome | `human_review_or_servo_reset` |
| `unsafe_near_target_continuation` | recovery or approach enters a forbidden/danger region near target | risk rises while the policy continues | `abort_candidate_or_takeover` |

The first three mechanisms are perception-side. The fourth is policy-side. The
last two are handoff and safety-side.

## Step 3: Multi-Evidence Analysis Families

The ECG project was not only an embedding study. The VPPV project should follow
the same style: multiple evidence families, each asking a different reliability
question.

| Evidence family | VPPV signal | Reliability question | Expected use |
| --- | --- | --- | --- |
| Policy embedding geometry | DDPG actor hidden layer, action-head representation, or proxy policy feature | Does the policy representation enter a failure-prone region before the final outcome fails? | early policy-risk signal |
| State-estimation uncertainty | mask area, mask dropout, depth variance, regressor residual, target-state jump, multi-view disagreement | Is the visual state estimate trustworthy? | perception mechanism evidence |
| Action-outcome mismatch | predicted movement vs observed movement, progress slope, distance change after action | Did the action produce the expected transition? | transition failure evidence |
| Local trajectory neighborhood | KNN purity, prototype distance, local mechanism mixture, nearest failed transitions | Does this transition resemble known failures more than nominal approaches? | mechanism attribution |
| Progress regularity | stalling, oscillation, overshoot, repeated action, near-target non-improvement | Is the rollout stuck or unstable despite continued commands? | handoff and servoing evidence |
| Perturbation sensitivity | visual bias sweep, depth scale sweep, mask dropout, approach drift, unsafe-zone perturbation | Which mechanism causes failure under controlled stress? | causal stress-test evidence |
| Budgeted risk and routing | review rate, intervention budget, residual unsafe failure, missed review/abort | Does the router capture important failures under limited intervention budget? | final decision evidence |

This makes the project a multi-evidence reliability framework, not an embedding
visualization project.

## Step 4: Analysis Program

The analysis should be staged so that each result has a clear role.

### 4.1 Single-Evidence Audit

For each evidence family, measure whether it captures each mechanism:

```text
evidence signal -> mechanism label
evidence signal -> high-risk failure label
evidence signal -> early warning before terminal failure
```

Recommended metrics:

- AUROC or average precision for high-risk failure capture.
- Top-k or fixed-budget capture rate.
- False alarm rate on nominal rollouts.
- Early-warning lead time.
- Mechanism-wise recall, not only global accuracy.

### 4.2 Mechanism Fingerprint Analysis

Each mechanism should have a different evidence fingerprint.

| Mechanism | Expected primary evidence | Expected secondary evidence |
| --- | --- | --- |
| `visual_estimation_bias` | state-estimation uncertainty or state jump | action-outcome mismatch after policy follows wrong state |
| `depth_scale_error` | depth residual or z-axis error | near-target oscillation |
| `segmentation_dropout_occlusion` | mask dropout and target disappearance | progress stall |
| `policy_approach_drift` | policy embedding atypicality | action-outcome mismatch |
| `handoff_servo_failure` | progress regularity failure near target | repeated action without outcome change |
| `unsafe_near_target_continuation` | boundary or danger-zone risk | route continues despite rising risk |

The intended claim is not that any one signal is perfect. The intended claim is
that failure mechanisms have separable multi-signal profiles.

### 4.3 Composite Router

The router should not collapse everything into one generic retry rule.

```text
Stage 1: irreversible or boundary risk
  -> abort_candidate or human takeover

Stage 2: visual-state reliability
  -> reobserve_reestimate

Stage 3: policy approach reliability
  -> low_gain_correction_or_replan

Stage 4: near-target handoff reliability
  -> servo reset, camera reposition, or human review

Stage 5: low-risk nominal state
  -> continue
```

This follows the ECG-style idea that high-risk boundary cases should be handled
before residual mechanisms, and that residual mechanisms need their own
reserved budget.

### 4.4 Comparators

The composite router should be compared against simpler baselines:

| Baseline | What it tests |
| --- | --- |
| Always continue | Whether risk supervision is needed at all |
| Uniform retry | Whether mechanism-specific routing beats "try again" |
| Single risk score | Whether multi-mechanism routing beats one scalar threshold |
| Embedding-only classifier | Whether embedding alone is enough |
| Visual-uncertainty-only gate | Whether perception signals alone are enough |
| Oracle mechanism labels | Upper-bound routing sanity check |

### 4.5 Final Metrics

Report decision quality, not just task success:

- Mechanism classification accuracy and macro-F1.
- High-risk failure capture at fixed review/intervention budget.
- Residual unsafe failure rate on the automatic path.
- Route-specific success after intervention.
- Missed `human_review` or `abort_candidate` cases.
- Early-warning lead time before terminal failure.
- Evidence-family ablation: single-family vs multi-signal router.

## Step 5: Minimal Experiment Order

The first executable version should not try to cover every surgical task.

1. Use NeedlePick or GauzeRetrieve as the first task.
2. Generate nominal, visual bias, depth error, and policy drift rollouts.
3. Log state, action, achieved goal, desired goal, progress, target estimate,
   and route labels at each step.
4. Compute all evidence families offline.
5. Train or score a mechanism classifier and composite router.
6. Report single-evidence audit, mechanism fingerprint table, and composite
   routing under a fixed intervention budget.

Only after this should the project add object-drop, jaw-stuck, or broader
task-specific videos.

## Step 6: Claim Boundary

Allowed claim:

> The project builds a simulator evidence layer around VPPV-style surgical
> autonomy and shows how multi-evidence reliability signals can classify
> visual, policy, handoff, and unsafe-continuation mechanisms for route-specific
> intervention.

Avoided claim:

> The project learns a new surgical manipulation policy or proves clinical
> surgical safety.

