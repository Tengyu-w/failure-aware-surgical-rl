# SurRoL Risk-Level Calibration

## 一句话结论

这一步把原来的 recovery/abort 二分思路改成四档风险路由：auto_execute、auto_recovery、human_review、abort_candidate。它更接近 ECG 项目里的分级处理逻辑：低风险自动执行，可恢复漂移自动恢复，视觉/状态不确定交给复查，接近 forbidden zone 或 unsafe abort 的片段进入候选中止。

## Risk-Level Summary

| Risk level | Episodes | Success | Unsafe abort | Final distance |
|---|---:|---:|---:|---:|
| abort_candidate | 16 | 0.312 | 0.438 | 0.069 |
| auto_execute | 86 | 1.000 | 0.000 | 0.018 |
| auto_recovery | 60 | 0.600 | 0.000 | 0.086 |
| human_review | 36 | 0.278 | 0.000 | 0.171 |

## Leakage Control

Risk-level assignment does not use the ground-truth route or family labels. Those labels are kept only for post-hoc evaluation tables. The routing evidence comes from predicted memory labels, embedding distances, learned risk score, monitor triggers, unsafe-warning counts, and proximity to the forbidden-zone proxy.

## Interpretation

- auto_execute is the low-risk route for nominal or clean-looking execution.
- auto_recovery is used when the memory says the episode resembles recoverable execution drift.
- human_review is used for visual-state error or high memory uncertainty, matching the review/re-estimation branch.
- abort_candidate is intentionally conservative: it prioritizes not missing unsafe-abort-like states, even at the cost of false alarms.

## Limitations

- The current score is a transparent calibration rule over logs, not a validated clinical safety model.
- Unsafe-zone labels still come from a geometric forbidden-zone proxy, not tissue force or deformation.
- Learned risk scores are merged when available, but the present routing still relies heavily on synthetic labels and simulator state features.

## Outputs

- `reports/tables/surrol_risk_level_scored.csv`
- `reports/tables/surrol_risk_level_summary.csv`
- `reports/tables/surrol_risk_level_by_original_route.csv`