# SurRoL 真实渲染视觉与课程奖励消融（Round 27）

## 一句话结论

本轮确认了 RGB 渲染帧会经过真实扰动、特征压缩并改变 PPO 动作，但 `progress_reward_scale=100` 虽提高训练回报，却明显恶化 clean 评估的目标距离；因此视觉链路已从 smoke 进入可诊断实验，奖励设计仍未通过有效性验证，不能宣称 learned policy 已解决任务。

## 实验问题与配置

- 任务：`NeedleReachRL-v0`，作为 NeedlePick 前的课程任务。
- 策略：SB3 PPO，CPU，单个训练 seed `45110`，每组 2048 timesteps。
- 观测：`render_pseudo_vision`；每个控制步调用 SurRoL/PyBullet RGB render，再压缩为图像统计、亮区位置和 4x4 灰度池化特征。
- 训练扰动：mixed corruption，概率 0.35，severity 0.25。
- 对照：稀疏奖励 `scale=0` 与距离进度奖励 `scale=100`；其余配置相同。
- 评估：3 个未用于训练的固定 seeds `45200-45202`，clean 图像。

## 关键结果

| 训练奖励 | 成功率 | 初始距离 | 过程最小距离 | 最终距离 | 净距离进步 |
|---|---:|---:|---:|---:|---:|
| sparse (`scale=0`) | 0.0% | 0.4332 | 0.0984 | 0.0989 | 0.3342 |
| progress (`scale=100`) | 0.0% | 0.4332 | 0.1978 | 0.3284 | 0.1048 |

两组均未成功。进度奖励组训练日志的 episode return 从约 -37.6 到 -34.3，表面优于稀疏组约 -50；但它的最终距离更大，净进步也更小。这是明确的 surrogate reward 与任务指标错位，不能用 shaped return 代替成功率或距离评价。

## 视觉是否真的影响动作

对同一状态的同一 RGB 帧分别构造 clean/corrupted 输入，固定策略并比较动作。每个 checkpoint 检查 20 个状态。

| checkpoint | 状态数 | 平均观测 L2 变化 | 平均动作 L2 变化 | 最大动作 L2 变化 |
|---|---:|---:|---:|---:|
| sparse | 20 | 0.8412 | 0.0270 | 0.0515 |
| progress-100 | 20 | 0.8446 | 0.0179 | 0.0315 |

动作差异非零，证明图像通道不是完全未使用；但样本少、动作变化较小，也没有证明变化方向是正确或安全的。当前仍是手工图像压缩特征，不是 CNN、VLM 或 RAM 视觉语义模块。

## 已落地的工程改进

- 新增 `gaussian_noise`、`brightness_shift`、`occlusion`、`mixed` 四种 RGB 帧扰动。
- 记录 `visual_corruption_magnitude` 与实际应用的扰动类型。
- 新增有界距离进度奖励；多阶段 desired goal 切换时强制进度奖励为 0，避免伪进步。
- 评估 CSV 新增初始、最小、最终距离、净进步和累计进度奖励。
- 新增 paired visual sensitivity 诊断，直接量化视觉变化对动作的影响。

## 证据边界

- 只有 1 个训练 seed、3 个评估 seeds，不能估计训练方差。
- 两个策略均为 0% 成功，当前证据只支持“链路可运行且可诊断”，不支持“策略有效”。
- `scale=100` 已被本轮反证，不应设为默认或直接扩展到复杂任务。
- 每步 CPU/EGL 软件渲染仅约 5-6 fps，多 seed 成本高。
- NeedlePick、GauzeRetrieve、PickAndPlace 的 learned policy 仍未成功；复杂动作广度尚未达到完成标准。

## 下一轮最小消融

1. 在更快的 `pseudo_vision` 课程上比较 progress scale `0/10/30/50`，每组至少 3 seeds，只按成功率和距离选候选。
2. 将最佳候选放回真实 render 通道做 clean/corruption 验证，不再用训练 return 选模型。
3. 增加 `vision_stride` 与帧缓存，显式比较每步视觉和低频视觉，支持可承受的多 seed。
4. NeedleReach 达到稳定非零成功率后，再迁移到 NeedlePick；PickAndPlace 继续保留为复杂任务门槛，不硬报成功。
5. 后续把手工图像统计替换为小型 CNN/关键点检测器，并用预测不确定性驱动 review/abort 路由。

## 产物

- `runs/surrol_ppo_needlereach_render_sparse_2048_seed45110/model.zip`
- `runs/surrol_ppo_needlereach_render_progress100_2048_seed45110/model.zip`
- `runs/surrol_ppo_eval_needlereach_render_sparse_clean_3ep.csv`
- `runs/surrol_ppo_eval_needlereach_render_progress100_clean_3ep.csv`
- `runs/surrol_visual_sensitivity_needlereach_sparse_20states.csv`
- `runs/surrol_visual_sensitivity_needlereach_progress100_20states.csv`
