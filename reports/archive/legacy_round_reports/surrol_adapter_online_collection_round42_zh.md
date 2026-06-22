# SurRoL 真实在线 Adapter-Space 轨迹采集：Round 42

## 目的

Round 40 证明了一个关键负结果：把旧 DAgger 视觉特征离线映射到 adapter space 后训练 recovery memory，会在闭环中显著增加自动失败。因此本轮不训练新记忆，而是先采集真实在线 adapter-space 轨迹，解决数据来源错位问题。

本轮使用 `all_steps` 模式，在每个在线访问状态记录：

- 208 维 `render_proprio_vision` 观测
- 当前策略动作
- oracle 动作
- policy-oracle action gap
- learned risk
- recovery memory distance
- goal distance
- episode seed 与 split

Oracle 只用于离线标签，不用于部署式闭环控制。

## 采集协议

共同设置：

- Policy：`runs/surrol_visual_dagger_round31_seed50710/model_dagger_round2.zip`
- Risk head：`runs/surrol_visual_dagger_round31_seed50710/visual_action_risk_head/visual_action_risk_head.npz`
- Recovery memory：`runs/surrol_visual_dagger_round33_ood20_seed51000/visual_recovery_memory_augmented/visual_recovery_memory.npz`
- Adapter：`runs/surrol_visual_denoising_adapter_round40_strict_split/visual_denoising_adapter.npz`
- Collection mode：`all_steps`
- Task：`NeedleReachRL-v0`
- Action-gap threshold：0.25
- Split：`seed % 4 in {0,1}` train，`seed % 4 == 2` validation，`seed % 4 == 3` test

## 数据集

| 条件 | Seed range | Episodes | Steps | High action-gap | High-gap rate | 观测形状 | Split 正样本检查 |
|---|---:|---:|---:|---:|---:|---|---|
| mixed corruption p=0.35 | 53100-53119 | 20 | 970 | 596 | 61.4% | 970 x 208 | 通过 |
| clean | 53200-53219 | 20 | 943 | 546 | 57.9% | 943 x 208 | 通过 |
| 合计 | - | 40 | 1913 | 1142 | 59.7% | 208D | 通过 |

## Split 分布

### Mixed corruption p=0.35

| Split | Seeds | Steps | High action-gap | Rate | Mean gap | Max gap |
|---|---:|---:|---:|---:|---:|---:|
| train | 10 | 500 | 309 | 61.8% | 0.3026 | 0.7148 |
| validation | 5 | 220 | 129 | 58.6% | 0.3078 | 0.7048 |
| test | 5 | 250 | 158 | 63.2% | 0.3262 | 0.8095 |

### Clean

| Split | Seeds | Steps | High action-gap | Rate | Mean gap | Max gap |
|---|---:|---:|---:|---:|---:|---:|
| train | 10 | 472 | 274 | 58.1% | 0.3039 | 0.8526 |
| validation | 5 | 250 | 157 | 62.8% | 0.3312 | 0.8060 |
| test | 5 | 221 | 115 | 52.0% | 0.2712 | 0.6300 |

## 结论

阶段 2 已达到最低可用标准：

1. 观测维度正确：所有样本均为 208D。
2. clean 与 mixed 两种条件都有真实在线 adapter-space 数据。
3. train / validation / test 三个 split 都包含 high action-gap 样本。
4. high action-gap 样本总量从 Round 40 的 2 条真实在线增强样本提升到 1142 条。

这意味着下一步可以进入 Stage 3：只用真实在线 adapter-space 高 action-gap 状态训练新的 recovery memory，并用独立 test split 与闭环验证判断是否采用。

## 注意事项

- high action-gap 比例很高，说明当前视觉策略本身仍不强；新 recovery memory 的目标不是证明策略强，而是学习“什么时候该用 oracle-like recovery action”。
- clean 条件也有大量 high gap，说明 action gap 不是视觉腐蚀专属问题，也包含策略闭环漂移和接近目标后的控制失败。
- 本轮仍未证明新 recovery memory 有效；它只是提供了比离线映射更干净的数据基础。

## 产物

- `scripts/summarize_surrol_adapter_online_dataset.py`
- `runs/surrol_visual_adapter_online_mixed20_seed53100/`
- `runs/surrol_visual_adapter_online_clean20_seed53200/`
- `runs/surrol_visual_adapter_online_mixed20_seed53100/summary/adapter_online_dataset_summary.json`
- `runs/surrol_visual_adapter_online_clean20_seed53200/summary/adapter_online_dataset_summary.json`

