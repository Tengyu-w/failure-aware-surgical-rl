# SurRoL 正式实验 Round 4：NeedlePick Cross-Failure Recovery

## 一句话结论

把 Round 3 选出的强 baseline `coarse + 16/32 recovery window` 扩展到更难故障后，结果显示：monitor 对不同 failure 的恢复能力明显不同。`action_noise` 可稳定从 0/3 恢复到 3/3；`execution_slip` 可恢复到 2/3；`action_dropout` 只能恢复到 1/3。窗口从 16 增加到 32 主要减少触发次数，成功率没有变化。

## 实验文件

- 汇总 CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_coarse_cross_failure_summary.csv`
- w16 hard failures：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_harder_failures_coarse_w16.csv`
- w32 hard failures：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_harder_failures_coarse_w32.csv`
- step-level CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_harder_failures_coarse_w16_steps.csv`
- step-level CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_harder_failures_coarse_w32_steps.csv`

## 实验设置

- Task：SurRoL `NeedlePick`
- Trigger mode：`coarse`
- Recovery windows：16、32 steps
- Seeds：3
- Failures：`action_noise`、`action_dropout`、`execution_slip`
- Baseline：对应 failure 的 `perturbed` controller
- Proposed：`monitor_corrected`

## 核心结果

| Window | Failure | Perturbed Success | Monitor Success | Monitor Final Distance | Monitor Triggers | Override Rate | Mean Steps |
|---:|---|---:|---:|---:|---:|---:|---:|
| 16 | none | N/A | 1.000 | 0.0214 | 2.00 | 0.783 | 40.7 |
| 16 | action_noise | 0.000 | 1.000 | 0.0192 | 3.00 | 0.966 | 41.0 |
| 16 | action_dropout | 0.000 | 0.333 | 0.1125 | 9.33 | 0.960 | 148.3 |
| 16 | execution_slip | 0.000 | 0.667 | 0.0657 | 6.33 | 0.977 | 96.0 |
| 32 | none | N/A | 1.000 | 0.0214 | 1.00 | 0.783 | 40.7 |
| 32 | action_noise | 0.000 | 1.000 | 0.0192 | 2.00 | 0.966 | 41.0 |
| 32 | action_dropout | 0.000 | 0.333 | 0.1125 | 5.00 | 0.960 | 148.3 |
| 32 | execution_slip | 0.000 | 0.667 | 0.0657 | 3.67 | 0.977 | 96.0 |

## 解释

- `action_noise` 是最容易被当前 monitor 恢复的故障；只要触发后切回 oracle，就能稳定完成。
- `execution_slip` 是中等难度；monitor 能救回 2/3，说明它不是完全失效，但仍存在 seed-level failure。
- `action_dropout` 更难；monitor 虽然降低 final distance，但成功率只到 1/3，说明单纯覆盖 oracle action 的恢复窗口还不够。
- w32 相比 w16 没有提升成功率，但减少了触发次数，说明长窗口可以降低重复触发，但不是解决 dropout/slip 的核心。

## 失败 Seed 观察

对未恢复成功的 monitor-corrected episode 做 step-level 摘要后，可以看到失败不是因为 monitor 没有触发：

| Window | Failure | Seed | Final Distance | Min Distance | Trigger Count | Override Steps | Steps |
|---:|---|---:|---:|---:|---:|---:|---:|
| 16 | action_dropout | 43001 | 0.1550 | 0.0384 | 13 | 195 | 200 |
| 16 | action_dropout | 43002 | 0.1614 | 0.0528 | 12 | 190 | 200 |
| 16 | execution_slip | 43001 | 0.1550 | 0.0384 | 13 | 195 | 200 |
| 32 | action_dropout | 43001 | 0.1550 | 0.0384 | 7 | 195 | 200 |
| 32 | action_dropout | 43002 | 0.1614 | 0.0528 | 6 | 190 | 200 |
| 32 | execution_slip | 43001 | 0.1550 | 0.0384 | 7 | 195 | 200 |

这些 episode 曾经接近目标，但没有进入 success threshold，随后距离又退回到约 0.155。并且 override steps 接近整集长度，说明失败的瓶颈不是检测不到，而是恢复策略没有处理好任务阶段/接触状态。

## 目前能支撑的研究说法

这轮结果支持一个更成熟的表述：

> 在 SurRoL NeedlePick 中，简单的运行时恢复层可以显著改善动作扰动下的任务完成率，但恢复效果依赖故障类型；不同 failure 需要不同的检测与恢复策略。

这比“加一个 monitor 提升成功率”更像博士课题，因为它引出了 failure taxonomy、selective recovery、intervention budget 和任务阶段建模。

## 局限

- 仍然只有 3 个 seed。
- 当前 recovery action 是 clean oracle override，不是 learned recovery policy。
- 当前 trigger 是规则型，不是校准的不确定性模型。
- `none` 仍有少量触发，说明 false intervention 还没有完全解决。

## 下一步

1. 加 phase-aware recovery：approach、grasp、lift 阶段使用不同恢复动作，而不是统一切回 oracle。
2. 对失败 seed 画 step-level distance/trigger/override 曲线，确认退回发生在哪个 waypoint。
3. 对 `coarse + 32` 做 5 到 10 seed 复跑，验证当前排序是否稳定。
4. 如果排序稳定，开始设计 learned risk score 或 uncertainty score，替代硬规则。
