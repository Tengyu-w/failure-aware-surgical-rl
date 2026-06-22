# SurRoL 视觉腐蚀与腐蚀感知恢复记忆：Round 36-37

## 目标

1. 验证 Round 35 learned stagnation head 在视觉扰动下是否仍有效。
2. 检查视觉腐蚀模拟是否符合相机帧更新逻辑。
3. 通过定向 OOD DAgger 扩充 mixed corruption 下的恢复记忆。

## Round 36：视觉腐蚀诊断

### 初始结果

在 mixed corruption（概率 0.35、强度 0.25）下，旧实现的 30-seed 结果为：

- 自动覆盖 1/30，成功 1/30。
- 29/30 转人工复核。
- 19 条由 embedding OOD 拒绝，10 条由 risk >= 0.6 拒绝。
- 视觉变化 95 分位为 0.1807，而 clean 为 0.0059；本体变化基本不变。

Gaussian noise 与 occlusion 的 10-seed 诊断均为 100% 复核，brightness shift 为 90% 复核。

### 模拟实现问题

环境每 4 步更新一次渲染帧，但旧实现会在每个控制步重新随机生成腐蚀和图像噪声。因此同一缓存帧会出现不真实的逐步闪烁。

本轮将腐蚀和图像特征绑定到实际帧更新：同一缓存帧内重复使用同一组视觉特征。对应单元测试验证了缓存帧内特征完全一致。

### 修正后结果

在新的 30 个 seed 上：

| 条件 | 自动成功 | 复核率 | 自动覆盖 | 覆盖内成功 |
|---|---:|---:|---:|---:|
| Clean + learned stagnation | 10/30 | 66.7% | 10/30 | 100% |
| Mixed + tiered routing | 3/30 | 90% | 3/30 | 100% |
| Mixed + learned stagnation | 3/30 | 90% | 3/30 | 100% |

帧级缓存将 mixed 覆盖从 3.3% 提高到 10%，但视觉分布漂移仍使 90% 轨迹进入复核。learned stagnation 没有额外作用，因为轨迹更早被 OOD/risk 层截断。

## Round 37：腐蚀感知 OOD DAgger

### 定向采集

- 训练 seed：52100-52119。
- mixed corruption：概率 0.35、强度 0.25。
- 20 个 episode 中 17 个触发 OOD 干预。
- 收集 86 个纠正步骤，其中 50 个 action gap >= 0.25。
- 采集轨迹成功率（含 oracle，仅作数据采集诊断）：90%。

将 50 个腐蚀样本与原 97 个 clean OOD 样本共同加入记忆：

- 恢复记忆从 270 扩为 320 条。
- 原 clean 奇数-seed 留出动作 L2 误差为 0.2376。
- 该误差略优于上一增强记忆的 0.2437，但仍不及最初小记忆的 0.2267。

### 50-seed 新旧记忆配对

| 条件 | 记忆 | 自动成功 | 复核率 | 自动覆盖 | 覆盖内成功 | 自动失败 |
|---|---|---:|---:|---:|---:|---:|
| Clean | 旧记忆 | 11/50 = 22% | 68% | 16/50 = 32% | 11/16 = 68.8% | 5 |
| Clean | 腐蚀增强记忆 | 13/50 = 26% | 64% | 18/50 = 36% | 13/18 = 72.2% | 5 |
| Mixed | 旧记忆 | 2/50 = 4% | 96% | 2/50 = 4% | 2/2 = 100% | 0 |
| Mixed | 腐蚀增强记忆 | 4/50 = 8% | 92% | 4/50 = 8% | 4/4 = 100% | 0 |

Mixed 覆盖内成功率的样本极少：新记忆的 4/4 对应 95% Wilson 区间为 51.0%-100%，不能解释为稳定 100%。

## 结论

1. 旧视觉腐蚀存在同帧闪烁问题，修正后模拟更接近帧级传感器扰动。
2. 安全路由面对视觉漂移会主动降低自主覆盖，没有观察到 mixed 下的自动失败爆发。
3. 腐蚀感知 DAgger 将 mixed 自动覆盖由 4% 提高到 8%，同时 clean 指标没有恶化，但绝对覆盖仍然很低。
4. 当前瓶颈不是停滞头，而是上游 RGB embedding 和 recovery memory 对视觉变化缺乏不变性。

这些结果属于仿真鲁棒性证据，不是临床视觉系统或手术安全验证。

## 下一步

1. 训练具备颜色/亮度/遮挡不变性的视觉 encoder，而不是继续向 3-NN 记忆堆样本。
2. 分别校准 clean 与 corruption 的 risk/OOD 分数，报告 condition-aware coverage-risk 曲线。
3. 在新 embedding 上重新训练 risk head、recovery memory 和 stagnation head，避免跨 embedding 复用阈值。
4. 保留帧级腐蚀缓存作为后续所有实验的默认实现。

## 产物

- `scripts/train_surrol_ppo_failure_aware.py`
- `scripts/collect_surrol_visual_ood_recovery_dagger.py`
- `scripts/train_surrol_visual_recovery_memory.py`
- `runs/surrol_visual_round37_corruption_augmented_memory/`
- `runs/surrol_visual_round37_corruption_memory_fixed50_summary.csv`
