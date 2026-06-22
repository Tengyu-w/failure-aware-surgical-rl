# SurRoL 正式实验 Round 7：Phase-Aware Recovery

## 一句话结论

已经完成 `phase-aware recovery`。在 5 seed SurRoL `NeedlePick` 中，三类扰动的 perturbed controller 都是 0/5 成功；加入 phase-aware recovery 后，`action_noise`、`action_dropout`、`execution_slip` 全部恢复到 5/5，同时 nominal case 仍保持 5/5。step-level 标签显示，dropout 和 slip 的关键恢复阶段主要是 `grasp_retry`，说明失败集中在抓取/接触闭环，而不是简单的轨迹偏差。

## 实验文件

- Episode CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_phase_replan_w32_5seed.csv`
- Step CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_phase_replan_w32_5seed_steps.csv`
- Summary CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_phase_replan_w32_5seed_summary.csv`
- 实验脚本：`E:\RL_projects\constraint_surgical_rl\scripts\run_surrol_monitor_recovery.ps1`

## 方法升级

上一轮 `contact_replan` 的逻辑是：如果 waypoint 已经走完，但任务未成功且没有有效抓取，就重建 NeedlePick waypoints。

本轮 `phase_replan` 进一步显式区分恢复阶段：

- `grasp_retry`：waypoint 已消费完、任务未成功、没有有效激活/接触约束时，重建 approach/grasp/lift 流程；
- `lift_retry`：已经有激活或接触约束，但流程结束后仍未成功时，只保留 lift/transfer waypoint；
- 普通 action noise：不需要 phase replan，靠短期 oracle override 即可恢复。

当前 5 seed 中实际触发的 phase label 主要是 `grasp_retry`，说明主要失败来自抓取/接触阶段。

## 核心结果

| Failure | Controller | Episodes | Success | Final Distance | Mean Triggers | Phase Replans | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|
| none | monitor_corrected | 5 | 1.000 | 0.0196 | 1.00 | 0.00 | 40.0 |
| action_noise | perturbed | 5 | 0.000 | 0.2172 | 0.00 | 0.00 | 200.0 |
| action_noise | monitor_corrected | 5 | 1.000 | 0.0201 | 2.00 | 0.00 | 40.0 |
| action_dropout | perturbed | 5 | 0.000 | 0.1946 | 0.00 | 0.00 | 200.0 |
| action_dropout | monitor_corrected | 5 | 1.000 | 0.0216 | 2.80 | 0.80 | 74.2 |
| execution_slip | perturbed | 5 | 0.000 | 0.2196 | 0.00 | 0.00 | 200.0 |
| execution_slip | monitor_corrected | 5 | 1.000 | 0.0202 | 2.40 | 0.40 | 58.0 |

## Phase 标签观察

| Failure | Seeds With Phase Replan | Phase |
|---|---:|---|
| action_noise | 0/5 | none |
| action_dropout | 4/5 | grasp_retry |
| execution_slip | 2/5 | grasp_retry |

这说明三类故障的恢复机制不同：

- `action_noise`：主要是局部动作偏差，短期 action override 足够；
- `action_dropout`：经常导致抓取阶段失败，需要重新执行 grasp；
- `execution_slip`：部分 seed 出现抓取失败，需要 grasp retry；其他 seed 用普通 override 即可恢复。

## 和前一版的区别

| Recovery Policy | action_noise | action_dropout | execution_slip | Phase Label |
|---|---:|---:|---:|---|
| oracle_override | 5/5 | 1/5 | 3/5 | no |
| contact_replan | 5/5 | 5/5 | 5/5 | coarse contact state |
| phase_replan | 5/5 | 5/5 | 5/5 | explicit grasp/lift retry |

`phase_replan` 的成功率与 `contact_replan` 持平，但解释性更强：它把恢复动作绑定到任务阶段，而不是只说“接触失败就重建”。

## 当前可支撑的研究说法

> In a 5-seed SurRoL NeedlePick pilot, phase-aware recovery restores action-noise, action-dropout, and execution-slip failures from 0/5 perturbed success to 5/5 monitor-corrected success while preserving nominal success. Step-level diagnostics show that dropout and slip failures primarily require grasp-stage retry, supporting the need for task-phase-aware recovery rather than generic action correction.

## 仍需谨慎的地方

- 仍然是 5 seed pilot，不是最终统计结论。
- `phase_replan` 仍使用 SurRoL 内部 waypoint/contact state，后续需要转成可观测 proxy 或 learned risk signal。
- 当前只在 `NeedlePick` 完整验证，仍需扩展到 `GauzeRetrieve`、`NeedleRegrasp` 或 `PegTransfer`。
- 这证明 phase-aware recovery 的方向可行，但还不是 learned surgical autonomy。

## 下一步

1. 扩展第二个 SurRoL 任务，优先 `GauzeRetrieve` 或 `NeedleRegrasp`。
2. 把内部 phase/contact 判断替换成可观测特征：jaw state、tool-object distance、contact proxy、object-goal residual。
3. 画 step-level 曲线，展示 perturbed、oracle_override、phase_replan 的距离和触发差异。
4. 跑 10 seed，并报告 seed variance / confidence interval。
