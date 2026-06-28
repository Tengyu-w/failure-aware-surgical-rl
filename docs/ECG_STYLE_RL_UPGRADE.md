# ECG-Style RL Reliability Upgrade

This document explains the real method transfer from the ECG reliability
project into the surgical RL project.

The transfer is not "do embedding only." The ECG project used broad evidence:
embedding geometry, uncertainty, calibration, signal regularity, OOD
perturbations, structured model interventions, risk distillation, and
mechanism routing. The RL project now mirrors that logic with surgical
simulation signals.

## What Was Added

Two scripts implement the upgrade:

- `scripts/run_multisignal_reliability_upgrade.py`
- `scripts/run_ecg_style_rl_reliability_suite.py`

They train and evaluate:

1. a multi-signal `review_or_abort` risk head;
2. a four-way mechanism router:
   `auto_execute`, `auto_recovery`, `human_review`, `abort_candidate`;
3. ECG-style diagnostics for representation, uncertainty, trajectory
   structure, perturbation robustness, and mechanism routing.

## ECG Methods Mapped Into RL

| ECG method family | RL counterpart |
| --- | --- |
| PCA / centroid / silhouette / prototype / kNN | multi-signal feature-space PCA, route centroid distance, normalized centroid distance, silhouette, Davies-Bouldin, prototype route ambiguity, kNN entropy, local purity |
| MSP / entropy / margin / calibration | route probability MSP, entropy, inverse margin, review-risk score, route-error AUROC |
| signal regularity | trajectory progress, stagnation, final distance, monitor triggers, recovery replans, contact uncertainty, boundary/unsafe signals |
| OOD / corruption | injected action noise/dropout/slip, perception bias, depth error, jaw-stuck, near-target drift |
| model intervention | multi-signal risk head, visual action-risk head, visual denoising adapter, recovery memory, risk-aware PPO pilot |
| RISK / v5d router | multi-signal review score plus mechanism router |

## Key Results

Representation and kNN diagnostics:

| Metric | Value |
| --- | ---: |
| silhouette | 0.412 |
| Davies-Bouldin | 1.368 |
| mean KNN label entropy | 0.034 |
| mean local purity | 0.969 |
| KNN route conflict rate | 0.019 |

Decision uncertainty:

| Score | Route-error AUROC | Review/abort AUROC |
| --- | ---: | ---: |
| MSP | 0.993 | 0.079 |
| entropy | 0.993 | 0.089 |
| inverse margin | 0.993 | 0.065 |
| review score | 0.118 | 1.000 |

Interpretation: normal route softmax uncertainty catches route-classifier
mistakes, but it does not identify review/abort states. A separate
multi-signal review-risk head is needed.

Model intervention:

| Model | Review/abort AUROC | AUPRC | Recall | FPR |
| --- | ---: | ---: | ---: | ---: |
| handcrafted multi-signal | 1.000 | 1.000 | 0.706 | 0.000 |
| all multi-signal | 1.000 | 1.000 | 0.941 | 0.000 |
| representation-proxy only | 0.989 | 0.977 | 0.941 | 0.000 |
| visual only | 0.985 | 0.972 | 0.941 | 0.000 |
| action only | 0.951 | 0.752 | 1.000 | 0.526 |
| progress only | 0.889 | 0.658 | 1.000 | 0.158 |

Mechanism router:

| Metric | Value |
| --- | ---: |
| accuracy | 0.973 |
| macro-F1 | 0.981 |
| missed review-or-abort rate | 0.000 |
| false review-or-abort rate | 0.000 |

## What This Means

The RL project now follows the ECG logic:

```text
broad failure analysis
  -> multi-signal reliability model
  -> model-side intervention / risk-head training
  -> if policy improvement is limited, use mechanism routing and recovery
```

The current evidence suggests that improving the RL policy alone is not the
strongest claim. The stronger claim is a reliability-supervised policy:
normal execution when evidence is safe, automatic recovery for reversible
drift, human-review routing for visual/contact uncertainty, and abort-candidate
routing for unsafe recovery.

## Limitations

- Labels are weak/proxy labels from simulator logs and injected failures.
- Some features are episode-level summaries, so this is not yet a fully online
  controller.
- `abort_candidate` support is small.
- The result is internal simulation evidence, not clinical or real-robot
  validation.
