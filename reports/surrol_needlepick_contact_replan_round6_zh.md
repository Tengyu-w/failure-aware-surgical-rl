# SurRoL 正式实验 Round 6：Contact-Aware Replanning Recovery

## 一句话结论

基于 Round 5 的失败 seed 诊断，我们发现 `action_dropout` 和部分 `execution_slip` 的失败不是因为 monitor 没触发，而是因为 NeedlePick 的 waypoint 流程已经走完，但夹爪没有保持激活、接触约束也没有建立。为此加入 `contact_replan`：当所有 waypoint 被消费完、任务仍未成功、且没有有效抓取/约束时，重建 NeedlePick waypoints 并继续恢复。结果在 5 seed 下把三类扰动全部恢复到 5/5。

## 实验文件

- Contact-aware episode CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_contact_replan_w32_5seed.csv`
- Contact-aware step CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_contact_replan_w32_5seed_steps.csv`
- 对比汇总 CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_contact_replan_comparison_5seed_summary.csv`
- 诊断 CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_phase_diagnostics_summary.csv`
- 脚本：`E:\RL_projects\constraint_surgical_rl\scripts\run_surrol_monitor_recovery.ps1`
- 诊断脚本：`E:\RL_projects\constraint_surgical_rl\scripts\run_surrol_phase_diagnostics.ps1`

## 失败诊断发现

失败 episode 的共同模式：

- `active_waypoint = -1`：所有 waypoint 都已经被消费；
- `activated = -1`：夹爪没有保持激活；
- `contact_constraint = 0`：没有有效抓取约束；
- 任务曾经接近目标，但随后退回较大距离。

这说明失败瓶颈不是“风险没检测到”，而是“恢复策略没有理解任务阶段和接触状态”。因此单纯延长 oracle override window 不够，需要 contact-aware replanning。

## 5 Seed 对比结果

| Recovery Policy | Failure | Perturbed Success | Monitor Success | Final Distance | Mean Triggers | Mean Replans | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|
| oracle_override | action_noise | 0/5 | 5/5 | 0.0201 | 2.00 | 0.00 | 40.0 |
| oracle_override | action_dropout | 0/5 | 1/5 | 0.1308 | 5.80 | 0.00 | 169.0 |
| oracle_override | execution_slip | 0/5 | 3/5 | 0.0746 | 4.00 | 0.00 | 106.0 |
| contact_replan | action_noise | 0/5 | 5/5 | 0.0201 | 2.00 | 0.00 | 40.0 |
| contact_replan | action_dropout | 0/5 | 5/5 | 0.0216 | 2.80 | 0.80 | 74.2 |
| contact_replan | execution_slip | 0/5 | 5/5 | 0.0202 | 2.40 | 0.40 | 58.0 |

Nominal case remains stable:

| Recovery Policy | Failure | Monitor Success | Mean Triggers | Mean Replans |
|---|---|---:|---:|---:|
| oracle_override | none | 5/5 | 1.00 | 0.00 |
| contact_replan | none | 5/5 | 1.00 | 0.00 |

## 解释

- `contact_replan` 没有改变 `action_noise` 结果，因为 action_noise 已经可以被普通 oracle override 完全恢复。
- `contact_replan` 显著改善 `action_dropout`，从 1/5 提升到 5/5。
- `contact_replan` 也改善 `execution_slip`，从 3/5 提升到 5/5。
- 平均 replan 次数很低：dropout 0.80，slip 0.40，说明不是靠频繁重置硬推成功。
- 这验证了 phase/contact-aware recovery 的价值：不同 failure type 需要不同恢复动作。

## 当前可支撑的更强说法

可以把项目表述升级为：

> In a 5-seed SurRoL NeedlePick pilot, clean execution succeeds and action-corrupted execution fails under action noise, dropout, and execution slip. A runtime recovery layer with contact-aware replanning restores all three corrupted settings from 0/5 perturbed success to 5/5 monitor-corrected success, while preserving nominal success. The result suggests that failure-aware surgical autonomy benefits from task-phase and contact-state-aware recovery, not merely generic action correction.

## 仍需谨慎的限制

- 仍然是 5 seed pilot，不是最终统计结论。
- Recovery 仍然依赖 SurRoL oracle / waypoint structure，不是 learned policy。
- Contact-aware rule 使用了任务内部状态，后续需要转成可观测或可学习的 risk/recovery signal。
- 当前只在 NeedlePick 上完成完整闭环，仍需扩展到 GauzeRetrieve / NeedleRegrasp / PegTransfer。

## 下一步

1. 把 contact-aware recovery 拆成更通用的 phase-aware policy：approach、grasp、lift 各自有不同恢复逻辑。
2. 把内部状态规则替换为可观测信号：contact proxy、jaw state、tool-object distance、object-goal residual。
3. 在第二个 SurRoL 任务上复现同样流程，优先考虑 `GauzeRetrieve` 或 `NeedleRegrasp`。
4. 做 10 seed 复跑，并报告 confidence interval / seed variance。
