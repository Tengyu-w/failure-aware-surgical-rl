# SurRoL Learned Risk Head

## Takeaway

A lightweight logistic risk head was trained from existing SurRoL episode-routing logs to predict whether an episode should be routed to review/abort rather than automatic execution/recovery. This version also includes the unsafe-zone abort proxy, so the head begins to model both visual-state review and geometric abort candidates. It is still best interpreted as reliability-policy distillation, evaluated with an even/odd seed split.

## Held-Out Metrics

| Metric | Value |
|---|---:|
| test_episodes | 158.000 |
| test_review_rate | 0.241 |
| AUROC | 0.986 |
| AUPRC | 0.975 |
| Brier | 0.013 |
| ECE | 0.012 |

## Threshold Routing

| Threshold | Precision | Recall | False Trigger | Auto Coverage | Auto Review Miss | TP | FP | FN | TN |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.20 | 1.000 | 0.947 | 0.000 | 0.772 | 0.016 | 36 | 0 | 2 | 120 |
| 0.40 | 1.000 | 0.947 | 0.000 | 0.772 | 0.016 | 36 | 0 | 2 | 120 |
| 0.60 | 1.000 | 0.947 | 0.000 | 0.772 | 0.016 | 36 | 0 | 2 | 120 |
| 0.80 | 1.000 | 0.947 | 0.000 | 0.772 | 0.016 | 36 | 0 | 2 | 120 |

## Feature Weights

| Feature | Weight |
|---|---:|
| first_perception_uncertain_missing | -1.293 |
| first_grasp_uncertain_missing | -1.173 |
| first_action_anomaly_missing | 0.951 |
| first_review_missing | -0.737 |
| steps | 0.629 |
| recovery_phase_replans | 0.413 |
| final_distance | 0.405 |
| monitor_triggers | 0.287 |
| unsafe_warning_events | -0.132 |
| min_danger_distance | 0.114 |
| recovery_override_rate | 0.085 |
| max_triage_risk | 0.033 |

## Limitations

- The labels come from the current rule-based triage and unsafe-zone outputs, so this is distillation rather than independent ground truth.
- The split is seed-based and small; it is useful for a prototype reliability head but not deployment validation.
- The unsafe-zone evidence is still geometric and task-local, not a true tissue-damage model.