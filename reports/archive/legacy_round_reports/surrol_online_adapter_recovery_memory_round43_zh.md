# SurRoL 在线 Adapter-Space Recovery Memory：Round 43

## 目的

Stage 3 的目标是修复 Round 40 暴露的数据错位问题：不再使用旧 DAgger 视觉特征的离线 adapter 映射，而是只用 Round 42 采集到的真实在线 adapter-space 轨迹训练 recovery memory。

本轮仍使用 KNN recovery memory，因此它是对“数据来源修正是否足够”的检验，而不是新模型结构升级。

## 数据

使用 Round 42 真实在线 adapter-space 数据：

| 条件 | Episodes | Steps | High action-gap |
|---|---:|---:|---:|
| clean | 20 | 943 | 546 |
| mixed p=0.35 | 20 | 970 | 596 |
| 合计 | 40 | 1913 | 1142 |

Split 规则：

- train：`seed % 4 in {0,1}`
- validation：`seed % 4 == 2`
- test：`seed % 4 == 3`

只使用 high action-gap 状态训练和测试 recovery memory。

## 离线动作误差

| 训练数据 | PCA | Train memory steps | Test action L2 | Global mean L2 | 结论 |
|---|---:|---:|---:|---:|---|
| clean only | 32 | 274 | 0.3759 | 0.3449 | 差于全局均值 |
| mixed only | 32 | 309 | 0.4334 | 0.4224 | 差于全局均值 |
| clean + mixed | 16 | 583 | 0.3940 | 0.3832 | 差于全局均值 |
| clean + mixed | 32 | 583 | 0.3800 | 0.3832 | 略优，但幅度极小 |
| clean + mixed | 64 | 583 | 0.3829 | 0.3832 | 基本打平 |

离线结论：真实在线数据解决了数据来源问题，但简单 KNN 仍没有学到强局部恢复动作结构。最佳结果只比全局平均动作略好，不能凭离线 L2 采用。

## 闭环 smoke

同 seed 53300-53303，mixed p=0.35：

| 记忆 | 成功 | 复核 | 自动覆盖 | 自动成功 | 自动失败 |
|---|---:|---:|---:|---:|---:|
| 旧 augmented memory | 1/4 | 3/4 | 1/4 | 1 | 0 |
| 在线 adapter memory | 1/4 | 3/4 | 1/4 | 1 | 0 |

4-seed smoke 说明新在线记忆没有像 Round 40 新记忆那样立即造成自动失败，但样本太少，不能证明提升。

## 20-seed 闭环验证

共同条件：

- seed：52500-52519
- Adapter：strict split visual adapter
- Risk head：旧 risk head，risk threshold 0.4
- Review threshold：0.6
- Vision corruption：mixed p=0.35，severity 0.25
- Routing：`selective_memory_guarded`

| Recovery memory | 成功 | 复核 | 自动覆盖 | 自动成功 | 自动失败 | 覆盖内成功率 | 平均最终距离 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 旧 augmented memory | 6/20 | 12/20 | 8/20 | 6 | 2 | 75.0% | 0.0882 |
| Round 40 bad new memory | 4/20 | 7/20 | 13/20 | 4 | 9 | 30.8% | 0.1127 |
| Round 43 online memory | 2/20 | 18/20 | 2/20 | 2 | 0 | 100.0% | 0.0838 |

## 解释

Round 43 在线记忆修复了 Round 40 的主要危险：它没有大规模误放行自动失败。但它变得过于保守，几乎所有 high-risk 状态都被 OOD gate 转入人工复核。

关键现象：

- 20-seed 中在线记忆的 mean override rate 为 0。
- 自动成功的 2 条轨迹都是 `auto_execute`，不是 memory recovery 带来的成功。
- 因此它不是有效 recovery memory，只是一个强复核过滤器。

## 结论

Stage 3 完成，但结果为负：

1. 真实在线 adapter-space 数据采集是必要的，避免了 Round 40 新记忆的危险误放行。
2. 仅靠 PCA + KNN 的 recovery memory 仍不足以恢复复杂高 action-gap 状态。
3. Round 43 在线 memory 不应替换旧 augmented memory。
4. 当前主线继续保留旧 augmented memory；在线 adapter memory 只作为反例和下一步建模依据。

## 下一步

Stage 4 不应继续盲目扩大 KNN memory，而应升级风险路由：

- 保留旧 augmented memory 作为主 baseline。
- 对在线 adapter memory 的失败原因做 embedding/OOD 分析。
- 比较更保守 risk head、recovery budget、temporal stagnation 的组合。
- 如果继续做 recovery memory，应尝试 learned action head 或按 phase/condition 分层，而不是单一全局 KNN。

## 产物

- `scripts/train_surrol_online_adapter_recovery_memory.py`
- `runs/surrol_visual_online_adapter_recovery_memory_round43_combined/`
- `runs/surrol_visual_online_adapter_recovery_memory_round43_combined_pca64/`
- `runs/surrol_visual_round43_online_memory_smoke_mixed_seed53300/`
- `runs/surrol_visual_round43_old_memory_smoke_mixed_seed53300/`
- `runs/surrol_visual_round43_online_memory_20seed_mixed_seed52500/`

