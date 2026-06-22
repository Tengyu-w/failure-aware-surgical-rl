# SurRoL 实验 Round 9：第二任务 GauzeRetrieve 横向扩展

## 一句话结论

项目已经从单一 `NeedlePick` 扩展到第二个 SurRoL 手术操作任务 `GauzeRetrieve`。在 5 seed 设置下，`GauzeRetrieve` 的三类扰动 rollout 都是 0/5 成功；加入同一套 runtime monitor + phase-aware recovery 框架后，三类扰动全部恢复到 5/5 成功。需要注意的是，`GauzeRetrieve` 中没有触发显式 `grasp_retry/lift_retry`，说明该任务当前主要靠短期 oracle override 即可恢复，而 `NeedlePick` 的 dropout/slip 更依赖 phase replan。

## 本轮新增内容

- 将 `scripts\run_surrol_monitor_recovery.ps1` 从单任务脚本升级为可选任务脚本。
- 新增参数：`-Task NeedlePick|GauzeRetrieve`。
- 保持旧默认行为：不传 `-Task` 时仍然运行 `NeedlePick`。
- 新跑 `GauzeRetrieve` 5 seed 正式实验。

## 新实验文件

- Episode CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_gauzeretrieve_phase_replan_w32_5seed.csv`
- Step CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_gauzeretrieve_phase_replan_w32_5seed_steps.csv`
- 自动报告：`E:\RL_projects\constraint_surgical_rl\reports\surrol_gauzeretrieve_phase_replan_w32_5seed.md`
- 脚本：`E:\RL_projects\constraint_surgical_rl\scripts\run_surrol_monitor_recovery.ps1`
- Cross-task 图：`E:\RL_projects\constraint_surgical_rl\reports\figures\surrol_cross_task\cross_task_success_rate.png`
- Cross-task 画图脚本：`E:\RL_projects\constraint_surgical_rl\scripts\plot_surrol_cross_task_results.py`

## GauzeRetrieve 5 Seed 结果

| Failure | Controller | Episodes | Success | Final Distance | Mean Triggers | Phase Replans | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|
| none | clean | 5 | 1.000 | 0.0126 | 0.0 | 0.0 | 34.6 |
| none | monitor_corrected | 5 | 1.000 | 0.0129 | 1.0 | 0.0 | 34.6 |
| action_noise | perturbed | 5 | 0.000 | 0.2708 | 0.0 | 0.0 | 200.0 |
| action_noise | monitor_corrected | 5 | 1.000 | 0.0169 | 1.8 | 0.0 | 34.6 |
| action_dropout | perturbed | 5 | 0.000 | 0.2570 | 0.0 | 0.0 | 200.0 |
| action_dropout | monitor_corrected | 5 | 1.000 | 0.0124 | 1.0 | 0.0 | 35.6 |
| execution_slip | perturbed | 5 | 0.000 | 0.2651 | 0.0 | 0.0 | 200.0 |
| execution_slip | monitor_corrected | 5 | 1.000 | 0.0129 | 1.0 | 0.0 | 35.8 |

## Cross-Task 对比

| Task | Failure | Perturbed Success | Recovered Success | Mean Phase Replans | 解释 |
|---|---|---:|---:|---:|---|
| NeedlePick | action_noise | 0/5 | 5/5 | 0.0 | 短期动作纠正足够 |
| NeedlePick | action_dropout | 0/5 | 5/5 | 0.8 | 多数 seed 需要 `grasp_retry` |
| NeedlePick | execution_slip | 0/5 | 5/5 | 0.4 | 部分 seed 需要 `grasp_retry` |
| GauzeRetrieve | action_noise | 0/5 | 5/5 | 0.0 | 短期动作纠正足够 |
| GauzeRetrieve | action_dropout | 0/5 | 5/5 | 0.0 | 当前扰动下未进入显式重试阶段 |
| GauzeRetrieve | execution_slip | 0/5 | 5/5 | 0.0 | 当前扰动下未进入显式重试阶段 |

## 这对项目定位的提升

之前项目最容易被质疑的是：是不是只在 `NeedlePick` 上调出来的单任务 demo？

现在可以更稳地说：

> We have implemented a shared failure-aware runtime recovery framework and evaluated it on two SurRoL manipulation tasks. NeedlePick requires phase-aware grasp retry under dropout/slip, while GauzeRetrieve can be recovered by short-horizon runtime correction under the tested corruptions.

这句话比“我做了一个避障/靠近目标点”强很多，因为它开始呈现出任务差异和恢复机制差异。

## 研究解释

当前结果支持三层说法：

1. 已经展示：同一套监控-恢复框架可以跨 `NeedlePick` 和 `GauzeRetrieve` 两个任务运行。
2. 数据暗示：不同任务的失败恢复机制不同，`NeedlePick` 更依赖抓取阶段重试，`GauzeRetrieve` 在当前扰动下更像短期动作纠正问题。
3. 尚未证明：这还不是通用 surgical autonomy，也没有证明 learned recovery 或真实机器人可迁移。

## 局限

- 仍然是 5 seed pilot。
- 两个任务都在 SurRoL 仿真环境中完成，没有真实机器人或 sim-to-real 验证。
- `GauzeRetrieve` 虽然跑的是 `phase_replan` policy，但实际没有触发 phase replan，因此不能说第二任务也证明了 grasp/lift phase retry。
- 当前 recovery 仍然是规则型，不是 learned recovery。

## 下一步建议

1. 对 `GauzeRetrieve` 增加强一点的接触/抓取失败扰动，让它真正测试 `grasp_retry` 是否必要。
2. 将 `NeedlePick + GauzeRetrieve` 合并成一张 cross-task figure。
3. 扩展第三个任务，优先选择更复杂的 `NeedleRegrasp`，因为它能体现双臂/交接/重抓取阶段。
4. 把内部 phase 状态替换成 observable risk proxy，避免看起来像仿真内部状态 hack。
