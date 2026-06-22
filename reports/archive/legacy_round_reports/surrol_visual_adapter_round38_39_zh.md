# SurRoL 视觉去噪适配器与再校准：Round 38-39

## 目标

在不改变现有 PPO、risk head 和 recovery memory 输入维度的前提下，学习一个 corruption-invariant 视觉适配器，将 Gaussian noise、brightness shift 和 occlusion 后的 201 维手工图像特征映射回 clean 特征空间。

## 配对数据

- seed 52400-52419，共 20 个 oracle 数据采集 episode。
- 每个实际渲染帧生成 clean identity pair，以及三种腐蚀、三个强度（0.15、0.25、0.4）的配对。
- identity pair 重复 3 次，用于限制 clean 输入漂移。
- 总计 1260 个 201 维输入/clean-target 对。
- 偶数 seed 训练，奇数 seed 测试。

oracle 仅用于移动到不同仿真状态；视觉适配器的监督来自同一 RGB 帧的 clean/corrupt 配对。

## 模型

适配器是带 L2 正则的残差线性映射：

`adapted = corrupted_feature + blend * predicted_residual`

输出仍为 201 维，与原 7 维本体状态拼接后保持 208 维策略接口。

## 离线结果

| 指标 | 结果 |
|---|---:|
| 训练 pair | 636 |
| 测试 pair | 624 |
| 选定 blend | 1.0 |
| 腐蚀 MSE before | 0.017301 |
| 腐蚀 MSE after | 0.0000127 |
| 腐蚀 MSE 降幅 | 99.93% |
| Clean MSE after | 0.00000275 |

高离线降幅部分来自当前 RGB 池化特征和模拟腐蚀较接近线性关系，不能直接外推到真实相机或 CNN 特征。

## 50-seed 闭环结果

使用原 Round 33 clean-oriented recovery memory，seed 52500-52629：

| 条件 | Adapter | 自动成功 | 复核率 | 自动覆盖 | 覆盖内成功 | 自动失败 |
|---|---|---:|---:|---:|---:|---:|
| Clean | 无 | 9/50 = 18% | 76% | 12/50 = 24% | 9/12 = 75.0% | 3 |
| Clean | 有 | 10/50 = 20% | 72% | 14/50 = 28% | 10/14 = 71.4% | 4 |
| Mixed | 无 | 3/50 = 6% | 94% | 3/50 = 6% | 3/3 = 100% | 0 |
| Mixed | 有 | 8/50 = 16% | 74% | 13/50 = 26% | 8/13 = 61.5% | 5 |

Adapter 将 mixed 自动成功从 3 条提高到 8 条，并将平均最终距离从 0.1289 降到 0.0944；但它同时将 mixed 自动失败从 0 增加到 5。该结果是“覆盖恢复伴随风险增加”，不能只报告成功率提升。

Clean 条件下总体变化较小：成功增加 1 条、覆盖增加 2 条、自动失败增加 1 条。

## Round 39：Adapter-specific stagnation

旧 stagnation head 在 adapter 路径上没有触发，因此按 adapter mixed 轨迹重新训练：

- 训练只有 6 个自动候选，其中 1 个失败。
- 验证 7 个候选，其中 4 个失败。
- 离线测试 6 个候选，其中 2 个失败；识别 1 个，成功误拒为 0。
- 阈值达到 0.9971，反映训练正样本过少。

在 seed 52800-52829 的在线 smoke 中：

| 条件 | 自动候选 | 成功 | 失败 | 复核 |
|---|---:|---:|---:|---:|
| Adapter + tiered routing | 4 | 2 | 2 | 26 |
| Adapter + new stagnation | 4 | 2 | 2 | 26 |

新 head 没有触发，未产生在线增益，因此不纳入主方法。

## 结论

视觉适配器有效缓解了 mixed corruption 导致的过度 OOD 拒绝，并显著提高自主覆盖；但原 risk/stagnation 校准无法自动适应新的视觉分布，导致新增自动失败。

当前推荐 operating point 仍取决于风险偏好：

- 极保守模式：不使用 adapter，mixed 覆盖低但本轮无自动失败。
- 研究型自主模式：使用 adapter，成功和覆盖更高，但必须接受并继续处理自动失败。

该适配器是仿真手工特征上的研究原型，不代表真实手术图像鲁棒性。

## 下一步

1. 在 adapter 输出空间重新采集足够的失败 episode，而不是仅用 1 个失败训练 stagnation head。
2. 联合重训 risk head、recovery memory 和 stagnation head，并保持新的独立 seed 测试集。
3. 将线性 adapter 升级为小型 CNN/关键点 encoder 时，重新建立全部校准阈值。
4. 增加 blackout 与未见强度，检验 adapter 是否会错误修复真正不可恢复的视觉缺失。

## 产物

- `scripts/collect_surrol_visual_corruption_pairs.py`
- `scripts/train_surrol_visual_denoising_adapter.py`
- `scripts/train_surrol_ppo_failure_aware.py`
- `runs/surrol_visual_denoising_adapter_round38/`
- `runs/surrol_visual_round38_adapter_fixed50_summary.csv`
- `runs/surrol_visual_temporal_stagnation_adapter_round39/`
