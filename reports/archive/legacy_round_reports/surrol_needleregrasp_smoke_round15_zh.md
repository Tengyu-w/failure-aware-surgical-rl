# SurRoL 实验 Round 15：NeedleRegrasp 第三任务 Smoke

## 一句话结论

第三任务 `NeedleRegrasp` 已完成初步 smoke。`needle_regrasp_bimanual_org.NeedleRegrasp` 可以 reset、产生 observation、调用 10 维 oracle action 并执行 step；但 clean oracle 在 1 seed、260 step 内没有成功。诊断显示 waypoint 被消费完，PSM2 tip 接近目标，但默认 success metric 使用针的 `obj_link1` 作为 achieved goal，最终仍远离目标。因此，`NeedleRegrasp` 暂时不能直接纳入正式 recovery 实验，需要先解决双臂任务的 goal/link/success 定义问题。

## Smoke 文件

- Smoke 脚本：`E:\RL_projects\constraint_surgical_rl\scripts\smoke_surrol_needle_regrasp.py`
- Clean smoke CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needleregrasp_clean_smoke.csv`
- Diagnostic CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_needleregrasp_clean_smoke_diagnostics.csv`

## 接口结果

| Item | Result |
|---|---|
| Task class | `surrol.tasks.needle_regrasp_bimanual_org.NeedleRegrasp` |
| Reset | 成功 |
| Observation dim | 35 |
| Goal dim | 3 |
| Oracle action dim | 10 |
| Clean oracle success | 0/1 |
| Max steps | 260 |
| Final default distance | 0.4155 |

## 诊断观察

| Signal | Value / Observation |
|---|---|
| Initial default distance | 0.3325 |
| Final `link1_goal_distance` | 0.4155 |
| Final `link2_goal_distance` | 0.5557 |
| Final `psm2_goal_distance` | about 0.051 |
| Active waypoint | 最终为 -1，说明 waypoints 已消费完 |
| Success | 仍为 0 |

这说明当前失败不只是“动作没跑起来”。更像是双臂重抓取任务的默认 achieved goal 和我们想验证的交接/放置目标之间没有直接对齐。

## Full-DOF 版本

尝试 `surrol.tasks.needle_regrasp.NeedleRegraspFullDof` 时，导入阶段需要：

```text
dvrk, rospy, PyKDL
```

这些属于 ROS/dVRK/硬件相关依赖。当前没有继续硬跑，符合本项目“不运行硬件-facing robot control”的安全约束。

## 当前判断

可以说：

> We probed NeedleRegrasp as a third SurRoL task. The environment and oracle interface are reachable, but the clean scripted rollout does not satisfy the default success metric, likely due to task-specific goal/link semantics in the bimanual regrasp setting.

不应该说：

> 已经完成第三任务 recovery 验证。

## 下一步

1. 检查 `NeedleRegrasp` 的 success metric 是否应绑定 `obj_link1`、`obj_link2`、object base，还是 PSM2 target pose。
2. 单独写一个 `NeedleRegrasp` diagnostic runner，记录 needle pose、link pose、PSM1/PSM2 tip pose、jaw state、activation/contact state。
3. 如果能让 clean oracle 稳定成功，再接入 failure/recovery 框架。
4. 如果该任务需要 ROS/dVRK full-dof 依赖，则暂时把第三任务候选切换到 `PegTransfer` 或 `BiPegTransfer` 的 non-hardware org 版本。

