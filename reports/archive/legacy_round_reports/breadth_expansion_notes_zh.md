# 横向项目广度扩展记录

## 已完成的两步

第一步已经补了 navigation 的 3 个训练 seed failure-recovery 评估：

- model seed: 0, 1, 2；
- episodes/seed: 10；
- failure modes: none, state_target_bias, state_dropout, execution_slip；
- monitor_recovery 在 3 个模型 seed 上均恢复到 1.000 success；
- policy_only 在 state_target_bias / state_dropout 下约 0.033 success，在 execution_slip 下约 0.533 success。

第二步已经横向增加了两个 surgical-proxy preset：

- `peg_transfer_proxy`
- `needle_regrasp_proxy`

这两个 preset 已接入 `CONFIG_PRESETS` 和新的 3D breadth suite。

## 当前任务广度

| Preset / Env | 对应意图 | 当前性质 |
|---|---|---|
| `prototype` | 基础 3D 安全导航 | 抽象导航 proxy |
| `strict` | 更严格约束迁移 | stress preset |
| `needle_reach` | 针尖到达/定位 | 抽象导航 proxy |
| `needle_insert` | 更高精度插入式目标 | 抽象导航 proxy |
| `tight_corridor` | 狭窄空间通过 | 安全约束 stress |
| `tissue_retraction_proxy` | 组织牵拉/避让压力 | 抽象导航 proxy |
| `gauze_manipulation_proxy` | 纱布/软物体操作代理 | 抽象导航 proxy |
| `peg_transfer_proxy` | peg transfer 风格目标迁移 | 新增抽象 proxy |
| `needle_regrasp_proxy` | needle regrasp 风格重新定位 | 新增抽象 proxy |
| `ConstrainedToolManipulationEnv` | approach -> push -> retract | 多阶段操作 proxy |

## 新增 3D Breadth 结果

轻量评估设置：

- trained models: `pilot_3d_50k_prototype_*_seed0/1/2`
- episodes/seed: 20
- evaluated presets: `peg_transfer_proxy`, `needle_regrasp_proxy`

| Preset | Best Variant | Success | Budget Exhausted | Cost | Final Distance |
|---|---|---:|---:|---:|---:|
| `peg_transfer_proxy` | `conditioned_tangent_shielded` | 0.933 | 0.000 | 0.000 | 0.053 |
| `needle_regrasp_proxy` | `conditioned_tangent_shielded` | 0.800 | 0.000 | 0.000 | 0.067 |

对照结果也很有用：

- `conditioned` 在两个新增 preset 上 success = 0.000，budget_exhausted = 1.000；
- `no_phase_budget` 基本也失败，说明 phase/budget 信息仍然重要；
- `conditioned_shielded` 有一定帮助，但明显弱于 tangent shield；
- `conditioned_tangent_shielded` 保持零 budget exhaustion 和零 cumulative cost。

## 这说明什么

现在项目的横向广度不再只是一个避障环境，而是覆盖了：

- 基础导航；
- 严格约束迁移；
- needle reach / insert 风格任务；
- peg transfer 风格任务；
- needle regrasp 风格任务；
- tissue/gauze 风格 proxy；
- 多阶段 manipulation proxy；
- failure detection / diagnosis / recovery；
- human-review trigger；
- risk/uncertainty scoring。

## 仍然不能夸大的地方

这些 preset 仍然是 abstract proxy，不是 SurRoL 真实任务。它们的作用是扩大实验矩阵和申请叙事宽度，证明同一套 safety/recovery 思路可以在不同几何难度、目标精度和安全预算下评估。

## 下一步真正扩大体量

1. 为 manipulation PPO 补 3 个训练 seed，而不仅是 heuristic/controller failure suite。
2. 把 failure recovery 也接到 `peg_transfer_proxy` 和 `needle_regrasp_proxy` 上，而不只做 nominal stress transfer。
3. 选一个 SurRoL 风格任务做 adapter：优先 `NeedleReach` 或 `GauzeRetrieve`。
