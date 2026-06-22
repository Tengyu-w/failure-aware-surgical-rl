# SurRoL 正式实验 Round 3：NeedlePick Recovery Window Sweep

## 一句话结论

这轮扫了 `NeedlePick + action_noise` 下的 recovery window。结果显示：`coarse` trigger 在 4、8、16、32 步窗口下都能把 action_noise 从 0/3 成功恢复到 3/3；同时窗口越长，nominal 场景的触发次数越少。`goalaware` trigger 完全消除了 nominal false trigger，但恢复能力不足，最好也只有 2/3 成功。当前最强的实用 baseline 是 `coarse + 16/32 step recovery window`。

## 实验文件

- 汇总 CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_window_sweep_summary.csv`
- 逐步轨迹 CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_window_sweep_*_steps.csv`
- 实验脚本：`E:\RL_projects\constraint_surgical_rl\scripts\run_surrol_monitor_recovery.ps1`

## 实验设置

- Task：SurRoL `NeedlePick`
- Failure：`action_noise`
- Nominal control：`none`
- Seeds：3
- Horizon：200 steps
- Recovery windows：4、8、16、32 steps
- Trigger modes：
  - `coarse`：高召回，包含短时停滞/轻微回退等触发条件
  - `goalaware`：低误报，去掉正常 waypoint 阶段容易误伤的停滞条件，并提高回退容忍度

## 核心结果

| Trigger | Window | Nominal Success | Nominal Triggers | Perturbed Success | Monitor Success | Monitor Triggers | Final Distance |
|---|---:|---:|---:|---:|---:|---:|---:|
| coarse | 4 | 1.000 | 7.67 | 0.000 | 1.000 | 10.33 | 0.0193 |
| coarse | 8 | 1.000 | 4.00 | 0.000 | 1.000 | 5.67 | 0.0187 |
| coarse | 16 | 1.000 | 2.00 | 0.000 | 1.000 | 3.00 | 0.0192 |
| coarse | 32 | 1.000 | 1.00 | 0.000 | 1.000 | 2.00 | 0.0192 |
| goalaware | 4 | 1.000 | 0.00 | 0.000 | 0.000 | 39.67 | 0.2230 |
| goalaware | 8 | 1.000 | 0.00 | 0.000 | 0.333 | 16.67 | 0.1558 |
| goalaware | 16 | 1.000 | 0.00 | 0.000 | 0.667 | 6.33 | 0.0694 |
| goalaware | 32 | 1.000 | 0.00 | 0.000 | 0.667 | 3.67 | 0.1042 |

## 解释

- `action_noise` 是一个稳定破坏任务的 failure：perturbed success 始终是 0/3。
- `coarse` trigger 的恢复能力很强：所有 window 都能恢复到 3/3。
- `coarse` 的 nominal false trigger 随 recovery window 变长而下降：从 7.67 降到 1.00。
- `goalaware` trigger 的 false trigger 是 0，但恢复能力下降，说明它漏掉了一些需要早介入的风险。
- 这不是简单的“越保守越好”；在这个任务里，过度保守会 miss failure。

## 当前最佳候选

`coarse + 16` 或 `coarse + 32` 是下一步最值得保留的 baseline：

- 成功恢复 action_noise：3/3
- nominal 仍成功：3/3
- nominal triggers 降到 2.00 或 1.00
- final distance 接近 clean oracle

## 研究意义

这轮实验把问题从“有没有 monitor”推进到了“如何调 intervention policy”。这更像一个可写进博士计划的问题：

> 在多阶段手术机器人任务中，风险监督器的触发阈值和恢复窗口如何影响 missed failure 与 false intervention 的权衡？

## 下一步

1. 用 `coarse + 16/32` 扩展到 `action_dropout` 和 `execution_slip`，看强 baseline 是否仍能部分恢复。
2. 做 5 到 10 seed 的复跑，验证 3 seed 结果是否稳定。
3. 引入 phase-aware trigger：在 approach、grasp、lift 阶段采用不同触发条件。
4. 画 step-level 曲线，比较 `goalaware` 为什么在 seed 43001/43002 上错过恢复窗口。
