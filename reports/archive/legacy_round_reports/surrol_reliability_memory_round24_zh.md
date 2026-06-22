# SurRoL External Reliability Memory Prototype

## 一句话结论

这一步把已有 SurRoL episode 日志编码成 reliability embedding，并用最简单的 nearest-prototype memory 做错误类型和路由预测。它是 RAM 思路的可靠性版本雏形：不是检索物体该怎么操作，而是检索当前执行片段像不像历史上的 visual-state error、execution drift、grasp uncertainty 或 unsafe abort。

## Label Definition

本轮修正了一个重要细节：clean controller 且成功、无 unsafe abort、路由为 auto_execute 的 episode 被标为 nominal。也就是说，failure family 现在更接近“实际观测到的风险状态”，而不是简单继承实验套件里的注入故障名。

## Held-Out Prototype Accuracy

| Prediction | Accuracy |
|---|---:|
| Failure family | 0.909 |
| Route | 0.909 |

## Failure-Family Metrics

| Family | Support | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| execution_drift | 61 | 0.957 | 0.738 | 0.833 |
| grasp_outcome_uncertain | 20 | 1.000 | 1.000 | 1.000 |
| nominal | 94 | 0.920 | 0.979 | 0.948 |
| unsafe_abort | 7 | 0.467 | 1.000 | 0.636 |
| visual_state_error | 16 | 1.000 | 1.000 | 1.000 |

## Route Metrics

| Route | Support | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| abort_candidate | 5 | 0.385 | 1.000 | 0.556 |
| auto_execute | 96 | 0.920 | 0.958 | 0.939 |
| auto_recovery | 61 | 0.959 | 0.770 | 0.855 |
| human_review | 36 | 1.000 | 1.000 | 1.000 |

## Interpretation

- This is the first external reliability-memory layer: episode features are embedded, then classified by distance to historical prototypes.
- If error classes cluster in embedding space, it supports the ECG-style argument that mixed/overlapping regions are reliability-risk regions.
- The prototype is intentionally simple; it is a baseline before trying learned encoders, sequence windows, or image-derived features.

## Limitations

- Current embeddings are based on simulator state/log features, not real visual embeddings.
- The labels partly come from synthetic injected failures and rule-based routing.
- Unsafe-zone evidence is still task-local and geometric, not a real tissue-damage model.

## Outputs

- `reports/tables/surrol_reliability_memory_embeddings.csv`
- `reports/tables/surrol_reliability_memory_predictions.csv`
- `reports/tables/surrol_reliability_memory_metrics.csv`
- `reports/tables/surrol_reliability_memory_confusion.csv`
- `reports/figures/surrol_reliability_memory/embedding_by_family.png`
- `reports/figures/surrol_reliability_memory/embedding_by_route.png`