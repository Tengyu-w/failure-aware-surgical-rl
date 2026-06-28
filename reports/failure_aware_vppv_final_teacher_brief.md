# Failure-Aware VPPV Final Teacher Brief

## One-Sentence Contribution

This project adds an ECG-style, mechanism-specific reliability router around the
VPPV surgical-simulation pipeline: instead of treating every failure as "try
again", it separates three VPPV-aligned mechanisms--visual/depth target
estimation bias, policy approach drift, and near-target occlusion or servo
failure--then routes the episode to re-observe, re-estimate, low-gain
correction, human review, or abort/human-takeover behavior.

## What The Project Does Not Claim

- It does not claim a real surgical robot policy trained from clinical data.
- It does not claim that low-level jaw or gripper mechanics are the main learned
  component in VPPV.
- It does not claim hardware, clinical, or real-patient validation.

The useful claim is narrower: in SurRoL/PyBullet-style surgical simulation, the
project tests whether runtime evidence can identify why VPPV-style execution is
becoming unreliable and choose a mechanism-matched correction. Depth-scale
error, action-outcome mismatch, progress loss, and local-neighborhood
instability are evidence channels or subtypes, not extra headline mechanisms.

## Why This Fits The VPPV Pain Point

The relevant VPPV failure is not simply "the gripper opens or closes wrong".
The more important reliability problem is that the visual estimate or
high-level approach target can be wrong, the policy can move toward a biased
position, or the near-target handoff can continue unsafely. A uniform retry is
weak because target-estimation bias, approach drift, and near-target
servo/occlusion failure need different responses.

## Evidence Ladder

| Stage | Key result | What it supports |
|---|---:|---|
| Step-level mechanism evidence | 10823 rows; composite macro-F1=0.998; missed high-risk=0.000 | Multi-evidence routing preserves mechanism identity better than one signal |
| Single-evidence ablation | visual=0.367, depth=0.381, policy=0.355, single-score=0.131 macro-F1 | One generic evidence channel is insufficient |
| Policy-side mechanism separability | PCA/cluster fingerprints from rollout behavior; labels held out until evaluation | Mechanisms are separable enough to support route assignment without direct step-label lookup |
| Cross-task frozen thresholds | NeedlePick->GauzeRetrieve=1.000; GauzeRetrieve->NeedlePick=0.996 macro-F1 | The route logic transfers across two SurRoL tasks |
| Severity holdout | boundary router=1.000; uniform retry=0.167 macro-F1 on high severity | Mechanism boundaries survive a held-out severity shift |
| Offline mixed-priority audit | priority=1.000; max-signal=0.033; uniform=0.000 macro-F1 | Compound faults need priority routing |
| Behavior-derived route assignment | held-out macro-F1=0.995; missed high-risk=0.000; false alarm=0.025 | Route assignment can be derived from rollout behavior regions |
| True mixed SurRoL rollouts | clean=40/40; perturbed=0/40; priority-routed=40/40 success | Route-specific re-estimation restores success in smoke-scale PyBullet rollouts |

## Policy-Side Mechanism Separability

The project does include a model-side test, but it should be described
carefully. It is not a hidden-layer analysis of the teacher's original VPPV
checkpoint. Instead, it uses policy-proxy evidence, action deviation,
action-outcome mismatch, local-neighborhood instability, progress regularity,
and rollout embeddings to ask whether simulator failure mechanisms are
separable before route assignment.

Mechanism labels are not used to form the PCA/clusters. They are used afterward
to evaluate whether the discovered behavior regions align with expected
routes. On held-out episodes this behavior-derived route assignment reaches
accuracy 0.996, macro-F1 0.995, missed high-risk 0.000, and nominal false alarm
0.025.

## Final Result Snapshot

In the true mixed-fault SurRoL smoke run, the perturbed controller fails all
mixed visual/depth/near-target cases (0/40
success, mean final distance 0.224). The
priority-routed controller succeeds in all matched cases
(40/40 success, mean final distance
0.016). This is the strongest current simulation
evidence, but it remains scripted-oracle PyBullet evidence.

## Current Limitations

- Labels and expected routes are weak labels from simulator perturbations and
  routing rules.
- The behavior-derived routing analysis uses policy/rollout behavior features.
  It is not a hidden-layer analysis of the teacher's original VPPV model and is
  still evaluated against simulator weak labels rather than independent expert
  labels.
- The true mixed rollout is a smoke-scale scripted-oracle run, not a deployment
  of a learned VPPV policy.
- The evidence is internal simulation evidence over NeedlePick and
  GauzeRetrieve, not external clinical or hardware validation.
- Visual media and figures demonstrate failure/recovery behavior, but they do
  not prove surgical autonomy.

## Next Strongest Experiments

1. Scale true mixed rollouts beyond the current 5-seed smoke run.
2. Replace the scripted oracle in the true mixed run with the closest available
   learned or teacher-provided VPPV policy path.
3. Add camera/image corruptions and state-estimation perturbations that more
   closely match VPPV's visual module.
4. Report confidence intervals and failure cases, not only success means.
