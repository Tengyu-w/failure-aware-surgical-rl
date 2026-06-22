# 博士申请方向总结：外接式手术机器人可靠性监督层

## 一句话定位

本项目不是试图重新发明一个手术机器人控制器，也不是宣称已经显著超过现有 SurRoL / VPPV 类方法；它更准确的定位是：

> 在已有手术机器人策略之外，建立一个 failure-aware / risk-aware 的外接可靠性监督层，使系统能够判断什么时候继续自动执行、什么时候允许短程恢复、什么时候转入人工复核、什么时候应视为中止候选。

这和 ECG 项目中的自动放行、复查、人工判断逻辑一致：核心不是把所有异常都恢复，而是先判断异常后果是否可接受。

## 为什么这个方向合理

主流手术机器人通常在目标位姿确定后使用传统控制或策略执行。盲目改变底层控制流程可能增加医生学习成本，也可能破坏已有系统稳定性。因此更稳妥的博士课题不是直接替换主控制器，而是在其外部增加一个可靠性监督层：

- 不改变医生熟悉的主要操作逻辑。
- 不强行让机器人在所有异常下继续自动恢复。
- 将低风险异常交给自动恢复。
- 将视觉错误、停滞、长时间恢复失败、不确定后果交给人工复核或中止候选。

这种定位更适合博士申请：它不是夸大“我能改进原论文策略”，而是提出一个可信的研究问题：

> How can a surgical robot know when not to recover?

## 当前已经完成的技术基础

### 1. 从抽象 3D 代理环境迁移到 SurRoL

最初文档 `constraint_surgical_rl_full_work_compendium_20260618.docx` 的主线是抽象 surgical tool navigation proxy。后续项目已经迁移到 SurRoL，并在 NeedleReach、NeedlePick、GauzeRetrieve 等任务上形成实验链路。

### 2. 建立了风险分流框架

当前系统已经区分：

- `auto_execute`：低风险自动执行
- `auto_recovery`：允许短程恢复
- `human_review`：需要复核
- `abort_candidate`：中止候选

这比“一检测到异常就 recovery”更接近手术机器人需求。

### 3. 建立了视觉输入原型

当前 learned visual routing 使用 `render_proprio_vision`：

- 7 维 proprioception
- 201 维 RGB 池化视觉特征
- 总输入 208 维
- 不直接把 privileged goal 坐标喂给 policy

这说明视觉信息已经进入策略和风险监督链路，虽然目前仍是手工视觉特征，不是 CNN/RAM/VLM。

### 4. 建立了多 seed 可靠性证据

主要结果包括：

| 模块 | 关键结果 | 解释 |
|---|---:|---|
| Risk-aware routing | pure policy 3/50 成功，guarded routing 9/50 成功 | 自动覆盖下降，但选择性成功率提升 |
| Temporal stagnation | 自动失败 8 -> 4，自动成功保持 15 | 可减少长时间恢复失败 |
| Conservative budget 10 | 自动失败 2 -> 0，自动成功保持 6 | 当前最简单有效的 guard |
| Visual adapter | 独立测试腐蚀 MSE 降低 99.91% | 离线视觉修正有效，但不能单独证明闭环可靠 |
| Online adapter memory | 20-seed 过度复核，不采用 | 负结果，说明 KNN memory 不够 |
| Cross-task learned transfer | NeedlePick/GauzeRetrieve 0/5 成功、5/5 复核 | 不可直接迁移，但未盲目放行 |

## 当前最强结论

### 已经证明

1. 在 NeedleReach visual routing 中，外接风险监督可以显著提高被允许自动执行轨迹的成功率。
2. Recovery budget 10 能在固定 20 seed 中把自动失败从 2 条降到 0 条，同时保留 6 条自动成功。
3. Temporal stagnation 能识别一部分“恢复很久但仍失败”的轨迹。
4. NeedlePick 和 GauzeRetrieve 上的规则/phase-aware monitor 已显示跨任务可靠性监督思想可行。
5. 直接把 NeedleReach learned visual policy/risk/memory 迁移到复杂任务不可行，会全部进入复核。

### 只能提示，尚未证明

1. Visual adapter 可能帮助视觉鲁棒性，但目前只证明了离线降噪。
2. Learned risk head 有潜力替代规则阈值，但当前仍需更多任务和 seed。
3. Recovery memory 方向有价值，但简单 KNN 不足以处理复杂高风险状态。

### 尚未证明

1. 尚未训练出强 SurRoL PPO/RL 策略。
2. 尚未完成 CNN/RAM/VLM 视觉语义接入。
3. 尚未证明 learned visual supervisor 能跨任务泛化。
4. 尚未建立真实组织损伤、力反馈或临床级不可逆风险模型。

## 推荐博士课题标题

中文：

> 面向手术机器人的外接式可靠性监督：视觉不确定性、失败恢复与风险分流

英文：

> Failure-Aware Reliability Supervision for Surgical Robot Autonomy under Visual Uncertainty

## 与 RAM/VLM 方向的关系

RAM/VLM 或 3D object memory 可以作为上游感知与语义模块，回答“物体是什么、面是什么、当前语义状态是什么”。本项目关注下游可靠性监督，回答：

- 当前视觉/策略状态是否可靠？
- 如果动作失败，是否允许自动恢复？
- 恢复多少次后应停止？
- 哪些异常应转入人工复核？

因此两者不是冲突关系，而是上下游关系：

```text
RAM / VLM / perception memory
        ↓
visual or semantic state estimate
        ↓
reliability supervisor
        ↓
auto execute / auto recovery / human review / abort candidate
```

## 下一步研究计划

1. 为 NeedlePick 和 GauzeRetrieve 分别采集任务专属 visual policy / risk / memory 数据。
2. 将手工 RGB 池化替换为 keypoint、small CNN 或 RAM/VLM-derived embedding。
3. 将 recovery memory 从 KNN 升级为 phase-aware learned action head。
4. 扩展风险标签：从 action gap 扩展到 unsafe proximity、forbidden zone、stagnation、visual OOD。
5. 报告 coverage-risk 曲线，而不是只报告成功率。

## 最稳妥的申请表述

> My current project investigates an external reliability supervisor for surgical robot autonomy. Rather than replacing the main controller, the supervisor monitors visual-policy rollouts and routes them into auto-execution, memory-based recovery, human review, or abort candidates. SurRoL experiments show that selective routing and conservative recovery budgets can reduce unsafe auto-recovery failures, while negative results reveal that offline visual correction and KNN recovery memory are insufficient for reliable closed-loop deployment. This motivates my PhD interest in failure-aware surgical autonomy under visual uncertainty.

