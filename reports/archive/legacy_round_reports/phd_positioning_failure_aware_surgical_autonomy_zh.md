# 博士申请定位：Failure-Aware Surgical Autonomy

## 核心判断

这个项目不应该被包装成“我能显著改进豆奇老师的完整 Science Robotics 级系统”。那样既不现实，也容易显得不自量力。

更合适的定位是：

> 我理解了 surgical embodied intelligence 系统中的一个可靠性缺口：simulation-trained surgical policies 已经能在 nominal cases 中执行任务，但 abnormal execution 下的 failure diagnosis、runtime recovery、selective intervention / human review 仍然没有被充分系统化。我的当前工作是一个 early-stage prototype，目标是把 VLA/RL 的 runtime reliability 思路迁移到 SurRoL surgical task recovery。

这不是替代主策略，也不是重做老师的大系统，而是在大系统上补一层 **runtime reliability layer**。

## 不要这样说

不建议把贡献说成：

- 我能改进老师的 RL 训练。
- 我能优化 embedding。
- 我能解释最后几层 hidden states。
- 我能显著提升完整 surgical embodied intelligence 系统。

这些表述会把项目缩小成“主系统里的一点小修补”，而且容易和老师已有的系统级贡献正面比较。

## 应该这样说

更好的表述是：

> I am interested in extending surgical embodied intelligence from task execution to failure-aware autonomy. Current simulation-trained policies can perform nominal tasks, but abnormal execution remains under-characterized. My previous work on VLA/RL recovery suggests that runtime risk monitoring, failure diagnosis, and demo-anchored or oracle-anchored recovery may provide a lightweight reliability layer for detecting and recovering from failure-prone states.

中文意思：

> 我感兴趣的不是替代主策略，而是把手术具身智能从“能执行任务”扩展到“知道自己什么时候不可靠，并能恢复或交给人”。当前仿真训练策略已经能完成 nominal tasks，但 abnormal execution 下的失败诊断、恢复触发和选择性干预仍然值得系统研究。我的工作尝试把 VLA/RL 中的 runtime reliability 思路迁移到 SurRoL 手术任务中。

## 和豆奇老师工作的关系

| 老师系统中的层 | 你的 extension |
|---|---|
| Surgical simulator | Failure injection / abnormal execution benchmark |
| RL policy / task autonomy | Runtime reliability monitor |
| Visual servoing / control | Recovery trigger and intervention policy |
| Sim-to-real execution | Failure-aware evaluation under distribution shift |
| Success rate | Success + recovery + false intervention + trigger delay |
| Task automation | Selective autonomy / human review |

你的定位不是“和老师系统平起平坐”，而是“沿着老师的平台继续往可靠性方向扩展”。

## 当前已有证据

### 1. 已经完成 SurRoL 小任务 demo

我们已经在 clean SurRoL SR-VPPV 环境中跑通了多个任务入口：

- `ECMReach`
- `NeedleReach`
- `NeedlePick`
- `GauzeRetrieve`
- `BiPegTransfer`
- `NeedleRegrasp`

这说明项目已经不只是自研 toy navigation，而是接入了真实 surgical simulation task entry points。

### 2. NeedlePick 是合适的 failure-aware benchmark

在 `NeedlePick` 中：

- clean oracle：3/3 success
- perturbed oracle under `action_noise`：0/3 success
- perturbed oracle under `action_dropout`：0/3 success
- perturbed oracle under `execution_slip`：0/3 success

这说明 NeedlePick 有一个很清楚的研究结构：nominal 可完成，但 abnormal execution 会稳定破坏任务。

### 3. Runtime monitor 有初步恢复效果

在 `coarse + 32 recovery window` 的 5 seed pilot 下，普通 oracle override 恢复结果是：

| Failure | Perturbed Success | Monitor-Corrected Success |
|---|---:|---:|
| action_noise | 0/5 | 5/5 |
| action_dropout | 0/5 | 1/5 |
| execution_slip | 0/5 | 3/5 |

这已经可以支撑一个 prototype-level claim：

> A lightweight runtime recovery layer can recover some abnormal executions in SurRoL NeedlePick, but recovery effectiveness depends strongly on failure type.

进一步做失败 seed 诊断后，我们发现 dropout/slip 的失败并不是 monitor 没触发，而是 waypoint 已经走完但抓取/接触约束没有保持。加入 phase-aware recovery，尤其是 grasp-stage retry 后，5 seed 结果变为：

| Failure | Perturbed Success | Phase-Aware Recovery Success |
|---|---:|---:|
| action_noise | 0/5 | 5/5 |
| action_dropout | 0/5 | 5/5 |
| execution_slip | 0/5 | 5/5 |

这说明更有价值的研究问题不是“是否加 monitor”，而是“不同 failure type 和任务阶段需要什么样的 selective recovery policy”。

### 4. 结果不是“全都成功”的演示，而是暴露了真实研究问题

当前实验显示：

- `action_noise` 容易恢复。
- `execution_slip` 中等难度。
- `action_dropout` 更难。
- 拉长 recovery window 可以减少重复触发，但不能解决所有 failure。
- 某些失败 seed 不是 monitor 没触发，而是 recovery policy 没理解任务阶段/接触状态。

这非常适合转化成博士问题：**failure taxonomy + selective recovery + intervention budget + phase-aware policy**。

## 研究问题雏形

可以把博士方向写成：

> Failure-aware recovery for surgical embodied intelligence.

更具体一点：

> How can simulation-trained surgical autonomy systems detect, diagnose, and recover from abnormal execution states without causing excessive unnecessary intervention?

核心研究问题：

1. 如何定义 surgical task 中的 abnormal execution？
2. 哪些 state / action / trajectory residual 信号能提前暴露 failure？
3. 不同 failure type 是否需要不同 recovery policy？
4. 如何平衡 missed failure 和 false intervention？
5. 哪些情况应该自动恢复，哪些情况应该 human review？

## 三阶段博士路线图

### 阶段 1：VLA / RL reliability prototype

已有基础：

- hidden-state / trajectory instability analysis
- runtime risk monitor
- failure-state retrieval
- demo-anchored or oracle-anchored recovery
- success improvement under abnormal states

目标：证明你不是只会训练模型，而是在研究 policy 什么时候不可靠。

### 阶段 2：迁移到 SurRoL surgical tasks

当前已经启动：

- SurRoL clean deployment
- NeedlePick abnormal execution benchmark
- action noise / dropout / slip failure injection
- monitor-corrected recovery experiments
- window sweep and trigger trade-off analysis

下一步可以扩展到：

- `GauzeRetrieve`
- `NeedleRegrasp`
- `PegTransfer`
- bimanual failure recovery

### 阶段 3：建立 surgical runtime recovery benchmark

不要只报告 success rate，而要报告：

- early failure detection
- recovery success
- failure-type classification
- unnecessary intervention rate
- trigger delay
- intervention budget
- human-review trigger accuracy
- robustness under task and initialization shift

这就从一个小 demo 变成了一个可扩展博士课题。

## 可以对老师说的话

英文版本：

> I understand that my current work is still an early-stage prototype and much smaller in scope than a full surgical embodied intelligence system. However, I see it as a possible reliability layer rather than a replacement of the main policy or controller. My goal is to investigate whether failure-aware monitoring and recovery can complement simulation-trained surgical policies, especially in abnormal or distribution-shifted execution states. As an initial step, I deployed SurRoL and tested NeedlePick under action noise, dropout, and execution slip. The clean oracle succeeds, while perturbed execution fails; a simple runtime recovery layer can recover action-noise failures and partially recover slip/dropout failures, exposing a concrete trade-off between recovery success and unnecessary intervention.

中文版本：

> 我知道我现在的工作还只是早期原型，规模远小于完整的手术具身智能系统。但我把它看作一个可靠性层，而不是替代主策略或控制器。我的目标是研究 failure-aware monitoring and recovery 能否补充仿真训练的手术策略，尤其是在异常或分布偏移的执行状态下。作为第一步，我已经部署了 SurRoL，并在 NeedlePick 上测试了 action noise、dropout 和 execution slip。clean oracle 能成功，而扰动执行会失败；一个简单的 runtime recovery layer 可以恢复 action-noise failure，并部分恢复 slip/dropout failure，同时暴露出 recovery success 与 unnecessary intervention 的权衡。

## 当前最稳的结论

你现在已经不只是“做了 embedding analysis”或“做了避障 toy task”。更稳的说法是：

> 我已经做出了一个 SurRoL NeedlePick 上的 failure-aware runtime recovery prototype。它证明 abnormal execution 可以被系统化注入、检测和部分恢复，也暴露出不同 failure type 对 recovery policy 的不同要求。这个 prototype 还很小，但它足够作为博士申请中的 research seed。

## 仍然要诚实承认的限制

- 目前已有 5 seed pilot，后续仍建议扩到 10 seed。
- recovery action 仍然是 oracle override，不是 learned recovery policy。
- trigger 是规则型，不是 calibrated uncertainty model。
- 目前只在 NeedlePick 上有完整实验，其他 SurRoL tasks 还只是 smoke verified。
- 当前没有 real robot / sim-to-real 结果，不能声称已经解决真实手术机器人安全问题。

这些限制不是坏事；它们正好构成博士阶段的研究空间。
