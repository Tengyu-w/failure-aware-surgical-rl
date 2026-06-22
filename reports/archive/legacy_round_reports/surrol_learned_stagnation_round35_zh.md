# SurRoL Learned Temporal Stagnation Head：Round 35

## 目标

固定恢复预算在 Round 34 中拦下失败的同时误拒了成功轨迹。本轮训练一个轻量时序停滞头，尝试只根据线上可观测的风险历史和路由历史识别“继续恢复仍可能失败”的轨迹。

## 输入与标签

时序头使用 8 步短窗，共 10 个特征：

- 当前 step 比例、当前 learned risk、恢复记忆 embedding 距离。
- 累计恢复比例、连续恢复比例。
- 近期风险均值、标准差和斜率。
- 近期高风险比例和恢复动作比例。

模型不读取 `achieved_goal`、`desired_goal` 或 oracle 动作。标签为自动候选 episode 最终是否失败。

## 数据划分

- 训练：seed 511xx-512xx，共 11 个自动候选 episode，其中 4 个失败。
- 阈值选择：seed 513xx，共 7 个自动候选，其中 1 个失败。
- 离线测试：seed 514xx-515xx，共 13 个自动候选，其中 1 个失败。
- 全新在线固定验证：seed 51600-51719，共 50 个 episode。

划分以 episode/seed 为单位，同一轨迹的时间窗不会跨集合。

## 模型

- 标准化特征上的带 L2 正则逻辑回归。
- 最早触发 step：15。
- 阈值：0.93157，由 513xx 验证集固定。
- 线上路由：超过阈值时转 `human_review_learned_stagnation`。

离线 514xx-515xx 测试得到 AUROC 1.0、失败召回 1.0、FPR 0，但测试集中只有 1 个失败，不能把该数字视为稳定泛化结论。

## 50-seed 在线结果

| 条件 | 总体自动成功 | 复核率 | 自动覆盖 | 覆盖内成功 | 自动失败 |
|---|---:|---:|---:|---:|---:|
| Round 33 分级路由 | 15/50 = 30% | 54% | 23/50 = 46% | 15/23 = 65.2% | 8 |
| 分级路由 + learned stagnation | 15/50 = 30% | 62% | 19/50 = 38% | 15/19 = 78.9% | 4 |

覆盖内成功率 95% Wilson 区间：

- 原分级路由：44.9%-81.2%。
- learned stagnation：56.7%-91.5%。

逐 seed 配对结果：

- 4 条原本自动失败的轨迹被转为人工复核。
- 15 条自动成功轨迹全部保留。
- 仍有 4 条自动失败未被识别。
- 在线失败召回率为 50%，对成功候选的误拒率为 0%。

## 与固定预算的区别

固定预算在另一组 50 seed 上拦下 1 条失败，但也误拒 2 条成功。learned stagnation 在本轮 50 seed 上拦下 4 条失败且未误拒成功，因此方向优于硬预算。不过两者使用的在线 seed 不同，不能把该差异当作严格的同场统计比较。

## 结论

短窗风险趋势比固定恢复次数更有能力区分“长但最终成功”和“长且不收敛”的恢复过程。它将自动失败减半，同时保留自动成功数量，是当前项目中第一个没有观察到自主成功损失的停滞路由模块。

证据仍有限：训练只有 4 个失败 episode，在线验证也只出现 8 个自动失败候选。当前结果支持继续扩大验证，不支持临床或不可逆动作授权。

## 下一步

1. 在视觉腐蚀条件下验证该 head，检查风险趋势是否发生分布漂移。
2. 记录本体和视觉 embedding 的逐步变化，加入真正的 observable progress 特征。
3. 对剩余 4 条漏检失败做错误分型，判断是视觉定位误差、恢复动作偏差还是终止阈值问题。
4. 使用更多失败 episode 重新训练和校准，并报告 calibration 与 coverage-risk 曲线。

## 产物

- `scripts/surrol_temporal_stagnation.py`
- `scripts/train_surrol_temporal_stagnation_head.py`
- `scripts/evaluate_surrol_visual_risk_routing.py`
- `runs/surrol_visual_temporal_stagnation_round35/`
- `runs/surrol_visual_round35_learned_stagnation_fixed50_summary.csv`
