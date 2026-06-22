# SurRoL 实验 Round 11：跨任务静默夹爪故障验证

## 一句话结论

本轮把 `jaw_stuck_open` 静默夹爪故障从 `GauzeRetrieve` 扩展到 `NeedlePick`，形成两个任务的 hard-fault 对比。5 seed 结果显示，两个任务在该故障下的 perturbed rollout 都是 0/5 成功；加入 runtime monitor + phase-aware recovery 后都恢复到 5/5 成功，并且两个任务都触发了 `grasp_retry`。这说明阶段性恢复不再只是 `NeedlePick` 或 `GauzeRetrieve` 的单点现象，而是在两个任务上都能处理抓取执行层失败。

## 实验文件

- NeedlePick Episode CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_jaw_stuck_phase_replan_w32_5seed.csv`
- NeedlePick Step CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_jaw_stuck_phase_replan_w32_5seed_steps.csv`
- GauzeRetrieve Episode CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_gauzeretrieve_jaw_stuck_phase_replan_w32_5seed.csv`
- GauzeRetrieve Step CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_gauzeretrieve_jaw_stuck_phase_replan_w32_5seed_steps.csv`
- Cross-task 图：`E:\RL_projects\constraint_surgical_rl\reports\figures\surrol_cross_task_jaw_stuck\cross_task_jaw_stuck_recovery.png`
- 画图脚本：`E:\RL_projects\constraint_surgical_rl\scripts\plot_surrol_cross_task_jaw_stuck.py`

## Cross-Task 结果

| Task | Failure | Perturbed Success | Recovered Success | Mean Triggers | Mean Grasp Retries | Mean Recovered Steps |
|---|---|---:|---:|---:|---:|---:|
| GauzeRetrieve | jaw_stuck_open | 0/5 | 5/5 | 5.0 | 2.0 | 108.6 |
| NeedlePick | jaw_stuck_open | 0/5 | 5/5 | 3.4 | 1.2 | 91.2 |

## 和前几轮的关系

- Round 7：`NeedlePick` 在 action dropout/slip 下需要 `grasp_retry`。
- Round 9：`GauzeRetrieve` 普通三类扰动可以恢复，但没有触发 phase replan。
- Round 10：`GauzeRetrieve` 在 `jaw_stuck_open` 下也需要 `grasp_retry`。
- Round 11：`NeedlePick` 和 `GauzeRetrieve` 在同一个静默夹爪故障下都需要 `grasp_retry`，形成跨任务证据。

## 研究意义

这轮结果让项目的主线更清楚：

> Different corruptions require different recovery mechanisms. Short-horizon action correction can handle some motion corruptions, but silent grasp/execution faults require task-phase-aware retry.

中文表述：

> 不是所有失败都适合用同一个“纠正动作”处理。动作噪声可以靠短期纠正，但夹爪卡开这类静默执行故障需要识别抓取阶段失败，并重新进入抓取阶段。

这比“避让障碍/靠近目标点”更接近 surgical autonomy 的风险恢复问题，因为它开始关心：系统是否知道自己在哪个任务阶段失败，以及应该重试哪个阶段。

## 当前仍然不能夸大的地方

- 仍然是 5 seed pilot，不是最终统计结论。
- `jaw_stuck_open` 是合成故障，不是真实机器人日志。
- `grasp_retry` 目前仍依赖 SurRoL 内部 waypoint 状态。
- recovery policy 是规则型，还不是 learned recovery。

## 下一步优先级

1. 做 observable proxy：不用内部 waypoint，改用 jaw command、tool-object distance、motion stall、object-goal residual 推断抓取失败。
2. 将 `action_noise/action_dropout/execution_slip/jaw_stuck_open` 合并成正式总表。
3. 对关键配置跑 10 seed，加强统计可信度。
4. Smoke 第三个任务 `NeedleRegrasp`，判断是否值得做双臂/重抓取扩展。

