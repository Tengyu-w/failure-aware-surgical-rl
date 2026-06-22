# SurRoL 正式实验 Round 2b：NeedlePick Monitor Trade-Off

## 一句话结论

`NeedlePick` 的 monitor 实验已经显示出一个真实的安全学习问题：粗 monitor 可以强力恢复 `action_noise`，但 nominal 场景误触发较多；goal-aware monitor 可以把 nominal false trigger 降到 0，但恢复能力下降。也就是说，下一步不是简单证明“加 monitor 就好”，而是要研究 precision-recall trade-off：什么时候该介入，介入多久，如何避免正常 waypoint 阶段被误判为风险。

## 对比文件

- 粗 monitor episode CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_monitor_recovery.csv`
- 粗 monitor step CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_monitor_recovery_steps.csv`
- goal-aware monitor episode CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_monitor_recovery_goalaware.csv`
- goal-aware monitor step CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_monitor_recovery_goalaware_steps.csv`
- 脚本：`E:\RL_projects\constraint_surgical_rl\scripts\run_surrol_monitor_recovery.ps1`

## 核心表

| Monitor | Failure | Perturbed Success | Monitor Success | Monitor Final Distance | Nominal False Trigger |
|---|---|---:|---:|---:|---:|
| coarse | action_noise | 0.000 | 1.000 | 0.0187 | 4.00 |
| coarse | action_dropout | 0.000 | 0.333 | 0.1125 | 4.00 |
| coarse | execution_slip | 0.000 | 0.333 | 0.1112 | 4.00 |
| goal-aware | action_noise | 0.000 | 0.333 | 0.1558 | 0.00 |
| goal-aware | action_dropout | 0.000 | 0.000 | 0.1893 | 0.00 |
| goal-aware | execution_slip | 0.000 | 0.000 | 0.1903 | 0.00 |

## 解释

- `NeedlePick` 的扰动确实有破坏性：三类 failure 的 perturbed success 都是 0。
- 粗 monitor 的恢复能力最强，尤其 `action_noise` 从 0/3 恢复到 3/3。
- 粗 monitor 的问题是 nominal 下也平均触发 4 次，说明它把正常 waypoint 阶段的停滞/回退当成风险。
- goal-aware monitor 消除了 nominal false trigger，但也错过了需要早介入的风险，导致恢复能力下降。
- 这说明风险触发不能只靠单一步进距离规则，需要结合任务阶段、oracle waypoint、动作异常和接触状态。

## 研究价值

这组结果比“全成功”更有博士课题价值。它明确提出了一个可研究问题：

> 在手术机器人任务中，如何设计 failure-aware monitor，使它既能及时从动作扰动中恢复，又不会误判正常多阶段操作过程？

这可以自然扩展成：

- selective recovery
- calibrated risk score
- phase-aware uncertainty
- intervention budget
- false intervention vs missed failure trade-off

## 下一步实验

1. 加 task phase 特征：approach、grasp、lift/transfer，不同阶段用不同 trigger。
2. 做 recovery window sweep：4、8、16、32 steps，找恢复能力和误触发的平衡点。
3. 把 monitor trigger 拆成多个信号：action anomaly、distance regression、clip、contact loss，分别报告贡献。
4. 从 step CSV 画曲线：distance、trigger、override、action deviation，挑成功和失败 seed 对比。
