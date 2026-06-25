# SurRoL Learned Route Classifier

## Takeaway

This step extends the rule/proxy taxonomy into an episode-level learned route classifier. The classifier predicts `auto_execute`, `auto_recovery`, `human_review`, or `abort_candidate` from numeric SurRoL rollout features and is evaluated with an even/odd seed split to reduce episode leakage. It remains a prototype reliability classifier because the labels are distilled from current rule-based routing and simulator logs.

## Held-Out Summary

| Metric | Value |
|---|---:|
| test_episodes | 460.000 |
| accuracy | 0.846 |
| macro_f1 | 0.828 |
| missed_review_or_abort_rate | 0.000 |
| false_review_or_abort_rate | 0.162 |
| mean_confidence | 0.821 |
| human_review_support | 108.000 |
| abort_candidate_support | 7.000 |

## Per-Route Metrics

| Route | Support | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| auto_execute | 234 | 0.951 | 0.987 | 0.969 |
| auto_recovery | 111 | 0.935 | 0.387 | 0.548 |
| human_review | 108 | 0.659 | 1.000 | 0.794 |
| abort_candidate | 7 | 1.000 | 1.000 | 1.000 |
| overall | 460 | 0.846 | 0.846 | 0.828 |

## Highest-Magnitude Feature Weights

| Route | Feature | Weight |
|---|---|---:|
| human_review | steps | 1.344 |
| human_review | visual_reestimate_triggers | 1.148 |
| auto_execute | steps | -1.108 |
| auto_execute | recovery_override_rate | -1.025 |
| auto_execute | visual_reestimate_triggers | -0.808 |
| human_review | recovery_override_rate | 0.766 |
| auto_recovery | success | -0.707 |
| auto_execute | success | 0.592 |
| auto_execute | monitor_triggers | -0.591 |
| abort_candidate | unsafe_abort | 0.554 |
| human_review | min_distance | 0.470 |
| auto_recovery | monitor_triggers | 0.426 |
| auto_recovery | recovery_override_rate | 0.415 |
| auto_execute | final_distance | -0.373 |
| auto_recovery | unsafe_warning_events | 0.369 |
| auto_execute | min_distance | -0.350 |
| auto_recovery | visual_reestimate_triggers | -0.325 |
| auto_execute | risk_event_rate | 0.315 |
| auto_recovery | unsafe_abort | -0.310 |
| auto_execute | distance_reduction | 0.297 |

## Boundary Errors

| Task | Failure | Controller | Seed | True | Pred | Confidence |
|---|---|---|---:|---|---|---:|
| NeedlePick | action_noise | perturbed | 43001 | auto_recovery | human_review | 0.712 |
| NeedlePick | action_noise | perturbed | 43003 | auto_recovery | human_review | 0.716 |
| NeedlePick | action_noise | monitor_corrected | 43001 | auto_recovery | auto_execute | 0.377 |
| NeedlePick | action_dropout | perturbed | 43001 | auto_recovery | human_review | 0.692 |
| NeedlePick | action_dropout | perturbed | 43003 | auto_recovery | human_review | 0.716 |
| NeedlePick | action_dropout | monitor_corrected | 43001 | auto_recovery | human_review | 0.534 |
| NeedlePick | action_dropout | monitor_corrected | 43003 | auto_recovery | human_review | 0.514 |
| NeedlePick | execution_slip | perturbed | 43001 | auto_recovery | human_review | 0.715 |
| NeedlePick | execution_slip | perturbed | 43003 | auto_recovery | human_review | 0.725 |
| NeedlePick | execution_slip | monitor_corrected | 43001 | auto_recovery | human_review | 0.540 |
| NeedlePick | action_noise | perturbed | 43001 | auto_recovery | human_review | 0.722 |
| NeedlePick | action_noise | perturbed | 43003 | auto_recovery | human_review | 0.720 |
| NeedlePick | action_noise | perturbed | 43005 | auto_recovery | human_review | 0.720 |
| NeedlePick | action_noise | perturbed | 43007 | auto_recovery | human_review | 0.732 |
| NeedlePick | action_noise | perturbed | 43009 | auto_recovery | human_review | 0.720 |
| NeedlePick | action_noise | monitor_corrected | 43003 | auto_recovery | human_review | 0.411 |
| NeedlePick | action_noise | monitor_corrected | 43005 | auto_recovery | human_review | 0.502 |
| NeedlePick | action_noise | monitor_corrected | 43009 | auto_recovery | human_review | 0.421 |
| NeedlePick | action_dropout | perturbed | 43001 | auto_recovery | human_review | 0.773 |
| NeedlePick | action_dropout | perturbed | 43003 | auto_recovery | human_review | 0.801 |

## Limitations

- Labels are distilled from the current rule/proxy routing policy, not independent expert annotations.
- The classifier is episode-level; Step 4 should move toward observable online/window-level routing.
- `abort_candidate` remains low-support and geometry-proxy based.
- Features include post-episode quantities such as final distance and success; do not present this as deployable online control yet.
