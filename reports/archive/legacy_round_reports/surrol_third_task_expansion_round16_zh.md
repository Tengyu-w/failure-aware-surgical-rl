# SurRoL 实验 Round 16：第三任务扩展与 NeedleReach 5 Seed

## 一句话结论

第三任务扩展已经完成一次可用验证，但需要分两层理解：`NeedleRegrasp` 已经 smoke 到接口层，但 clean oracle 没有通过默认 success metric，因此暂缓正式实验；作为稳定第三任务，`NeedleReach` 已接入主 runner，并在 `action_freeze` 故障下完成 5 seed：perturbed 0/5，monitor-corrected 5/5。它不是核心复杂操作任务，但能作为框架跨第三个 SurRoL 任务运行的广度证据。

## 新增文件

- NeedleReach 5 seed episode CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlereach_action_freeze_w16_5seed.csv`
- NeedleReach 5 seed step CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlereach_action_freeze_w16_5seed_steps.csv`
- 自动报告：`E:\RL_projects\constraint_surgical_rl\reports\surrol_needlereach_action_freeze_w16_5seed.md`
- 主 runner：`E:\RL_projects\constraint_surgical_rl\scripts\run_surrol_monitor_recovery.ps1`
- Master table：`E:\RL_projects\constraint_surgical_rl\reports\tables\surrol_master_paired_results.csv`

## NeedleReach 5 Seed 结果

| Task | Failure | Controller | Episodes | Success | Final Distance | Mean Triggers | Mean Steps |
|---|---|---|---:|---:|---:|---:|---:|
| NeedleReach | none | clean | 5 | 1.000 | 0.0157 | 0.0 | 19.2 |
| NeedleReach | none | monitor_corrected | 5 | 1.000 | 0.0157 | 0.0 | 19.2 |
| NeedleReach | action_freeze | clean | 5 | 1.000 | 0.0157 | 0.0 | 19.2 |
| NeedleReach | action_freeze | perturbed | 5 | 0.000 | 0.4166 | 0.0 | 120.0 |
| NeedleReach | action_freeze | monitor_corrected | 5 | 1.000 | 0.0157 | 2.0 | 21.2 |

## 和前面任务的关系

| Task | Role | Current Evidence |
|---|---|---|
| NeedlePick | 核心操作任务 | standard corruptions、jaw-stuck、observable proxy、10 seed |
| GauzeRetrieve | 第二核心操作任务 | standard corruptions、jaw-stuck、observable proxy、10 seed |
| NeedleReach | 第三任务广度补充 | action-freeze 5 seed recovery |
| NeedleRegrasp | 高复杂度候选 | 接口 smoke 已完成，但 clean oracle/success metric 未通过 |

## 研究解释

可以谨慎地说：

> The framework now runs across three SurRoL tasks, with the strongest evidence on NeedlePick and GauzeRetrieve and a simpler third-task recovery check on NeedleReach.

不应该说：

> 三个复杂手术操作任务都已完成 phase-aware recovery 验证。

`NeedleReach` 的作用是证明工程框架和 monitor/recovery runner 可以横向扩展到第三任务；真正有研究含量的 phase-aware/observable-proxy 证据仍主要来自 `NeedlePick` 和 `GauzeRetrieve`。

## NeedleRegrasp 暂缓原因

`NeedleRegrasp` 的 bimanual org 版本可以 reset、step、产生 10 维 oracle action，但 clean oracle 在 260 step 内没有达到默认 success。诊断显示 waypoints 已消费完，但默认 achieved goal 使用针的 `obj_link1`，最终仍远离目标；这更像双臂任务的 goal/link/success 语义问题，而不是简单 runner bug。

full-dof 版本需要 `dvrk/rospy/PyKDL`，属于 ROS/dVRK/硬件相关依赖，当前没有继续运行。

## 下一步

1. 把英文 pitch 更新到最新状态：two core manipulation tasks + one reach sanity task + observable proxy risk sweep。
2. 若继续追第三复杂任务，优先修 `NeedleRegrasp` 的 success/goal/link 语义。
3. 若优先出材料，先把 master table、10 seed figure、risk sweep figure 统一进英文项目摘要。

