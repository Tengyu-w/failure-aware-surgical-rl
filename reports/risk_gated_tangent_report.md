# Risk-Gated Tangent Backup for Explainable Safe Surgical RL

## Question
Can a reliability signal decide when the tangent backup controller is necessary, instead of applying safety correction at every timestep?

## Method
1. Build weak timestep risk labels from rollout logs and lightweight navigation rollouts.
2. Train interpretable logistic and depth-3 decision-tree risk models.
3. Use predicted risk to gate tangent backup activation.
4. Compare offline threshold coverage and lightweight online controller behavior.

## Risk Definition
A timestep is weakly labeled high risk when it is close to a forbidden region, has high contact/force proxy, has low remaining budget, stalls while still far from the goal, or belongs to an episode that ultimately fails or exhausts budget.

## Model Metrics
- Rows: 28551 total, 21443 train, 7108 test.
- Split: group_shuffle_by_episode_id.
- Logistic: AUROC=0.923, AUPR=0.993, F1=0.919, false_safe_rate=0.147.
- Decision tree: AUROC=0.949, AUPR=0.995, F1=0.963, false_safe_rate=0.029.

## Strongest Logistic Signals
| feature | coefficient | abs_coefficient |
| --- | --- | --- |
| distance_to_goal | 4.745 | 4.745 |
| action_norm | -1.029 | 1.029 |
| progress_5 | 0.493 | 0.493 |
| normalized_time | 0.388 | 0.388 |
| force_proxy | 0.165 | 0.165 |
| remaining_budget | 0.050 | 0.050 |
| distance_to_forbidden | -0.048 | 0.048 |

## Decision Tree Rules
```text
|--- remaining_budget <= 1.000000
|   |--- distance_to_goal <= 0.357734
|   |   |--- distance_to_goal <= 0.175633
|   |   |   risk_prob=0.320 samples=821 positives=263
|   |   |--- distance_to_goal >  0.175633
|   |   |   risk_prob=0.727 samples=3275 positives=2381
|   |--- distance_to_goal >  0.357734
|   |   |--- action_norm <= 0.000000
|   |   |   risk_prob=1.000 samples=16267 positives=16267
|   |   |--- action_norm >  0.000000
|   |   |   risk_prob=0.926 samples=94 positives=87
|--- remaining_budget >  1.000000
|   |--- progress_5 <= 0.000000
|   |   risk_prob=1.000 samples=107 positives=107
|   |--- progress_5 >  0.000000
|   |   |--- distance_to_forbidden <= 0.103736
|   |   |   risk_prob=0.068 samples=88 positives=6
|   |   |--- distance_to_forbidden >  0.103736
|   |   |   risk_prob=0.000 samples=791 positives=0
```

## Offline Gate Sweep
| threshold | risk_coverage | missed_risk_rate | intervention_rate | activation_reduction_vs_always_gate |
| --- | --- | --- | --- | --- |
| 0.300 | 0.895 | 0.105 | 0.845 | 0.155 |
| 0.400 | 0.870 | 0.130 | 0.813 | 0.187 |
| 0.500 | 0.853 | 0.147 | 0.789 | 0.211 |
| 0.600 | 0.835 | 0.165 | 0.770 | 0.230 |
| 0.700 | 0.799 | 0.201 | 0.737 | 0.263 |

The best threshold under the low-missed-risk then low-intervention ordering was 0.300: it covered 0.895 of weak-label risk states with intervention_rate=0.845.

## Online Smoke Comparison
| method | preset | seed | success_rate | budget_exhaustion_rate | mean_interventions | gate_activation_rate |
| --- | --- | --- | --- | --- | --- | --- |
| unshielded | prototype | 0.000 | 0.100 | 0.900 | 0.000 | 0.000 |
| always_tangent | prototype | 0.000 | 0.120 | 0.000 | 145.880 | 0.000 |
| risk_gated_tangent | prototype | 0.000 | 0.120 | 0.000 | 72.460 | 0.465 |
| unshielded | prototype | 1.000 | 0.090 | 0.890 | 0.000 | 0.000 |
| always_tangent | prototype | 1.000 | 0.120 | 0.000 | 146.800 | 0.000 |
| risk_gated_tangent | prototype | 1.000 | 0.120 | 0.000 | 67.590 | 0.432 |
| unshielded | prototype | 2.000 | 0.060 | 0.930 | 0.000 | 0.000 |
| always_tangent | prototype | 2.000 | 0.080 | 0.000 | 150.790 | 0.000 |
| risk_gated_tangent | prototype | 2.000 | 0.080 | 0.000 | 71.080 | 0.453 |
| unshielded | strict | 0.000 | 0.010 | 0.990 | 0.000 | 0.000 |
| always_tangent | strict | 0.000 | 0.020 | 0.000 | 118.210 | 0.000 |
| risk_gated_tangent | strict | 0.000 | 0.020 | 0.000 | 51.500 | 0.431 |

## Aggregate Result Across Seeds
| method | preset | success_rate | budget_exhaustion_rate | mean_interventions | intervention_rate | mean_tangent_corrections | seeds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| always_tangent | prototype | 0.107 | 0.000 | 147.823 | 1.000 | 67.383 | 3.000 |
| always_tangent | strict | 0.017 | 0.000 | 118.540 | 1.000 | 47.490 | 3.000 |
| risk_gated_tangent | prototype | 0.107 | 0.000 | 70.377 | 0.450 | 67.383 | 3.000 |
| risk_gated_tangent | strict | 0.017 | 0.000 | 50.923 | 0.426 | 47.490 | 3.000 |
| unshielded | prototype | 0.083 | 0.907 | 0.000 | 0.000 | 0.000 | 3.000 |
| unshielded | strict | 0.013 | 0.977 | 0.000 | 0.000 | 0.000 | 3.000 |

## Interpretation
This upgrade turns the tangent backup controller from an always-available correction layer into a risk-gated supervisor. The key evidence is not only task success, but whether the gate preserves coverage of risky states while reducing unnecessary controller activation.

## Limitations
- The labels are weak simulation labels, not clinical or hardware safety ground truth.
- Offline threshold coverage does not prove online causal safety preservation.
- If the held-out split shares similar generators or failure modes with training, external validity remains limited.
- The next ablation should sweep thresholds online across prototype and strict presets with multiple seeds.

## Reusable Claim
I further upgraded the project with an explainable risk-gated supervisor: instead of always activating the backup controller, a lightweight risk model predicts when the policy is entering a risky state and gates the tangent backup controller accordingly. This turns reliability analysis from post-hoc explanation into a runtime decision signal for safer and more efficient surgical RL.
