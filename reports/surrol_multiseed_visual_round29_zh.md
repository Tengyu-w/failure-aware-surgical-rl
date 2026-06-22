# SurRoL 多 Seed 奖励筛选与真实视觉验证（Round 28–29）

## 一句话结论

完成了 progress scale 的多 seed 筛选和真实 RGB 配对腐蚀验证，但所有 learned PPO 策略成功率仍为 0%。`scale=10` 在伪视觉中缩短了最终距离，却未在真实 RGB 中复现；强视觉腐蚀只引起约 0.001–0.002 的最终距离变化，说明当前策略虽然接收图像特征，却主要依赖拼接的特权状态向量。

## Round 28：伪视觉奖励筛选

配置：`NeedleReachRL-v0`，每个 scale 3 个独立训练 seeds，每个 checkpoint 1024 timesteps，并在固定的 3 个未见评估 seeds 上测试。表中标准差先按 checkpoint 聚合，再在训练 seeds 间计算。

| progress scale | 训练 seeds | 评估 episodes | 成功率 | 最终距离（均值±seed std） | 净距离进步 |
|---:|---:|---:|---:|---:|---:|
| 0 | 3 | 9 | 0.0% | 0.4224 ± 0.1269 | 0.0108 |
| 10 | 3 | 9 | 0.0% | 0.2078 ± 0.0888 | 0.2253 |
| 30 | 3 | 9 | 0.0% | 0.2984 ± 0.0368 | 0.1347 |
| 50 | 3 | 9 | 0.0% | 0.2760 ± 0.0889 | 0.1572 |

四组均为 0% 成功。按预先固定的‘成功率、最终距离、净进步’排序，`scale=10` 是距离代理上的候选，而不是成功策略。其三个训练 seed 的平均最终距离约为 0.233、0.302、0.089，仍有明显 seed 敏感性。

## Round 29：真实 RGB 迁移验证

使用新训练 seeds `48000–48002`，比较 `scale=0` 与伪视觉候选 `scale=10`。每个 checkpoint 训练 1024 timesteps；训练图像为 mixed corruption（概率 0.35，severity 0.25），`vision_stride=4`。clean 与 mixed-paired 使用相同评估 seeds `49000–49001`。

| 条件 | scale | 成功率 | 最终距离（均值±seed std） | 最小距离 | 净距离进步 |
|---|---:|---:|---:|---:|---:|
| clean | 0 | 0.0% | 0.3546 ± 0.1014 | 0.3492 | 0.1048 |
| clean | 10 | 0.0% | 0.3916 ± 0.0231 | 0.3834 | 0.0679 |
| mixed-paired | 0 | 0.0% | 0.3536 ± 0.1012 | 0.3487 | 0.1059 |
| mixed-paired | 10 | 0.0% | 0.3934 ± 0.0229 | 0.3837 | 0.0661 |
| mixed-external | 0 | 0.0% | 0.3581 ± 0.0962 | 0.3518 | 0.1013 |
| mixed-external | 10 | 0.0% | 0.3938 ± 0.0229 | 0.3836 | 0.0656 |

真实 RGB clean 条件下，稀疏基线最终距离 0.3546，`scale=10` 为 0.3916。候选奖励没有复现伪视觉优势，因此本轮拒绝把 scale 10 升级为默认配置。

## 配对视觉腐蚀效应

| scale | 平均 Δ最终距离（corrupt-clean） | seed std | 平均腐蚀幅度 |
|---:|---:|---:|---:|
| 0 | -0.0010 | 0.0008 | 0.1469 |
| 10 | +0.0018 | 0.0010 | 0.1468 |

图像平均绝对腐蚀幅度约 0.147，但最终距离变化只有约千分之一。结合此前同帧动作敏感性非零的结果，当前证据更支持‘图像通道被网络使用但不是任务必需’，而不是‘模型对视觉腐蚀高度鲁棒’。这是下一步必须去除 achieved/desired goal 特权输入、建立视觉必需观测的依据。

## 工程与可靠性改进

- 新增 `vision_stride`、帧缓存、`visual_frame_age` 与 `visual_frame_updated`；真实 RGB 训练吞吐从约 5–6 fps 提升到约 9 fps。
- 新增可恢复的多 seed 训练/评估 runner，每个模型、日志和 CSV 独立保存。
- 识别 SurRoL `p.disconnect()` 的全局连接生命周期问题；正式 runner 默认使用独立子进程，避免跨 seed 污染。
- 新增训练 seed 层汇总，避免把同一 checkpoint 的多个 episode 误当独立训练样本。
- 新增 clean/corrupt 同 seed 配对比较，并保留不同 seeds 的 external corruption 结果。

## 证据边界

- 所有策略成功率仍为 0%，只能讨论距离代理、稳定性和视觉依赖，不能宣称 learned policy 已有效。
- 每个真实 RGB checkpoint 仅评估 2 个 episodes；3 个训练 seeds 适合筛选，不足以给出紧置信区间。
- 当前视觉是手工统计与池化特征，不是 CNN、关键点检测器、RAM 或 VLM。
- 观测仍包含 achieved/desired goal 和完整状态，造成视觉信息可被绕过。
- 本轮仅在 NeedleReach 课程任务做奖励筛选；NeedlePick、GauzeRetrieve 和 PickAndPlace learned policy 仍未解决。
- 全部证据来自仿真研究原型，不对应临床或实体机器人有效性。

## 下一步

1. 新增 `render_proprio_vision`：只保留机器人本体状态和图像特征，移除 achieved/desired goal 特权输入。
2. 提高图像空间表达力，并逐步替换为小型 CNN/关键点检测器；用 clean/corrupt 动作与任务差异验证视觉确实成为必需信号。
3. 在 NeedleReach 先获得稳定非零成功率，再迁移到 NeedlePick；否则复杂任务只会放大训练失败。
4. 将视觉扰动敏感性、策略不确定性和 risk routing 接通，使 high-uncertainty 帧触发 review/abort，而非盲目恢复。
5. 保留 PickAndPlace 为复杂任务门槛，待视觉必需课程任务通过后再做正式 3-seed 训练。

## 核心产物

- `runs/surrol_progress_multiseed_round28/scale_summary.csv`
- `runs/surrol_progress_multiseed_round28/seed_summary.csv`
- `runs/surrol_render_progress_round29/clean_scale_summary.csv`
- `runs/surrol_render_progress_round29/mixed_paired_scale_summary.csv`
- `runs/surrol_render_progress_round29/paired_condition_scale_summary.csv`
- `runs/surrol_render_progress_round29/manifest_clean.json`
- `runs/surrol_render_progress_round29/manifest_mixed_paired.json`
