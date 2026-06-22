# SurRoL 跨任务广度状态：Round 45

## 目的

Stage 5 的目标是检查当前 conservative visual routing 是否能从 NeedleReach 迁移到更复杂的 NeedlePick 和 GauzeRetrieve。为了避免过度宣称，本轮分开报告两类证据：

1. 旧的规则/phase-aware monitor 链路是否已有跨任务结果。
2. 当前 learned visual policy + risk/memory 路由能否直接跨任务迁移。

## Wrapper 与接口检查

两个复杂任务都可以进入当前 visual wrapper：

| Task | Obs shape | Action shape | Adapter | Status |
|---|---:|---:|---|---|
| NeedlePickRL-v0 | 208 | 5 | strict-split visual adapter | wrapper smoke pass |
| GauzeRetrieveRL-v0 | 208 | 5 | strict-split visual adapter | wrapper smoke pass |

这说明代码接口不是当前瓶颈：复杂任务可以产生与 NeedleReach 一样维度的 `render_proprio_vision` 输入。

## Learned Visual Routing 直接迁移 Probe

共同设置：

- Policy：NeedleReach 视觉 DAgger policy
- Risk head：NeedleReach 旧 visual risk head
- Recovery memory：NeedleReach 旧 augmented visual recovery memory
- Adapter：strict-split visual adapter
- Routing：`selective_memory_guarded`
- Review threshold：0.6
- Recovery budget：10
- Corruption：mixed p=0.35
- Seeds：54100-54104

结果：

| Task | Episodes | 成功 | 复核 | 自动覆盖 | 自动成功 | 自动失败 | Mean final distance |
|---|---:|---:|---:|---:|---:|---:|---:|
| NeedlePickRL-v0 | 5 | 0 | 5 | 0 | 0 | 0 | 0.1836 |
| GauzeRetrieveRL-v0 | 5 | 0 | 5 | 0 | 0 | 0 | 0.2566 |

解释：

- 这不是迁移成功。
- 但也没有危险地盲目放行；全部进入 human review。
- 直接使用 NeedleReach 的 policy/risk/memory 到复杂任务，只能说明保守 guard 能拒绝处理，不说明能恢复。

## 已有跨任务正结果：规则/Phase-Aware Monitor 链路

历史报告已经在 NeedlePick 和 GauzeRetrieve 上证明了 phase-aware / observable-proxy recovery 的跨任务可行性：

| Suite | Task | Failure | Perturbed | Recovered |
|---|---|---|---:|---:|
| standard corruptions | NeedlePick | action dropout/noise/slip | 0.0 | 1.0 |
| standard corruptions | GauzeRetrieve | action dropout/noise/slip | 0.0 | 1.0 |
| observable jaw-stuck 10seed | NeedlePick | jaw_stuck_open | 0/10 | 10/10 |
| observable jaw-stuck 10seed | GauzeRetrieve | jaw_stuck_open | 0/10 | 10/10 |
| visual-state re-estimation | NeedlePick | perception/depth error | 0/5 | 5/5 |
| visual-state re-estimation | GauzeRetrieve | perception/depth error | 0/5 | 5/5 |

这部分支持“可靠性监督思想跨任务成立”，但它是规则/monitor/oracle-based 链路，不是当前 learned visual policy 的跨任务成功。

## 已有复杂任务 blocked 证据

PickAndPlace 曾作为复杂第三任务尝试，但不纳入正式实验：

- clean oracle 3 seed 只有 1/3 成功。
- 本地环境需要 haptic module mock 才能导入部分任务。
- 因此不能用于正式 recovery/routing claim。

NeedleRegrasp 也保留为 blocked，因为 success/goal semantics 与 clean oracle 稳定性不足。

## 结论

Stage 5 完成为“有限完成 / learned visual 跨任务 blocked”：

1. 代码接口层面，NeedlePickRL 和 GauzeRetrieveRL 可以接入 208D visual wrapper。
2. 规则/phase-aware 可靠性监督已在 NeedlePick 和 GauzeRetrieve 有跨任务正结果。
3. 当前 learned visual conservative routing 不能直接从 NeedleReach 迁移到复杂任务；5/5 全部复核，0 自动恢复。
4. 正式多任务 learned visual routing 需要任务专属 policy、risk head 和 recovery memory 数据。

## 对项目定位的影响

现在不能说：

> 当前 visual learned supervisor 已经解决多任务 SurRoL。

可以说：

> 跨任务的可靠性监督框架已经在规则/phase-aware 层面有 NeedlePick/GauzeRetrieve 证据；learned visual routing 目前在 NeedleReach 上成立，向复杂任务迁移需要重新采集任务专属视觉策略和风险数据。

这反而让博士申请叙事更稳：项目已经识别出“监督框架可迁移”和“learned visual policy 不可直接迁移”之间的边界。

## 下一步

Stage 6 应进入申请叙事和研究计划整合：

- 把当前证据整理成“外接可靠性监督层”的博士课题雏形。
- 将 NeedleReach learned visual 结果作为视觉 supervisor 原型。
- 将 NeedlePick/GauzeRetrieve 规则/phase-aware 结果作为跨任务可行性证据。
- 明确下一步研究问题：如何为每个复杂任务构建任务专属 visual risk/memory，并逐步替换规则模块。

## 产物

- `runs/surrol_stage5_needlepick_visual_wrapper_check/`
- `runs/surrol_stage5_gauzeretrieve_visual_wrapper_check/`
- `runs/surrol_stage5_needlepick_transfer_probe_budget10_seed54100/`
- `runs/surrol_stage5_gauzeretrieve_transfer_probe_budget10_seed54100/`
- `reports/surrol_cross_task_breadth_round45_zh.md`

