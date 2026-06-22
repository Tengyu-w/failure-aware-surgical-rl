# 当前可信基线与阶段目标锁定：Round 41

## 目的

本文件用于冻结当前项目基线，避免后续实验把“已验证有效”“候选但未定”“闭环失败已撤回”的模块混在一起。

对照 `constraint_surgical_rl_full_work_compendium_20260618.docx`，项目已经从抽象 3D navigation proxy 升级到 SurRoL 仿真中的视觉可靠性监督原型。当前主线不是证明一个全新手术机器人控制策略优于原论文，而是在已有策略外部建立 failure-aware / risk-aware supervisor。

## 当前主任务定义

- 平台：SurRoL，主要任务为 `NeedleReachRL-v0`，另有 NeedlePick / GauzeRetrieve / NeedleRegrasp / PickAndPlace 的扩展尝试。
- 策略输入：`render_proprio_vision`，7 维 proprioception + 201 维 RGB 池化视觉特征，共 208 维。
- 可靠性目标：在自动执行、自动恢复、人工复核和中止候选之间做风险分流。
- 核心评价：总体自动成功数、复核率、自动覆盖率、覆盖内成功率、自动失败数、平均最终距离。

## 当前推荐基线

### 主基线 A：视觉风险路由 + 旧恢复记忆 + 高风险复核

用途：作为当前最稳的 SurRoL 视觉风险分流基线。

组件：

- Policy：`runs/surrol_visual_dagger_round31_seed50710/model_dagger_round2.zip`
- Risk head：`runs/surrol_visual_dagger_round31_seed50710/visual_action_risk_head/visual_action_risk_head.npz`
- Recovery memory：`runs/surrol_visual_dagger_round33_ood20_seed51000/visual_recovery_memory_augmented/visual_recovery_memory.npz`
- Routing：`selective_memory_guarded`
- Risk threshold：0.4
- Review threshold：0.6

主要证据：

| 条件 | Episodes | 成功 | 复核率 | 自动覆盖 | 自动成功 | 覆盖内成功率 |
|---|---:|---:|---:|---:|---:|---:|
| pure policy | 50 | 3 | 0% | 100% | 3 | 6.0% |
| guarded + review 0.6 | 50 | 9 | 74% | 26% | 9 | 69.2% |

解释：它牺牲了自动覆盖率，但显著提高了被允许自动处理轨迹中的成功率。这是“不能一味 recovery”的核心证据。

### 主基线 B：主基线 A + learned temporal stagnation

用途：作为当前最接近 ECG 式分流思想的候选主线。

组件：

- 主基线 A
- Stagnation head：`runs/surrol_visual_temporal_stagnation_round35/temporal_stagnation_head.npz`
- 输入：risk、memory distance、恢复历史和短窗风险趋势，不读取 privileged goal 或 oracle action。

50-seed 在线结果：

| 条件 | 成功 | 复核率 | 自动覆盖 | 自动成功 | 自动失败 | 覆盖内成功率 |
|---|---:|---:|---:|---:|---:|---:|
| tiered routing | 15/50 | 54% | 23/50 | 15 | 8 | 65.2% |
| + learned stagnation | 15/50 | 62% | 19/50 | 15 | 4 | 78.9% |

解释：stagnation head 没有增加成功数，但减少了自动失败数，保留了全部自动成功。这是当前最像“风险复核/搁置”的监督模块。

## 可保留但暂不替换主线的候选

### 严格拆分视觉适配器

路径：`runs/surrol_visual_denoising_adapter_round40_strict_split/visual_denoising_adapter.npz`

证据：

- 训练/验证/测试配对数：624 / 324 / 312
- 测试腐蚀 MSE：0.017129 -> 0.0000151
- 腐蚀 MSE 降低：99.91%
- 干净输入 MSE：0.00000385

结论：离线降噪成立，但不能单独证明闭环可靠性提升。

### 新风险头

路径：`runs/surrol_visual_dagger_round40_adapter_space/visual_action_risk_head/visual_action_risk_head.npz`

离线证据：

- AUROC：0.9364
- AUPRC：0.8928
- Recall：97.5%
- 阈值：0.35

20-seed 四格消融：

| 风险头 + 恢复记忆 | 成功 | 复核 | 自动覆盖 | 自动成功 | 自动失败 | 覆盖内成功率 |
|---|---:|---:|---:|---:|---:|---:|
| 旧风险 + 旧记忆 | 6/20 | 12/20 | 8/20 | 6 | 2 | 75.0% |
| 新风险 + 旧记忆 | 4/20 | 16/20 | 4/20 | 4 | 0 | 100.0% |

结论：新风险头更保守，可能减少自动失败，但会降低覆盖率和总自动成功数。暂不替换主线，后续作为保守分流候选继续验证。

## 已撤回或不能作为主结果的模块

### 新 adapter-space recovery memory

路径：`runs/surrol_visual_dagger_round40_adapter_space/visual_recovery_memory/visual_recovery_memory.npz`

离线动作误差看似改善：

- 测试 action L2：0.2275
- 全局平均动作 L2：0.2688

但闭环失败：

| 风险头 + 恢复记忆 | 成功 | 复核 | 自动覆盖 | 自动成功 | 自动失败 | 覆盖内成功率 |
|---|---:|---:|---:|---:|---:|---:|
| 旧风险 + 新记忆 | 4/20 | 7/20 | 13/20 | 4 | 9 | 30.8% |
| 新风险 + 新记忆 | 0/20 | 9/20 | 11/20 | 0 | 11 | 0.0% |

撤回原因：

- 新记忆主要来自旧 DAgger 观测的离线适配器映射，不是真实在线适配器轨迹。
- 真实在线高 action-gap 增强样本只有 2 条。
- 离线动作 L2 改善没有转化为闭环可靠性。

决策：不得纳入主线，不再用于正式结论。

### Adapter-specific stagnation head

结论：已尝试，但在线触发无明显收益，不纳入当前主线。

### PPO/RL 重新训练

结论：当前 PPO 尝试不稳定，不能作为主成果。项目主线暂时是 supervisor / routing / recovery，而不是宣称训练出强 RL policy。

### PickAndPlace / NeedleRegrasp 正式纳入

结论：复杂第三任务已尝试，但 clean oracle 或环境稳定性不足，暂时记录为 blocked，不硬凑正式实验。

## 已完成能力清单

| 能力 | 状态 | 证据 |
|---|---|---|
| SurRoL 部署与 WSL/E 盘环境 | 完成 | SurRoL 多轮实验可运行 |
| 多 seed 验证 | 完成 | 10/20/50-seed 多组结果 |
| Phase-aware recovery | 完成 | NeedlePick/GauzeRetrieve jaw-stuck 与 phase replan 报告 |
| Risk-aware routing | 完成 | auto/recovery/review/abort_candidate 路由 |
| Learned risk head | 完成基础版 | AUROC 0.9484 的旧风险头；0.9364 的新风险头 |
| Recovery memory | 完成旧基线 | 旧记忆在 50-seed 中提升选择性成功 |
| Temporal stagnation | 完成基础版 | 自动失败 8 -> 4 |
| 真实渲染视觉输入 | 完成基础版 | 208D `render_proprio_vision` |
| 视觉腐蚀测试 | 完成 | noise/brightness/occlusion/blackout/mixed |
| 视觉适配器 | 完成离线版 | 严格测试降噪 99.91% |
| 新 adapter-space recovery memory | 撤回 | 20-seed 闭环自动失败过多 |

## 当前最大缺口

1. 缺少足量真实在线 adapter-space 高 action-gap 轨迹。
2. Recovery memory 仍依赖旧视觉空间，适配器空间的新记忆失败。
3. 视觉特征仍是手工 RGB 池化，不是 CNN/keypoint/RAM/VLM。
4. 多任务统一协议尚未完全成型。
5. 不可逆风险仍是 proxy，缺少真实接触力或组织损伤证据。

## 下一阶段：阶段 2 入口

阶段 2 的目标不是训练新模型，而是采集干净、可分割、真实在线的 adapter observation 数据。

建议协议：

- 模式：`collect_surrol_visual_ood_recovery_dagger.py --collection-mode all_steps`
- Policy：`runs/surrol_visual_dagger_round31_seed50710/model_dagger_round2.zip`
- Adapter：`runs/surrol_visual_denoising_adapter_round40_strict_split/visual_denoising_adapter.npz`
- 任务：先 `NeedleReachRL-v0`
- 条件：clean + mixed corruption
- 记录：observation、policy action、oracle action、action gap、risk、memory distance、goal distance
- 拆分：按 seed 分 train / validation / test，避免同一 episode 窗口跨集合
- 目标：先获得足够 high action-gap 样本，再考虑重训 recovery memory

成功标准：

- 真实在线样本数足够，不再只靠离线映射。
- high action-gap 样本覆盖恢复阶段，而不只是短 smoke 中的少量异常。
- 数据集能支持独立 validation/test，不出现 Round 40 那类闭环反例后才发现数据错位。

## 当前对外表述建议

可以说：

> We developed a SurRoL-based failure-aware reliability supervisor that routes visual-policy rollouts into auto-execution, memory-based recovery, and human review. Multi-seed experiments show that risk-aware routing improves selective success and temporal stagnation detection reduces unsafe auto-recovery failures. Recent adapter experiments further show that offline visual correction is insufficient for reliable closed-loop recovery, motivating online adapter-space data collection.

不应说：

> 我们已经显著提升了 SurRoL 原始论文策略。

也不应说：

> 视觉适配器已经解决了视觉不确定性。

更准确的定位是：

> 当前项目证明了一个外接可靠性监督层的博士课题雏形，并且已经有正结果、负结果和下一步数据闭环。

