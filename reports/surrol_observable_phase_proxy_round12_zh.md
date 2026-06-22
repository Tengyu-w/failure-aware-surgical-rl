# SurRoL 实验 Round 12：Observable Proxy Phase Recovery

## 一句话结论

本轮把 phase-aware recovery 从“依赖 SurRoL 内部 waypoint/activation 状态来判断何时重试”推进到一个 observable proxy 版本。新策略 `observable_phase_replan` 使用夹爪闭合命令次数、目标距离停滞、最小距离改善幅度等可记录信号来判断抓取阶段失败。在 `NeedlePick` 和 `GauzeRetrieve` 的 `jaw_stuck_open` 静默夹爪故障下，两个任务的 perturbed rollout 都是 0/5 成功；observable proxy recovery 都恢复到 5/5 成功，并且每个 seed 都触发 `observable_grasp_retry`。

## 本轮新增方法

新增 recovery policy：

```text
observable_phase_replan
```

判断信号：

- `close_command_count`：oracle/控制器已经多次发出闭合夹爪命令。
- `stalled_count`：目标距离长时间几乎没有改善。
- `current_distance`：当前仍明显远离成功阈值。
- `min_distance` improvement：episode 内最小距离相对初始距离改善很小。

触发含义：

```text
close command seen + still far + stalled/barely improved
=> observable_grasp_retry
```

需要谨慎说明：当前版本只是把“是否 replan 的判断依据”改成 observable proxy；真正执行重试时仍调用 SurRoL 的 waypoint primitive 来重建抓取流程。

## 实验文件

- 脚本：`E:\RL_projects\constraint_surgical_rl\scripts\run_surrol_monitor_recovery.ps1`
- NeedlePick CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_observable_phase_jaw_stuck_w32_5seed.csv`
- NeedlePick Step CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_observable_phase_jaw_stuck_w32_5seed_steps.csv`
- GauzeRetrieve CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_gauzeretrieve_observable_phase_jaw_stuck_w32_5seed.csv`
- GauzeRetrieve Step CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_gauzeretrieve_observable_phase_jaw_stuck_w32_5seed_steps.csv`
- Figure：`E:\RL_projects\constraint_surgical_rl\reports\figures\surrol_cross_task_observable_jaw_stuck\cross_task_jaw_stuck_recovery.png`

## 5 Seed 结果

| Task | Failure | Perturbed Success | Observable Recovery Success | Mean Triggers | Mean Observable Grasp Retries | Mean Recovered Steps |
|---|---|---:|---:|---:|---:|---:|
| NeedlePick | jaw_stuck_open | 0/5 | 5/5 | 3.0 | 1.8 | 102.4 |
| GauzeRetrieve | jaw_stuck_open | 0/5 | 5/5 | 3.0 | 2.0 | 102.0 |

## Seed-Level 观察

| Task | Seeds With Observable Grasp Retry | Phase Label |
|---|---:|---|
| NeedlePick | 5/5 | `observable_grasp_retry` |
| GauzeRetrieve | 5/5 | `observable_grasp_retry` |

## 和内部 Phase Replan 的对比

| Task | Policy | Success | Mean Triggers | Mean Phase Replans | Mean Steps |
|---|---|---:|---:|---:|---:|
| NeedlePick | internal `phase_replan` | 5/5 | 3.4 | 1.2 | 91.2 |
| NeedlePick | `observable_phase_replan` | 5/5 | 3.0 | 1.8 | 102.4 |
| GauzeRetrieve | internal `phase_replan` | 5/5 | 5.0 | 2.0 | 108.6 |
| GauzeRetrieve | `observable_phase_replan` | 5/5 | 3.0 | 2.0 | 102.0 |

解释：

- observable proxy 没有明显降低成功率。
- 它在两个任务上都能触发抓取重试。
- NeedlePick 上平均步数略多，说明 proxy 判断更保守或重试时机不同。
- GauzeRetrieve 上平均触发次数更少，说明 proxy 在这个 hard fault 下反而更集中。

## 研究意义

这一轮把项目从“仿真内部状态驱动恢复”往“可观测风险信号驱动恢复”推进了一步。更适合博士申请里的表达是：

> We prototype an observable-proxy failure monitor that detects silent grasp-stage failures from command history and progress stagnation, then routes the controller to a grasp retry primitive.

中文表述：

> 系统不是直接读取仿真内部状态说“我该重抓了”，而是根据夹爪命令历史和任务进展停滞来判断抓取阶段可能失败，再触发抓取重试。

## 仍然不能过度声称

- 这还不是 learned uncertainty model。
- 这还不是真实机器人可观测传感器验证。
- 恢复 primitive 仍然使用 SurRoL 内部 waypoint 生成。
- 仍然是 5 seed pilot。

## 下一步

1. 把 observable proxy 的风险分数显式记录为 `risk_score`，而不是只用布尔规则。
2. 做 threshold sweep：不同 stalled/count/distance 阈值下的 success、false trigger、delay。
3. 把普通三类扰动和 `jaw_stuck_open` 合并成正式总表。
4. 对关键配置跑 10 seed。

