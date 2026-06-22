# SurRoL Visual-State Error And Near-Target Drift Experiment

## 一句话结论

这组 5-seed 实验把项目重新收束到 VPPV 论文的核心局限：视觉/深度状态估计错误，以及 RL policy 接近目标后的 final-control drift。结果显示，perception/depth 错误会让 NeedlePick 和 GauzeRetrieve 都失败，且短窗 oracle override 不能可靠恢复，因此应进入人工复核或重新估计；near-target drift 则是可逆的执行偏差，monitor 可以从 perturbed 失败恢复到 5/5 成功。

## Paired Results

| Task | Failure | Seeds | Clean | Perturbed | Monitor | Perturbed Dist | Monitor Dist | Triggers | Suggested Route |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| GauzeRetrieve | depth_scale_error | 5 | 1.000 | 0.000 | 0.000 | 0.265 | 0.265 | 0.000 | human_review / re-estimate visual state |
| NeedlePick | depth_scale_error | 5 | 1.000 | 0.000 | 0.000 | 0.218 | 0.233 | 1.600 | human_review / re-estimate visual state |
| GauzeRetrieve | near_target_drift | 5 | 1.000 | 0.000 | 1.000 | 0.046 | 0.011 | 1.000 | auto_recovery |
| NeedlePick | near_target_drift | 5 | 1.000 | 0.200 | 1.000 | 0.096 | 0.019 | 1.000 | auto_recovery |
| GauzeRetrieve | perception_bias | 5 | 1.000 | 0.000 | 0.000 | 0.265 | 0.265 | 0.000 | human_review / re-estimate visual state |
| NeedlePick | perception_bias | 5 | 1.000 | 0.000 | 0.000 | 0.226 | 0.226 | 1.600 | human_review / re-estimate visual state |

## Interpretation

- `perception_bias` and `depth_scale_error` proxy errors in image parsing, depth estimation, or perceptual state regression.
- These perception-state failures should not be framed as cases where the robot simply retries the same motion.
- `near_target_drift` proxies the paper-relevant handoff problem from learned high-level motion to final visual-servoing/control.
- This supports a low-intrusion supervisor: preserve the mainstream control pipeline, but route unreliable visual states to review/re-estimation.

## Limitations

- The perception errors are state-space proxies, not actual FastSAM/IGEV image failures.
- Only 5 seeds per task are reported here.
- The recovery controller is still scripted oracle override, not a learned or robot-certified controller.

## Outputs

- `runs/surrol_needlepick_perception_drift_w16_5seed.csv`
- `runs/surrol_gauzeretrieve_perception_drift_w16_5seed.csv`
- `reports/tables/surrol_perception_drift_summary.csv`
- `reports/tables/surrol_perception_drift_paired.csv`