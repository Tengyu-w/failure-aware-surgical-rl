# 从“单一避让动作”升级到博士课题雏形

## 当前担心

你的担心是对的：如果项目只展示“到达目标点 + 避开障碍”，它更像一个课程级 RL demo，而不是博士申请里足够可信的研究雏形。老师项目里有很多动作时，我们不能只说“我也做了一个避障动作”，那样贡献会显得窄。

更好的做法不是立刻堆很多复杂动作，而是把动作组织成一个清晰的实验阶梯：从单步导航，到多阶段操作，再到失败恢复和跨任务泛化。

## 现在已经覆盖的动作层级

| 层级 | 当前任务 | 动作/阶段 | 它证明什么 |
|---|---|---|---|
| Level 1 | 3D tool navigation | reach + avoid | safety layer 能保护基本工具运动 |
| Level 2 | Failure-aware navigation | recover from target/state/action failures | monitor 能处理异常执行状态 |
| Level 3 | Manipulation proxy | approach object -> push object -> retract | 不只是到点，而是改变物体状态 |
| Level 4 | Manipulation failure recovery | recover from object bias/dropout/slip | recovery 可以覆盖感知和执行失败 |

这样讲，项目就不是“一个动作”，而是一个从简单技能到可靠执行系统的递进。

## 最推荐新增的实验

### A. Contact Loss Recovery（已补入当前 benchmark）

**问题：** 工具推物体时失去接触，物体没有继续向目标移动。

**当前实验设计：**

- 在 manipulation proxy 中注入 contact loss；
- base controller 继续按错误假设执行；
- monitor 检测 object-goal distance 停滞；
- recovery 重新 approach object，再 push。

**当前结果：** 100 episode 正式评估中，base controller 在 contact_loss 下 success = 0.000，monitor_recovery success = 1.000，平均 detection delay = 6 steps。

**为什么有价值：** 这是手术操作里很常见的失败模式，比单纯 state dropout 更接近 manipulation。

### B. Failure Classification

**问题：** 当前 monitor 主要是 binary detection：发现异常就恢复。博士方向里可以进一步问：系统能否知道是哪类失败？

**类别：**

- target/state bias；
- state dropout；
- execution slip；
- object dropout；
- contact loss；
- excessive force / budget risk。

**指标：**

- classification accuracy；
- detection delay；
- recovery success；
- false intervention rate；
- unnecessary recovery under none。

### C. Cross-Task Recovery Transfer

**问题：** 同一套 recovery 思想能否同时适用于 navigation 和 manipulation？

**实验设计：**

- navigation failure suite；
- manipulation failure suite；
- 统一报告 success、constraint cost、trigger rate、detection delay。

**为什么有价值：** 这能证明你的贡献不是某个环境里的硬编码技巧，而是一个可靠性评估框架。

### D. Surgical Proxy Preset Suite

**问题：** 老师项目动作多，我们可以用 surgical-proxy presets 表示不同任务场景。

**已有方向：**

- needle reach；
- needle insert；
- gauze manipulation proxy；
- tissue retraction proxy；
- tight corridor。

**下一步：** 把这些 preset 和 failure recovery 结合起来，而不是只做 nominal transfer。

## 申请材料里的推荐说法

不要说：

```text
我做了一个避障 RL 环境。
```

可以说：

```text
I started from a minimal 3D surgical tool navigation proxy, then extended it into a multi-phase manipulation and failure-recovery benchmark. The current focus is not a single motor primitive, but a runtime reliability layer that detects abnormal execution states and triggers recovery across navigation and manipulation phases.
```

中文可以说：

```text
我不是把贡献放在某一个动作本身，而是把动作作为 failure-aware recovery 的测试载体。现在的原型已经从 3D 导航扩展到 approach-push-retract 的多阶段操作，并且加入了状态偏移、观测丢失、执行打滑等失败模式。后续我希望把这个 monitor/recovery 评估框架迁移到 SurRoL 风格的手术任务中。
```

## 最现实的下一步路线

1. contact_loss failure mode 已经是最优先项：它让 manipulation 更像真实操作中的接触丢失问题。
2. failure classification 已补入 manipulation failure report：每个 episode 会记录 predicted failure type 和 class correctness。
3. 最后做 SurRoL/needle/gauze 风格迁移，作为申请材料里的未来计划。

这样项目会显得更像一个博士课题雏形：有最小原型、有实验矩阵、有失败模式、有指标、有下一步高保真迁移，而不是单点 demo。
