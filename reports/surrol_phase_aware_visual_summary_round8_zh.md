# SurRoL 实验 Round 8：Phase-Aware Recovery 可视化小结

## 一句话结论

这轮没有再改核心算法，而是把 Round 7 的 5 seed `NeedlePick` phase-aware recovery 结果整理成可展示图。三类扰动下，原始 perturbed controller 都是 0/5 成功；加入 phase-aware recovery 后，`action_noise`、`action_dropout`、`execution_slip` 都恢复到 5/5 成功。轨迹图进一步显示，恢复不是只靠“避让”或“靠近目标点”，而是在失败后重新进入抓取阶段，把物体重新带到成功阈值内。

## 图文件

- 成功率对比图：`E:\RL_projects\constraint_surgical_rl\reports\figures\surrol_phase_aware\success_rate_by_failure.png`
- 代表性距离轨迹：`E:\RL_projects\constraint_surgical_rl\reports\figures\surrol_phase_aware\representative_distance_curves.png`
- phase replan 时间线：`E:\RL_projects\constraint_surgical_rl\reports\figures\surrol_phase_aware\phase_replan_timeline.png`
- 画图脚本：`E:\RL_projects\constraint_surgical_rl\scripts\plot_surrol_phase_aware_results.py`

## 图 1：成功率对比

`success_rate_by_failure.png` 展示的是最核心的横向结果：

| Failure | Perturbed | Phase-aware recovery |
|---|---:|---:|
| action_noise | 0/5 | 5/5 |
| action_dropout | 0/5 | 5/5 |
| execution_slip | 0/5 | 5/5 |

这张图适合放在项目 pitch 或博士申请材料里，表达方式可以是：

> In a 5-seed SurRoL NeedlePick pilot, phase-aware recovery restores three corrupted rollout types from 0/5 perturbed success to 5/5 recovered success.

需要谨慎的是，这仍然是 5 seed pilot，不应写成已经充分统计验证。

## 图 2：代表性距离轨迹

`representative_distance_curves.png` 展示每类扰动中一个代表性 episode 的 goal distance 随时间变化。

可以看到：

- perturbed rollout 通常长时间停留在较大 goal distance，最终没有进入成功阈值。
- phase-aware recovery 的曲线会在触发恢复后快速下降到成功阈值附近。
- 对 `action_dropout` 和 `execution_slip`，恢复过程不是单纯继续推进原轨迹，而是出现了重新尝试抓取后的距离下降。

这张图的意义是把“5/5 成功率”变成可解释的过程证据：失败不是被一个最终数字掩盖，而是能看到系统从失败状态回到可完成状态。

## 图 3：Phase Replan 时间线

`phase_replan_timeline.png` 展示 dropout/slip 的具体恢复时刻：

- 橙色竖线表示 risk trigger。
- 紫色虚线表示 `grasp_retry`。
- 灰色虚线表示成功阈值。

这张图最重要的含义是：当前系统不是只有一个泛化的“纠正动作”，而是已经能区分任务阶段。当 rollout 已经走完但没有形成有效抓取时，系统会执行 `grasp_retry`，重新构造抓取相关 waypoint，再把任务带回成功区域。

## 当前能支持的研究表述

可以相对稳妥地说：

> The prototype suggests that recovery in surgical manipulation should be phase-aware: action noise may be corrected by short-horizon override, while dropout and slip often require re-entering the grasp phase.

中文表达可以是：

> 当前实验说明，手术操作中的失败恢复不应只被建模成“避障”或“继续靠近目标点”。不同失败类型对应不同任务阶段，尤其是 dropout 和 slip 常常需要重新进入抓取阶段，而不是简单修正下一步动作。

## 仍然不能过度声称的地方

- 目前只有 `NeedlePick` 一个完整任务的正式 5 seed 结果。
- `phase_replan` 仍然使用 SurRoL 内部 waypoint/contact/activation 状态，离真实机器人上的可观测风险信号还有距离。
- 目前 recovery policy 仍是规则型，不是 learned recovery policy。
- 现在证明的是“failure-aware / phase-aware recovery 方向有希望”，还不是证明已经超越某个完整老师项目或 SOTA 系统。

## 下一步优先级

1. 把同一套 failure + monitor + recovery 框架扩展到第二个 SurRoL 任务，优先 `NeedleRegrasp` 或 `GauzeRetrieve`。
2. 把内部 phase 判断替换成可观测 proxy：tool-object distance、object-goal residual、contact proxy、jaw state、recent motion consistency。
3. 增加 10 seed 复现实验，并报告均值、方差和 seed-level failure case。
4. 增加一个横向 baseline：只做 oracle override、不做 phase replan，用来证明 phase-aware 不是可有可无。

