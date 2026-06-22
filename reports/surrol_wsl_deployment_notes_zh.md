# SurRoL WSL 部署记录

## 当前结论

SurRoL 已部署在 E 盘，并且已经在 WSL Ubuntu 中跑通最小纯仿真 smoke test。这个结果说明它可以作为本项目后续“动作广度扩展”的外部仿真平台候选，而不只是继续停留在自研 toy 3D 避障/到达环境。

## 路径

- SurRoL 干净源码：`E:\RL_projects\SurRoL_clean_SR-VPPV`
- WSL 路径：`/mnt/e/RL_projects/SurRoL_clean_SR-VPPV`
- micromamba：`E:\RL_projects\micromamba`
- SurRoL Python 环境：`E:\RL_projects\surrol_py38_env`
- 复测脚本：`E:\RL_projects\constraint_surgical_rl\scripts\run_surrol_wsl_smoke.ps1`

## 干净归档

- 已验证工作线归档：`E:\RL_projects\archives\SurRoL-SR-VPPV-10f7c8f.zip`
- 官方 main 分支归档：`E:\RL_projects\archives\SurRoL-main-a903fa6.zip`
- WSL/Taichi 兼容补丁：`E:\RL_projects\archives\SurRoL-SR-VPPV-wsl-taichi-cpu.patch`

校验值：

- `SurRoL-SR-VPPV-10f7c8f.zip`: `520c40a536afb0bb28c7dcfd9f40e79c5f149770b8d04a282ee058a70145a033`
- `SurRoL-main-a903fa6.zip`: `5d02ac1344b3544ad1b468d763e5ea0f1204b821e91dd474081c748c07df014d`
- `SurRoL-SR-VPPV-wsl-taichi-cpu.patch`: `f9f2fe04218dc7cf88a401c83e912cb67644ec5482112923599414b06e6f6f29`

`SurRoL_clean_SR-VPPV` 已使用同一套 smoke script 验证通过。复测命令：

```powershell
powershell -ExecutionPolicy Bypass -File E:\RL_projects\constraint_surgical_rl\scripts\run_surrol_wsl_smoke.ps1
```

## 已安装核心环境

- Python 3.8.20
- PyBullet
- Gym 0.23.1
- NumPy 1.24.4
- roboticstoolbox-python / spatialmath-python / scipy
- pandas
- taichi 1.6.0
- scikit-image
- trimesh

## 已验证任务

以下任务均完成了 `import -> env(render_mode=None) -> reset -> oracle/sample action -> step` 的 smoke test：

- `ECMReach`
- `NeedleReach`
- `NeedlePick`
- `GauzeRetrieve`
- `BiPegTransfer`
- `NeedleRegrasp`

这组任务覆盖了相机 reach、针/纱布抓取、双臂 peg transfer、针重抓取等入口，比当前自研原型里的导航避障和代理式 manipulation 更接近 SurRoL 的任务广度。

## 已做兼容性补丁

`E:\RL_projects\SurRoL\Benchmark\state_based\MPM\mpm3d.py` 原本会在检测到 Vulkan 时自动选择 Vulkan backend。WSL 中该路径触发 Taichi/Vulkan 原生崩溃，因此已改为默认 `cpu`，并支持通过环境变量 `SURROL_TAICHI_ARCH` 手动指定 `cpu`、`cuda`、`vulkan` 或 `metal`。

## 已知限制

- 当前只验证了仿真 smoke test，没有开始训练。
- 当前没有启用真实 dVRK、ROS、haptic device 或硬件控制。
- 一些非 `_org` 任务文件会直接 import `dvrk/rospy/PyKDL`，后续需要隔离硬件代码或优先使用纯仿真入口。
- 当前 WSL 渲染走 Mesa llvmpipe/EGL，适合 smoke 和轻量评估，不代表高性能 GPU 渲染。
- 原始 `E:\RL_projects\SurRoL` 的 git clone 过程曾超时，`.git` 状态不适合作为可信版本来源；现在已删除该旧目录，保留干净 zip 归档和 clean 解压副本。

## 下一步建议

1. 把当前自研风险监督器接到 SurRoL 的 observation/action/step 接口上，先做 wrapper，不急着训练新策略。
2. 为每个 SurRoL 任务定义统一评估指标：success、reward、step budget、action clipping、near-failure、recovery trigger。
3. 先对 oracle action 做多 seed 扰动评估，验证任务本身的稳定性和风险标签质量。
4. 再做策略层实验：baseline policy、risk monitor、human-review trigger、recovery policy。
