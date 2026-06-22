# SurRoL 正式实验 Round 1：Oracle Robustness Pilot

## 一句话结论

第一轮正式 SurRoL 实验已经跑通。结果显示：`ECMReach` 在动作噪声、动作丢失和执行滑移下仍保持 3/3 成功；`NeedlePick` 在无扰动下 3/3 成功，但在三类动作扰动下均降为 0/3 成功；`BiPegTransfer` 在 200 步无扰动 oracle 下仍未达到 strict success，但距离明显下降，适合作为后续 hard-case，而不适合直接和前两个任务用同一 horizon 比成功率。

## 实验文件

- 25 步 pilot CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_oracle_robustness_pilot.csv`
- 200 步 horizon 校准 CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_oracle_horizon_calibration.csv`
- 200 步扰动实验 CSV：`E:\RL_projects\constraint_surgical_rl\runs\surrol_oracle_robustness_200step.csv`
- 实验脚本：`E:\RL_projects\constraint_surgical_rl\scripts\run_surrol_oracle_robustness.ps1`

## 实验设置

- 平台：SurRoL clean SR-VPPV 源码，WSL Ubuntu，PyBullet DIRECT/EGL。
- Policy：SurRoL scripted oracle，不训练 RL policy。
- Seeds：3 个 seed，`42000` 到 `42002`。
- 每个 seed-condition-task 运行 1 个 episode。
- 风险 proxy：距离回退、比初始状态更远、动作被 clip。
- 主要指标：success、final distance、distance reduction、risk event rate、stalled rate、steps。

## Horizon 校准结果

| Task | Condition | Episodes | Success | Final Distance | Distance Reduction | Risk Event | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|
| ECMReach | none | 3 | 1.000 | 0.0044 | 0.0775 | 0.000 | 38.0 |
| NeedlePick | none | 3 | 1.000 | 0.0181 | 0.1615 | 0.026 | 38.7 |
| BiPegTransfer | none | 3 | 0.000 | 0.0682 | 0.1366 | 0.093 | 200.0 |

解释：`ECMReach` 和 `NeedlePick` 的合理 horizon 约 40 步左右；25 步 pilot 太短，不能用来判断 strict success。`BiPegTransfer` 在 200 步内仍未成功，但距离下降，说明它更像难任务/长 horizon 任务。

## 200 步扰动结果

| Task | Condition | Episodes | Success | Final Distance | Distance Reduction | Risk Event | Stalled Rate | Mean Steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| ECMReach | none | 3 | 1.000 | 0.0044 | 0.0775 | 0.000 | 0.000 | 38.0 |
| ECMReach | action_noise | 3 | 1.000 | 0.0042 | 0.0777 | 0.269 | 0.021 | 51.3 |
| ECMReach | action_dropout | 3 | 1.000 | 0.0044 | 0.0775 | 0.000 | 0.314 | 55.0 |
| ECMReach | execution_slip | 3 | 1.000 | 0.0045 | 0.0775 | 0.176 | 0.012 | 54.7 |
| NeedlePick | none | 3 | 1.000 | 0.0181 | 0.1615 | 0.026 | 0.775 | 38.7 |
| NeedlePick | action_noise | 3 | 0.000 | 0.1994 | -0.0198 | 0.237 | 0.975 | 200.0 |
| NeedlePick | action_dropout | 3 | 0.000 | 0.1652 | 0.0144 | 0.260 | 0.975 | 200.0 |
| NeedlePick | execution_slip | 3 | 0.000 | 0.1799 | -0.0003 | 0.248 | 0.863 | 200.0 |

## 目前能说明什么

- 这个项目现在已经从自研 toy 3D 环境推进到了真实 SurRoL 任务入口。
- `ECMReach` 是低难度鲁棒任务，可作为 sanity check。
- `NeedlePick` 是最适合下一步做 failure-aware monitor 的任务：无扰动能成功，但动作扰动会明显破坏成功率。
- `BiPegTransfer` 是 hard-case，应该先做 horizon/task debugging，再纳入公平对比。
- 风险 proxy 在 `ECMReach action_noise/execution_slip` 和 `NeedlePick` 扰动条件下有明显响应，说明它可以作为下一步 monitor 的弱标签来源。

## 不能过度声称的地方

- 这不是 RL 训练结果，只是 oracle robustness baseline。
- 每个条件只有 3 个 seed，适合做 pilot，不适合写成强统计结论。
- 当前 risk proxy 是启发式，不是校准后的 uncertainty model。
- `NeedlePick none` 的 stalled rate 偏高，说明任务内部有阶段性停滞或 oracle 行为细节，需要进一步看 trajectory。
- `BiPegTransfer` 不能因为 0 success 就简单说失败；它可能需要更长 horizon、不同 oracle 或任务初始化检查。

## 下一步实验

1. 对 `NeedlePick` 加 monitor-corrected action：比较 `oracle`、`perturbed oracle`、`monitor-corrected oracle`。
2. 保存 trajectory-level CSV：每一步记录 distance、action norm、risk score、success flag，方便画曲线。
3. 对 `BiPegTransfer` 单独做 horizon sweep：200、400、800 步，并检查 oracle 是否真的朝目标推进。
4. 如果 monitor-corrected 能恢复 `NeedlePick` 扰动成功率，再开始训练 RL policy。
