# SurRoL 保守风险路由升级：Round 44

## 目的

Stage 4 的目标不是继续扩大 recovery memory，而是在当前可信主线基础上减少自动失败：

- 保留旧 risk head
- 保留旧 augmented recovery memory
- 使用 strict-split visual adapter
- 比较 recovery budget、learned temporal stagnation 和更保守的新 risk head

核心问题：能否在不牺牲自动成功数的情况下，把自动失败降到 0？

## 实验设置

共同条件：

- seed：52500-52519
- Task：`NeedleReachRL-v0`
- Policy：`runs/surrol_visual_dagger_round31_seed50710/model_dagger_round2.zip`
- Old risk head：`runs/surrol_visual_dagger_round31_seed50710/visual_action_risk_head/visual_action_risk_head.npz`
- Old recovery memory：`runs/surrol_visual_dagger_round33_ood20_seed51000/visual_recovery_memory_augmented/visual_recovery_memory.npz`
- Adapter：`runs/surrol_visual_denoising_adapter_round40_strict_split/visual_denoising_adapter.npz`
- Routing：`selective_memory_guarded`
- Risk threshold：0.4
- Review risk threshold：0.6
- Corruption：mixed p=0.35，severity=0.25

## 20-seed 结果

| 条件 | 成功 | 复核 | 自动覆盖 | 自动成功 | 自动失败 | 覆盖内成功率 | 平均最终距离 |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline old risk + old memory | 6/20 | 12/20 | 8/20 | 6 | 2 | 75.0% | 0.0882 |
| + recovery budget 10 | 6/20 | 14/20 | 6/20 | 6 | 0 | 100.0% | 0.0823 |
| + learned stagnation | 6/20 | 14/20 | 6/20 | 6 | 0 | 100.0% | 0.0866 |
| + budget 10 + stagnation | 6/20 | 14/20 | 6/20 | 6 | 0 | 100.0% | 0.0823 |
| new risk + old memory | 4/20 | 16/20 | 4/20 | 4 | 0 | 100.0% | 0.1180 |

## 关键发现

1. Recovery budget 10 是当前最简单有效的 conservative guard。
   - 自动失败：2 -> 0
   - 自动成功：6 -> 6
   - 自动覆盖：8 -> 6
   - 复核率：60% -> 70%

2. Learned stagnation 在这批 seed 上效果与 budget 10 几乎等价。
   - 同样保留 6 条自动成功
   - 同样拦下 2 条自动失败
   - 与 budget 合并没有额外收益，说明它们主要拦截同一类长恢复失败。

3. 新 risk head 太保守。
   - 自动失败也为 0
   - 但成功数从 6 降到 4，自动覆盖从 8 降到 4
   - 暂不替换旧 risk head。

4. Stage 3 的 online adapter KNN memory 不纳入本轮主线。
   - 它安全但几乎不恢复，20-seed 只有 2/20 成功、18/20 复核。
   - 当前最优路线不是换 memory，而是在旧 memory 上加 conservative guard。

## 当前推荐路由候选

当前候选主线：

```text
old visual risk head
+ old augmented recovery memory
+ strict-split visual adapter
+ selective_memory_guarded
+ review risk threshold 0.6
+ recovery budget 10
```

理由：

- 比 baseline 更安全：自动失败 0/6，而 baseline 是 2/8。
- 不损失自动成功数：仍为 6/20。
- 比 learned stagnation 更简单、可解释、低训练依赖。
- 比新 risk head 覆盖更高、成功数更多。

Learned stagnation 可以作为备选或未来 Stage 4+ 的二级 guard，但当前不必强行加入主线。

## 与 ECG 式分流的关系

这一轮终于形成了更清楚的三段式逻辑：

- 自动执行：低风险且不需要恢复的轨迹。
- 自动恢复：风险升高但恢复次数未超预算、仍在可控范围内。
- 人工复核：高风险、OOD、恢复预算耗尽或 learned stagnation 触发。

它不是一味 recovery，而是用“恢复次数是否过多”作为行为后果风险的低成本代理。

## 局限

- 目前仍是 20-seed 固定验证，不是跨任务最终结论。
- Budget 10 是在 NeedleReach + mixed p=0.35 上验证的，需要在更多 seed 和任务上复核。
- Stagnation head 的训练失败样本仍少，不应过度解释 AUROC。
- 本轮没有解决视觉语义理解问题，仍是 RGB 池化 + adapter。

## 下一步

Stage 5 应做跨任务广度：

1. 先在 NeedlePick 和 GauzeRetrieve 上跑同一 conservative routing。
2. 对每个任务记录 clean baseline、corruption baseline、budget 10 guard。
3. 如果 clean oracle 或环境不稳定，明确标记 blocked，不硬凑。
4. 暂不再训练新的 KNN memory，除非先完成 embedding/OOD 失败分析或换 learned action head。

## 产物

- `runs/surrol_visual_round44_conservative_routing_summary.csv`
- `runs/surrol_visual_round44_oldrisk_oldmem_budget10_seed52500/`
- `runs/surrol_visual_round44_oldrisk_oldmem_stagnation_seed52500/`
- `runs/surrol_visual_round44_oldrisk_oldmem_budget10_stagnation_seed52500/`

