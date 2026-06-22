# SurRoL Risk-Aware Intervention Routing

## 一句话结论

这一步把 SurRoL 结果从“检测到异常就恢复”升级为“先判断是否允许自动恢复”。在已有 NeedlePick、GauzeRetrieve、NeedleReach 日志上，动作噪声、dropout、slip、freeze 主要被路由为 `auto_recovery`，而 silent jaw-stuck 这类夹爪结果不确定的失败被路由为 `human_review`。这更接近 ECG 项目里的自动放行/复查/人工分流逻辑。

## 路由定义

| Route | 含义 | 当前触发依据 |
|---|---|---|
| `auto_execute` | 低风险正常执行 | nominal episode 且无明显风险报警 |
| `auto_recovery` | 可逆异常，允许短窗自动恢复 | action anomaly、clip、monitor trigger，但没有视觉状态或夹爪结果不确定信号 |
| `human_review` | 不应盲目恢复，需要暂停/复核 | 视觉/深度状态估计不确定，或多次闭合夹爪后目标距离仍远、停滞或无进展 |
| `abort_candidate` | 中止候选 | 持续高风险、长时间无进展且距离仍远；当前日志里主要作为规则预留 |

## 路由计数

| Route | Episodes |
|---|---:|
| auto_execute | 175 |
| auto_recovery | 90 |
| human_review | 80 |
| abort_candidate | 0 |

## 关键故障分流结果

| Suite | Task | Failure | Controller | Route | Episodes | Success | Mean Risk | First Review Step |
|---|---|---|---|---|---:|---:|---:|---:|
| observable_jaw_stuck_10seed | GauzeRetrieve | jaw_stuck_open | monitor_corrected | human_review | 10 | 1.000 | 3.750 | 30.000 |
| observable_jaw_stuck_10seed | GauzeRetrieve | jaw_stuck_open | perturbed | human_review | 10 | 0.000 | 3.750 | 30.000 |
| observable_jaw_stuck_10seed | NeedlePick | jaw_stuck_open | monitor_corrected | human_review | 10 | 1.000 | 3.750 | 34.700 |
| observable_jaw_stuck_10seed | NeedlePick | jaw_stuck_open | perturbed | human_review | 10 | 0.000 | 3.750 | 34.700 |
| standard_corruptions | GauzeRetrieve | action_dropout | monitor_corrected | auto_recovery | 5 | 1.000 | 2.725 |  |
| standard_corruptions | GauzeRetrieve | action_dropout | perturbed | auto_recovery | 5 | 0.000 | 3.250 | 36.400 |
| standard_corruptions | GauzeRetrieve | action_noise | monitor_corrected | auto_recovery | 5 | 1.000 | 2.500 |  |
| standard_corruptions | GauzeRetrieve | action_noise | perturbed | auto_recovery | 5 | 0.000 | 3.250 | 30.600 |
| standard_corruptions | GauzeRetrieve | execution_slip | monitor_corrected | auto_recovery | 5 | 1.000 | 2.500 |  |
| standard_corruptions | GauzeRetrieve | execution_slip | perturbed | auto_recovery | 5 | 0.000 | 3.250 | 46.400 |
| standard_corruptions | NeedlePick | action_dropout | monitor_corrected | auto_recovery | 5 | 1.000 | 2.819 |  |
| standard_corruptions | NeedlePick | action_dropout | perturbed | auto_recovery | 5 | 0.000 | 3.250 | 32.400 |
| standard_corruptions | NeedlePick | action_noise | monitor_corrected | auto_recovery | 5 | 1.000 | 2.594 |  |
| standard_corruptions | NeedlePick | action_noise | perturbed | auto_recovery | 5 | 0.000 | 3.250 | 32.000 |
| standard_corruptions | NeedlePick | execution_slip | monitor_corrected | auto_recovery | 5 | 1.000 | 2.594 |  |
| standard_corruptions | NeedlePick | execution_slip | perturbed | auto_recovery | 5 | 0.000 | 3.250 | 32.000 |
| third_task_reach_freeze | NeedleReach | action_freeze | monitor_corrected | auto_recovery | 5 | 1.000 | 2.594 |  |
| third_task_reach_freeze | NeedleReach | action_freeze | perturbed | auto_recovery | 5 | 0.000 | 3.250 | 30.000 |
| visual_state_drift_5seed | GauzeRetrieve | depth_scale_error | monitor_corrected | human_review | 5 | 0.000 | 3.250 | 30.000 |
| visual_state_drift_5seed | GauzeRetrieve | depth_scale_error | perturbed | human_review | 5 | 0.000 | 3.250 | 30.000 |
| visual_state_drift_5seed | GauzeRetrieve | near_target_drift | monitor_corrected | auto_recovery | 5 | 1.000 | 3.000 |  |
| visual_state_drift_5seed | GauzeRetrieve | near_target_drift | perturbed | auto_recovery | 5 | 0.000 | 3.000 |  |
| visual_state_drift_5seed | GauzeRetrieve | perception_bias | monitor_corrected | human_review | 5 | 0.000 | 4.750 | 30.000 |
| visual_state_drift_5seed | GauzeRetrieve | perception_bias | perturbed | human_review | 5 | 0.000 | 4.750 | 30.000 |
| visual_state_drift_5seed | NeedlePick | depth_scale_error | monitor_corrected | human_review | 5 | 0.000 | 3.250 | 53.250 |
| visual_state_drift_5seed | NeedlePick | depth_scale_error | perturbed | human_review | 5 | 0.000 | 3.250 | 54.400 |
| visual_state_drift_5seed | NeedlePick | near_target_drift | monitor_corrected | auto_recovery | 5 | 1.000 | 2.250 |  |
| visual_state_drift_5seed | NeedlePick | near_target_drift | perturbed | auto_recovery | 5 | 0.200 | 2.250 |  |
| visual_state_drift_5seed | NeedlePick | perception_bias | monitor_corrected | human_review | 5 | 0.000 | 3.250 | 33.000 |
| visual_state_drift_5seed | NeedlePick | perception_bias | perturbed | human_review | 5 | 0.000 | 3.250 | 33.000 |

## Nominal Specificity Check

| Task | Controller | Route | Episodes | Success | Mean Risk |
|---|---|---|---:|---:|---:|
| GauzeRetrieve | monitor_corrected | auto_execute | 10 | 1.000 | 3.009 |
| NeedlePick | monitor_corrected | auto_execute | 10 | 1.000 | 2.250 |
| GauzeRetrieve | monitor_corrected | auto_execute | 5 | 1.000 | 2.250 |
| NeedlePick | monitor_corrected | auto_execute | 5 | 1.000 | 2.250 |
| NeedleReach | monitor_corrected | auto_execute | 5 | 1.000 | 1.500 |
| GauzeRetrieve | monitor_corrected | auto_execute | 5 | 1.000 | 3.000 |
| NeedlePick | monitor_corrected | auto_execute | 5 | 1.000 | 2.250 |

## 研究解释

- 现在可以更准确地说：SurRoL 原型已经有了风险分流雏形，而不只是 recovery demo。
- `auto_recovery` 对应低后果、可逆的执行异常；`human_review` 对应夹爪结果不确定、盲目 retry 可能不合理的异常。
- 新增 perception-state 代理后，视觉/深度/状态估计错误会优先进入 `human_review`，near-target drift 才进入 `auto_recovery`。
- 当前 `abort_candidate` 仍是代理规则，因为 SurRoL 日志还没有真实组织损伤、力反馈或 forbidden-zone 接触证据。

## 局限

- 这是离线重放已有日志，不是在线中止控制。
- 风险分数是规则型 proxy，不是 learned uncertainty/risk head。
- 还没有视觉、力觉或组织危险区，所以不能宣称检测到了真实手术损伤风险。

## 输出文件

- `reports/tables/surrol_risk_triage_episode_routes.csv`
- `reports/tables/surrol_risk_triage_summary.csv`
- `reports/tables/surrol_risk_triage_scored_steps.csv`
- `reports/figures/surrol_risk_triage/surrol_risk_triage_routes.png`