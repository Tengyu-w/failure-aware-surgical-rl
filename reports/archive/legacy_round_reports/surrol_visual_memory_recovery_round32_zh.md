# SurRoL 视觉风险路由与无特权恢复记忆：Round 32

## 本轮目标

将风险路由中的 oracle 动作替换为线上可用的视觉恢复模块。恢复模块只能读取与主策略相同的 `render_proprio_vision` 观测（7 维本体状态和 8x8 RGB 池化特征），不能读取 `achieved_goal`、`desired_goal` 或 oracle 动作。

## 方法

- 风险头：沿用 step-level learned risk head，风险阈值为 0.4。
- 恢复模块：在 PCA embedding 中保存偶数 episode seed 的 173 个高风险 DAgger 样本，以 3-NN 距离加权检索恢复动作。
- 数据划分：偶数 seed 建库；奇数 seed 作为动作预测留出集。
- OOD 安全门：使用最终记忆空间的 leave-one-out 最近邻距离 75 分位（1.783）作为自动恢复边界。超过边界时停止自动动作并路由到人工复核。
- 闭环评估：NeedleReachRL-v0，seed 50900-50909，共 10 个 episode。

## 确认结果

### 离线恢复动作

| 指标 | 结果 |
|---|---:|
| 留出高风险步骤 | 158 |
| 留出 episode | 8 |
| 3-NN 平均动作 L2 误差 | 0.2267 |
| 固定平均动作 L2 误差 | 0.2683 |
| 相对改善 | 15.5% |

恢复记忆学到了观测相关信息，但动作误差仍然偏大，不能单独作为高可靠控制器。

### 闭环阈值消融

| 条件 | 成功率 | 复核率 | 自动覆盖率 | 覆盖内成功率 | 平均最终距离 | 平均接管率 |
|---|---:|---:|---:|---:|---:|---:|
| 纯策略 | 10% | 0% | 100% | 10% | 0.1020 | 0% |
| Memory, threshold 0.2 | 0% | 0% | 100% | 0% | 0.3415 | 70.6% |
| Memory, threshold 0.4 | 20% | 0% | 100% | 20% | 0.1618 | 26.1% |
| Memory, threshold 0.6 | 10% | 0% | 100% | 10% | 0.1154 | 19.4% |
| Memory, threshold 0.8 | 10% | 0% | 100% | 10% | 0.1015 | 1.2% |
| Guarded memory, threshold 0.4 | 20% | 80% | 20% | 100% (2/2) | 0.0989 | 11.7% |
| Selective oracle 上界, threshold 0.4 | 100% | 0% | 100% | 100% | 0.0146 | 15.1% |

## 解释

1. 低风险阈值导致恢复模块过度接管，并显著恶化轨迹，说明“检测到风险”不等于“当前恢复动作可信”。
2. threshold 0.4 的无保护恢复多完成了一个 seed，但平均最终距离变差，因此属于混合结果，不能只按成功率宣称提升。
3. OOD 安全门把 8 条缺乏记忆支持的轨迹送入人工复核；剩余 2 条自动轨迹均成功。这展示了选择性执行流程，但不是可靠性定论。
4. oracle 上界与视觉记忆之间的巨大差距说明当前主要瓶颈已经从“何时接管”转向“接管后如何产生精确动作”。

## 局限性

- 只有 10 个闭环 seed，`2/2` 覆盖内成功没有足够置信度。
- 记忆仅有 173 个高风险动作，覆盖范围很窄。
- 当前 RGB 特征是手工池化，不具备稳定的针尖和器械关键点定位能力。
- 风险标签来自 policy-oracle action gap；虽然线上 memory 模式不调用 oracle，但监督标签仍依赖仿真专家。
- 人工复核只是路由结果，尚未接入真实人机交互。
- 本结果是仿真研究原型，不构成手术机器人临床安全证据。

## 下一步

1. 扩充恢复记忆：针对 OOD 复核轨迹采集新的 DAgger 精细纠正数据。
2. 将固定池化视觉替换为针尖/器械关键点或小型 CNN embedding。
3. 在至少 50 个新 seed 上报告 coverage-risk 曲线、复核率、危险动作漏检率和 bootstrap 置信区间。
4. 只在恢复模块达到预设留出误差和覆盖门槛后，再提高自动恢复权限。

## 产物

- `scripts/train_surrol_visual_recovery_memory.py`
- `scripts/evaluate_surrol_visual_risk_routing.py`
- `runs/surrol_visual_dagger_round31_seed50710/visual_recovery_memory/`
- `runs/surrol_visual_dagger_round31_seed50710/visual_recovery_memory_threshold_sweep.csv`
- `runs/surrol_visual_dagger_round31_seed50710/risk_routing_selective_memory_guarded_t0p4_seed50900/`
