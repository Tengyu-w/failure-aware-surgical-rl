# SurRoL 实验 Round 10：GauzeRetrieve 静默夹爪故障

## 一句话结论

本轮给 `GauzeRetrieve` 增加了一个更贴近执行风险的故障：`jaw_stuck_open`。它模拟控制器发出闭合夹爪动作，但执行端在前期保持张开，且这个故障不直接暴露为 action deviation。5 seed 结果显示，原始 perturbed rollout 为 0/5 成功；加入 runtime monitor + phase-aware recovery 后恢复到 5/5 成功，并且每个 seed 都触发了 `grasp_retry`。这补上了 Round 9 中 `GauzeRetrieve` 没有真正测试 phase replan 的缺口。

## 新增故障

`jaw_stuck_open` 的设定：

- 当 oracle/控制器试图闭合夹爪时，前 70 step 内执行端被强制保持打开。
- 该故障被记为 silent fault，不直接计入 action deviation。
- 这比普通 action noise/dropout 更接近“执行端失败但控制端不一定立刻知道”的风险。
- 在 monitor override 阶段，故障在前 70 step 内仍然存在，因此短期 override 不能立刻解决全部问题。

## 文件

- 实验脚本：`E:\RL_projects\constraint_surgical_rl\scripts\run_surrol_monitor_recovery.ps1`
- Episode CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_gauzeretrieve_jaw_stuck_phase_replan_w32_5seed.csv`
- Step CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_gauzeretrieve_jaw_stuck_phase_replan_w32_5seed_steps.csv`
- 自动报告：`E:\RL_projects\constraint_surgical_rl\reports\surrol_gauzeretrieve_jaw_stuck_phase_replan_w32_5seed.md`
- 图：`E:\RL_projects\constraint_surgical_rl\reports\figures\surrol_gauzeretrieve_jaw_stuck\gauzeretrieve_jaw_stuck_recovery.png`
- 画图脚本：`E:\RL_projects\constraint_surgical_rl\scripts\plot_surrol_jaw_stuck_results.py`

## 5 Seed 结果

| Failure | Controller | Episodes | Success | Final Distance | Mean Triggers | Mean Phase Replans | Mean Override Rate | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| none | clean | 5 | 1.000 | 0.0126 | 0.0 | 0.0 | 0.000 | 34.6 |
| none | monitor_corrected | 5 | 1.000 | 0.0129 | 1.0 | 0.0 | 0.826 | 34.6 |
| jaw_stuck_open | clean | 5 | 1.000 | 0.0126 | 0.0 | 0.0 | 0.000 | 34.6 |
| jaw_stuck_open | perturbed | 5 | 0.000 | 0.2647 | 0.0 | 0.0 | 0.000 | 220.0 |
| jaw_stuck_open | monitor_corrected | 5 | 1.000 | 0.0130 | 5.0 | 2.0 | 0.945 | 108.6 |

## Seed-Level 观察

| Seed | Perturbed Success | Recovered Success | Recovered Steps | Triggers | Phase Replans |
|---:|---:|---:|---:|---:|---:|
| 43000 | 0 | 1 | 109 | 5 | 2 |
| 43001 | 0 | 1 | 107 | 5 | 2 |
| 43002 | 0 | 1 | 109 | 5 | 2 |
| 43003 | 0 | 1 | 109 | 5 | 2 |
| 43004 | 0 | 1 | 109 | 5 | 2 |

## 研究意义

Round 9 的普通扰动说明，`GauzeRetrieve` 在 action noise/dropout/slip 下可以靠短期 runtime correction 恢复，但没有真正触发 phase replan。Round 10 则进一步说明，当故障发生在夹爪/抓取执行层时，第二任务也会需要阶段性恢复。

因此现在可以更稳地表达：

> Across two SurRoL tasks, phase-aware recovery is not merely a NeedlePick-specific hack. Under a silent jaw-stuck execution fault, GauzeRetrieve also requires grasp-stage retry to recover corrupted rollouts.

中文说法：

> 这个项目不再只是“避开/靠近目标点”。在更真实的执行故障下，系统需要识别抓取阶段失败并重新进入抓取阶段，说明恢复动作开始具有任务阶段含义。

## 仍需谨慎

- `jaw_stuck_open` 是人工合成故障，不是真实硬件日志。
- 当前 monitor/recovery 仍是规则型。
- 5 seed 仍然是 pilot 规模。
- `grasp_retry` 仍然依赖 SurRoL 内部 waypoint 状态，后续应替换为可观测 proxy。

## 下一步

1. 把 `jaw_stuck_open` 同时跑到 `NeedlePick`，形成 cross-task harder failure 对比。
2. 增加 observable proxy 版本：用 jaw command、tool-object distance、object-goal residual、motion stall 判断抓取失败。
3. 把普通三类扰动和 `jaw_stuck_open` 合并进一张正式实验总表。
4. 如果时间允许，再 smoke `NeedleRegrasp`，为第三任务扩展做准备。

