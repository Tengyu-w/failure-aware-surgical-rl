# 项目简介：面向手术具身智能的 Failure-Aware Recovery 原型

## 项目标题

Failure-Aware Runtime Recovery for Safe 3D Surgical Tool Navigation and Manipulation Proxies

## 一句话概括

这个项目不是只做“避障到目标点”。当前原型把问题拆成两层：底层是 3D 手术工具导航和多阶段物体操作，上层是运行时失败检测与恢复。核心问题是：当策略遇到状态估计错误、目标漂移、执行打滑或物体观测丢失时，能否用一个轻量的 monitor/recovery layer 保持任务成功并减少不必要干预。

## 为什么这个项目现在比 2L 更完整

早期 2L/导航版本主要验证了一个最小问题：工具尖端如何在 3D 空间里接近目标，同时避开 forbidden tissue-like region 和安全预算耗尽。这个版本很适合作为安全机制的最小载体，但单独拿出来确实容易显得动作单一。

现在项目已经扩展成两个任务族：

- 3D safe navigation：工具尖端到达目标，同时遵守 forbidden volume、force proxy、workspace 和 safety budget 约束。
- Multi-phase manipulation proxy：工具先接近物体，再推动物体到目标区，最后撤回安全位置。这个任务包含 approach、push、retract 三个阶段，不再只是“靠近目标点”。

因此，当前更合适的表述是：项目从一个最小 3D 导航任务出发，逐步扩展到多阶段操作，并重点研究跨任务阶段的 failure-aware recovery。

## 当前方法

策略接口可以写成：

```text
a_t = pi(s_t, task_phase, safety_budget)
```

当前实现包含：

- constraint-conditioned PPO；
- task phase 和 remaining safety budget 输入；
- forbidden-volume、force proxy、workspace、path length 和 time cost；
- standard safety shield；
- tangent backup controller，将潜在危险动作修正到绕开 forbidden region 的方向；
- navigation failure-recovery benchmark；
- manipulation failure-recovery benchmark。

## 已有实验证据

### 1. 3D 导航

50k-step 3D prototype 结果显示，普通 conditioned PPO 成功率较低且经常耗尽 safety budget；加入 tangent shield 后，成功率接近或达到 1.0，同时 observed cumulative cost 和 budget exhaustion 降到 0。

这说明 tangent backup controller 不是一个单独替代策略的“硬编码完成器”，而是一个 safety correction layer。已有 random-policy sanity check 显示，random policy + tangent shield 在 prototype 中 success = 0.000，因此 shield 本身并不能单独解决 reaching task。

### 2. 导航失败恢复

failure suite 覆盖：

- nominal none；
- target/state bias；
- state dropout；
- execution slip。

结果显示 monitor recovery 在异常状态下能显著恢复成功率，同时在 nominal setting 下不触发不必要恢复。这一点可以包装成“低 false intervention 的 runtime recovery layer”。

### 3. 多阶段操作 proxy

manipulation proxy 包含 approach object、push object to goal、retract 三个阶段。启发式可解性测试中，conditioned tangent shielded 版本可以稳定完成 object delivery 和 retract，说明这个环境不是不可解的 toy，而是一个可用于失败恢复实验的可控代理任务。

### 4. 操作失败恢复

manipulation failure suite 覆盖：

- object_state_bias；
- object_dropout；
- execution_slip；
- contact_loss；
- nominal none。

已有结果显示，base controller 在 object bias、dropout、execution slip 和 contact loss 下会明显失败，而 monitor_recovery 可以恢复到 1.000 success；nominal none 下 monitor 不触发恢复，说明它没有简单地“永远接管”。

## 回答“一个动作够不够”

如果项目只停留在“避开障碍并到达目标点”，确实不够支撑一个强博士方向。它只能算是一个最小验证环境。

但现在的研究问题已经不是“让机器人做一个动作”，而是：

```text
当手术策略在不同任务阶段出现感知、状态估计或执行失败时，
运行时系统能否及时检测、分类并触发恢复，
同时保持 nominal 状态下的低误触发？
```

这个问题可以跨多个动作展开：reach、approach、push、retract，后续还可以接到 SurRoL 的 needle reach、peg transfer、gauze retrieve、needle regrasp 等任务。

## 可以对老师这样说

我现在的工作还不是完整的手术具身智能系统，而是一个 failure-aware reliability layer 的早期原型。它从 3D surgical tool navigation 开始，扩展到 multi-phase manipulation proxy，重点研究异常状态下的 monitor and recovery，而不是替代主策略本身。后续我希望把同一套 failure detection、intervention 和 recovery evaluation 接到更高保真的 SurRoL 或 MuJoCo 手术任务中。

## 下一步实验建议

1. 扩展 failure classification：当前已经能显式报告 predicted failure type，下一步可以替换成学习式 classifier。
2. 增加 human-review trigger 指标：报告 false positive、true positive、trigger delay。
3. 做 cross-task transfer：同一个 monitor/recovery 机制在 navigation 和 manipulation proxy 上都评估。
4. 迁移到 SurRoL 风格任务：先选 NeedleReach 或 GauzeRetrieve，再考虑 NeedlePick/PegTransfer。

## 谨慎结论

当前证据支持一个 prototype-level claim：在抽象 3D 手术代理任务中，constraint-conditioned policy 加 runtime safety/recovery layer 可以提高任务成功率并降低约束违反。这个结论仍需要更多 seeds、更高保真模拟器和更复杂任务验证，不能直接声称已经解决真实手术机器人自主操作。
