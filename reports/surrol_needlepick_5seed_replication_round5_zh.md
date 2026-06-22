# SurRoL 正式实验 Round 5：NeedlePick 5-Seed Replication

## 一句话结论

`coarse + 32 recovery window` 的 5 seed 复跑确认了前面 3 seed 的主要结论：`NeedlePick` 在 clean oracle 下稳定成功，三类动作扰动下 perturbed oracle 稳定失败；runtime recovery 对 `action_noise` 最有效，可以从 0/5 恢复到 5/5；对 `execution_slip` 部分有效，从 0/5 恢复到 3/5；对 `action_dropout` 仍然困难，只从 0/5 恢复到 1/5。

## 实验文件

- Episode CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_coarse_w32_5seed.csv`
- Step CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_coarse_w32_5seed_steps.csv`
- Summary CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needlepick_coarse_w32_5seed_summary.csv`
- 自动报告：`E:\RL_projects\constraint_surgical_rl\reports\surrol_needlepick_coarse_w32_5seed.md`

## 实验设置

- Task：SurRoL `NeedlePick`
- Seeds：5，`43000` 到 `43004`
- Horizon：200 steps
- Trigger mode：`coarse`
- Recovery window：32 steps
- Failures：`action_noise`、`action_dropout`、`execution_slip`
- Controllers：`clean`、`perturbed`、`monitor_corrected`

## 核心结果

| Failure | Controller | Episodes | Success | Final Distance | Monitor Triggers | Override Rate | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|
| none | clean | 5 | 1.000 | 0.0196 | 0.00 | 0.000 | 40.0 |
| none | monitor_corrected | 5 | 1.000 | 0.0196 | 1.00 | 0.799 | 40.0 |
| action_noise | perturbed | 5 | 0.000 | 0.2172 | 0.00 | 0.000 | 200.0 |
| action_noise | monitor_corrected | 5 | 1.000 | 0.0201 | 2.00 | 0.964 | 40.0 |
| action_dropout | perturbed | 5 | 0.000 | 0.1946 | 0.00 | 0.000 | 200.0 |
| action_dropout | monitor_corrected | 5 | 0.200 | 0.1308 | 5.80 | 0.962 | 169.0 |
| execution_slip | perturbed | 5 | 0.000 | 0.2196 | 0.00 | 0.000 | 200.0 |
| execution_slip | monitor_corrected | 5 | 0.600 | 0.0746 | 4.00 | 0.976 | 106.0 |

## 稳定下来的结论

- `NeedlePick` 现在可以作为一个可复现的 failure-aware surgical task benchmark：clean 成功，perturbed 失败，monitor 部分恢复。
- `action_noise` 是当前 runtime recovery 最擅长处理的 failure type。
- `execution_slip` 是中等难度 failure，monitor 可以显著改善但不能完全解决。
- `action_dropout` 是当前策略的主要短板，说明仅靠 oracle override 不足以恢复观测/动作中断类 failure。
- 故障难度排序在 3 seed 和 5 seed 中保持一致：`action_noise` < `execution_slip` < `action_dropout`。

## 重要限制

- 5 seed 仍然是 early-stage evidence，不是最终统计显著性结果。
- recovery 仍然是 oracle override，不是 learned recovery policy。
- nominal monitor 仍有平均 1 次触发，false intervention 尚未完全消除。
- action_dropout 失败表明下一步需要 phase-aware recovery 或 contact-aware recovery，而不是继续拉长 window。

## 可以写进申请材料的表述

> In a 5-seed SurRoL NeedlePick pilot, clean scripted execution succeeds consistently while action-corrupted execution fails under action noise, dropout, and slip. A simple runtime recovery layer restores action-noise failures from 0/5 to 5/5 and partially recovers execution slip from 0/5 to 3/5, while action dropout remains difficult. These results suggest that failure-aware recovery is feasible but strongly failure-type dependent, motivating phase-aware and uncertainty-calibrated recovery policies.

## 下一步

1. 做 phase-aware recovery：approach、grasp、lift/transfer 阶段用不同恢复动作。
2. 对 `action_dropout` 失败 seed 做 trajectory plot，确认卡在抓取前、接触中还是 lift 后。
3. 加 learned risk score / calibrated uncertainty，替代固定规则 trigger。
4. 扩展到第二个 SurRoL 任务，比如 `GauzeRetrieve` 或 `NeedleRegrasp`。
