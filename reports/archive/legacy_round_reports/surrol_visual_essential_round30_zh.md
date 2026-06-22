# SurRoL 视觉必需策略与训练稳定性（Round 30）

## 一句话结论

项目首次得到不依赖 achieved/desired goal 特权坐标的非零成功策略：seed-fixed 评估中，三个 phase-aware BC 训练运行达到 20%/10%/10% 成功，全黑图像使最佳运行降为 0%，证明 RGB 信息对成功具有因果作用。但平均成功率仅 13.3%，训练示范又采集于全局 seed 修复前，因此视觉链路已成立，稳定且完全可复现的 learned policy 尚未成立。

## 视觉必需观测

- 新模式：`render_proprio_vision`。
- 输入只包含 7 维 PSM 本体状态和 8×8 RGB 池化特征。
- `achieved_goal`、`desired_goal` 不进入策略输入，只在环境内部用于奖励和评估。
- 输入总维度 208；目标位置必须从渲染图像中获取。
- 单元测试验证：仅改变特权目标坐标时，策略输入逐元素不变。

## Phase-aware BC

每个训练 seed 使用 30 条成功 oracle 轨迹、约 566–597 个样本；距离小于 0.12 的近目标样本权重为 4，以加强精细接近和停止阶段。

| 训练 seed | 示范步数 | 动作 MSE | clean 成功率 | 最小距离 | 最终距离 |
|---:|---:|---:|---:|---:|---:|
| 50400 | 597 | 0.000915 | 20% | 0.0587 | 0.3058 |
| 50401 | 566 | 0.000894 | 10% | 0.0556 | 0.3582 |
| 50402 | 577 | 0.001078 | 10% | 0.0531 | 0.3546 |

训练运行间成功率为 13.3% ± 4.7%。三组动作 MSE 接近，但闭环成功率仍不同，说明监督损失不能充分预测闭环可靠性。

## 视觉因果干预

对最佳训练 seed 50400 使用相同的 10 个场景 seeds，分别评估 clean、强 mixed corruption 和全黑图像。初始距离逐 episode 完全一致。

| 条件 | 成功率 | 最小距离 | 最终距离 | 净距离进步 |
|---|---:|---:|---:|---:|
| clean | 20% | 0.0587 | 0.3058 | 0.1192 |
| mixed | 20% | 0.0587 | 0.3018 | 0.1233 |
| blackout | 0% | 0.2148 | 0.2148 | 0.2103 |

强 mixed corruption 保留了 2/10 成功，说明当前池化特征对局部噪声、亮度和部分遮挡有一定稳定性。blackout 将成功率从 20% 降到 0%，最小距离从 0.059 增至 0.215，证明成功不是仅靠固定轨迹先验。blackout 的最终距离偶尔小于 clean，是因为 clean 失败轨迹会先靠近再漂走，因此此处应优先解释成功率和最小距离。

## Seeding 审计

SurRoL 任务场景使用全局 `np.random`，原始 `env.seed()` 并不会控制它。现已在 `make_env()` 和 wrapper `seed()` 中同步设置 Python/NumPy 全局 seed，并验证三个模型在同一评估 seed 上的初始距离最大差异为 0。旧评估 CSV 保留但不再用于跨模型比较。当前三套 BC 示范是在该修复前采集，属于独立训练运行，但数据场景序列不能按声明 seed 完全复现；下一轮应在修复后重采集。

## Ensemble uncertainty 反例

三个策略的动作分歧未能识别失败：mean disagreement AUC=0.0000，max disagreement AUC=0.3125。该信号在当前数据上弱于随机，不能接入自动 review/abort 阈值。

## PPO 微调反例

从 5-demo BC checkpoint 做 1024 步 PPO 微调后仍为 0/5 成功，平均最终距离由 0.383 恶化到 0.408。当前 PPO reward/value learning 仍不稳定，不能把 BC+PPO 当作改进；真正有效的结果来自 phase-aware、更多示范的视觉 BC。

## 已证明、提示与未证明

**已证明**

- RGB 图像经过渲染、压缩、腐蚀后进入策略，并影响动作。
- 移除特权目标坐标后，策略仍能在未见场景获得非零成功。
- blackout 会消除成功，图像信息具有因果作用。
- seed-fixed 后三个独立训练运行均出现非零成功，但整体成功率仍低。

**结果提示**

- 近目标样本加权和更多示范比当前短 PPO 微调更有效。
- 多数失败轨迹能接近目标但随后漂移，下一步应针对闭环纠错、停止相位和 DAgger 数据。

**仍未证明**

- 尚未得到稳定成功的 failure-aware PPO policy。
- ensemble action disagreement 已测试但失败，尚无可用的 learned uncertainty 信号接入 risk routing。
- 尚未把视觉必需策略迁移到 NeedlePick、GauzeRetrieve 或 PickAndPlace。
- 当前是手工 RGB 池化，不是 learned CNN、关键点检测器、RAM 或 VLM。

## 下一步门槛

1. 用 DAgger 收集策略偏离后的 oracle 纠正状态，特别是靠近后漂移阶段。
2. 用小型 CNN 或关键点热图替代手工池化，并保持 `render_proprio_vision` 的无特权输入约束。
3. 将三个策略的动作分歧作为 epistemic uncertainty，验证它能否提前识别失败 episode。
4. NeedleReach 至少达到 3 个训练 seeds 均非零且更稳定后，再迁移 NeedlePick。
5. PickAndPlace 继续作为复杂任务门槛，不以单次成功替代正式多 seed 证据。

## 产物

- `runs/surrol_visual_essential_round30/train_seed_summary.csv`
- `runs/surrol_visual_essential_round30/visual_condition_summary.csv`
- `runs/surrol_visual_essential_round30/aggregate.json`
- `runs/surrol_visual_essential_round30/ensemble_uncertainty_primary50400_seedfixed/ensemble_uncertainty_summary.json`
- `runs/surrol_bc_needlereach_render_proprio_rgb8_phaseweighted_30demo100_seed50400/model_bc.zip`
