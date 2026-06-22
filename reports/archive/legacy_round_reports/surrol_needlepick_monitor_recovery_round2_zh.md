# SurRoL 正式实验 Round 2：NeedlePick Monitor Recovery

## 一句话结论

在 `NeedlePick` 上，动作扰动会稳定破坏 oracle 成功率，而一个简单的 runtime monitor 已经能把 `action_noise` 从 0/3 成功恢复到 3/3 成功；但对 `action_dropout` 和 `execution_slip` 只恢复到 1/3 成功，并且 nominal 场景也会触发干预，说明 monitor 有效但还偏粗糙，尤其需要降低 false trigger 和改进恢复策略。

## 实验文件

- Episode CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_monitor_recovery.csv`
- Step CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_monitor_recovery_steps.csv`
- 自动报告：`E:\RL_projects\constraint_surgical_rl\reports\surrol_needlepick_monitor_recovery_zh.md`
- 实验脚本：`E:\RL_projects\constraint_surgical_rl\scripts\run_surrol_monitor_recovery.ps1`

## 实验设置

- Task：SurRoL `NeedlePick`
- Seeds：3 个 seed，`43000` 到 `43002`
- Horizon：200 steps
- Controllers：
  - `clean`：无扰动 oracle
  - `perturbed`：注入动作扰动的 oracle
  - `monitor_corrected`：检测风险后临时覆盖为 clean oracle action
- Failures：`action_noise`、`action_dropout`、`execution_slip`
- Recovery window：8 steps

## 汇总结果

| Failure | Controller | Episodes | Success | Final Distance | Risk Event | Monitor Triggers | Override Rate | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| none | clean | 3 | 1.000 | 0.0214 | 0.704 | 0.00 | 0.000 | 40.7 |
| none | monitor_corrected | 3 | 1.000 | 0.0214 | 0.704 | 4.00 | 0.783 | 40.7 |
| action_noise | clean | 3 | 1.000 | 0.0214 | 0.704 | 0.00 | 0.000 | 40.7 |
| action_noise | perturbed | 3 | 0.000 | 0.2103 | 0.993 | 0.00 | 0.000 | 200.0 |
| action_noise | monitor_corrected | 3 | 1.000 | 0.0187 | 0.750 | 5.67 | 0.951 | 41.3 |
| action_dropout | clean | 3 | 1.000 | 0.0214 | 0.704 | 0.00 | 0.000 | 40.7 |
| action_dropout | perturbed | 3 | 0.000 | 0.1969 | 0.960 | 0.00 | 0.000 | 200.0 |
| action_dropout | monitor_corrected | 3 | 0.333 | 0.1125 | 0.872 | 18.00 | 0.938 | 148.3 |
| execution_slip | clean | 3 | 1.000 | 0.0214 | 0.704 | 0.00 | 0.000 | 40.7 |
| execution_slip | perturbed | 3 | 0.000 | 0.2231 | 0.985 | 0.00 | 0.000 | 200.0 |
| execution_slip | monitor_corrected | 3 | 0.333 | 0.1112 | 0.859 | 18.33 | 0.960 | 147.7 |

## 主要发现

- `NeedlePick` 是一个合适的 failure-aware benchmark：clean oracle 稳定 3/3 成功，而三类扰动下 perturbed oracle 都是 0/3 成功。
- 当前 monitor 对 `action_noise` 很有效：成功率从 0.000 提升到 1.000，平均步数也回到约 41 步。
- 当前 monitor 对 `action_dropout` 和 `execution_slip` 只有部分效果：成功率从 0.000 提升到 0.333，最终距离明显优于 perturbed，但仍未稳定完成任务。
- Step-level CSV 已保存，可以继续画 distance/risk/trigger 曲线，分析为什么某些 seed 没恢复。

## 问题和限制

- `none + monitor_corrected` 也触发了干预，说明当前 trigger 过敏。
- `risk_event_rate` 在 clean 轨迹中偏高，主要原因是当前规则把接近目标后的持续小进展也算作 stalled risk；下一版需要 goal-aware stall rule。
- 当前恢复策略只是临时切回 clean oracle，并不是 learned recovery policy。
- 只有 3 个 seed，属于正式实验起步，不是最终统计结论。

## 下一步

1. 修改 risk trigger：当距离已经接近 success threshold 或仍保持单调接近目标时，不把 stall 记为风险。
2. 对失败 seed 画 step-level 曲线，重点看 `action_dropout` 和 `execution_slip` 为什么恢复窗口不足。
3. 增加 recovery window sweep：4、8、16、32 steps。
4. 在调好 false trigger 后，再跑 5 到 10 seed，形成可写进博士课题雏形的稳定表格。
