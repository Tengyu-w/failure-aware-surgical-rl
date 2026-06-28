# Multi-Signal Reliability Upgrade

## Question

Can the surgical RL project move beyond a single embedding/KNN analysis and train ECG-style reliability models from multiple evidence families?

## What Was Added

This upgrade trains and evaluates two lightweight supervisors from existing SurRoL reliability logs:

1. a binary `review_or_abort` risk head;
2. a four-way mechanism router over `auto_execute`, `auto_recovery`, `human_review`, and `abort_candidate`.

The input evidence families are:

- progress and stagnation evidence;
- action anomaly and recovery burden evidence;
- visual/perception uncertainty evidence;
- grasp/contact uncertainty evidence;
- boundary and unsafe-zone evidence;
- representation-proxy evidence from learned review risk and triage scores.

This is intentionally broader than embedding/PCA/KNN alone.

## Binary Review/Abort Head

| Model | AUROC | AUPRC | Recall | FPR | Capture@20% | Capture@30% |
|---|---:|---:|---:|---:|---:|---:|
| handcrafted_multisignal | 1.000 | 1.000 | 0.706 | 0.000 | 0.882 | 1.000 |
| all_multisignal | 1.000 | 1.000 | 0.941 | 0.000 | 0.882 | 1.000 |
| representation_proxy_only | 0.989 | 0.977 | 0.941 | 0.000 | 0.882 | 0.941 |
| visual_only | 0.985 | 0.972 | 0.941 | 0.000 | 0.882 | 0.941 |
| action_only | 0.951 | 0.752 | 1.000 | 0.526 | 0.647 | 1.000 |
| progress_only | 0.889 | 0.658 | 1.000 | 0.158 | 0.412 | 0.765 |
| contact_only | 0.791 | 0.687 | 1.000 | 1.000 | 0.588 | 0.588 |
| boundary_only | 0.562 | 0.244 | 1.000 | 0.930 | 0.059 | 0.059 |

Best AUROC in this held-out split is `handcrafted_multisignal` at 1.000. The all-signal model achieves AUROC 1.000, AUPRC 1.000, and recall 0.941.

![Multi-signal reliability upgrade](figures/multisignal_reliability_upgrade/multisignal_reliability_upgrade.png)

## Mechanism Router

| Metric | Value |
|---|---:|
| accuracy | 0.973 |
| macro-F1 | 0.981 |
| missed review-or-abort rate | 0.000 |
| false review-or-abort rate | 0.000 |
| mean confidence | 0.939 |

Per-route metrics:

| Route | Support | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| auto_execute | 37 | 1.000 | 0.946 | 0.972 |
| auto_recovery | 20 | 0.909 | 1.000 | 0.952 |
| human_review | 16 | 1.000 | 1.000 | 1.000 |
| abort_candidate | 1 | 1.000 | 1.000 | 1.000 |

## Highest-Magnitude Review-Risk Weights

| Feature | Weight | Interpretation family |
|---|---:|---|
| learned_review_risk | 1.208 | visual |
| first_grasp_uncertain_signal | 0.806 | contact |
| first_perception_uncertain_signal | 0.785 | visual |
| steps | 0.568 | progress |
| first_action_anomaly_signal | -0.518 | action |
| final_distance | 0.407 | progress |
| unsafe_abort | 0.384 | boundary |
| recovery_phase_replans | 0.357 | contact |
| monitor_triggers | 0.212 | action |
| unsafe_warning_events | -0.106 | boundary |
| min_distance | 0.101 | progress |
| risk_event_rate | -0.092 | progress |

## Existing Visual And Representation Modules Used As Evidence

| Module | Held-out evidence | Interpretation |
|---|---|---|
| visual action-risk head | AUROC 0.948, AUPRC 0.947, recall 0.842 | Detects high policy-vs-oracle action-gap steps. |
| visual recovery memory | mean action L2 0.227, global mean L2 0.268 | PCA/KNN recovery memory gives a local action suggestion for high-risk visual states. |
| visual denoising adapter | corrupt MSE reduction 0.999 | Clean/corrupt visual-feature pairs support a perception reliability branch. |

## Interpretation

This upgrade makes the RL project closer to the ECG project structurally. The supervisor is no longer described as only embedding/KNN. It uses multiple evidence families, trains a new risk head, trains a mechanism router, reports single-family ablations, and keeps the final claim focused on reliability routing.

## Limitations

- The labels are distilled from simulator logs and injected failures, not expert surgical annotations.
- Some features are episode-level or summary features, so this is a research audit and supervisor prototype rather than a fully deployable online controller.
- The visual modules are lightweight feature-level models, not full surgical scene segmentation or clinical perception validation.
- The evidence is internal simulation evidence only.