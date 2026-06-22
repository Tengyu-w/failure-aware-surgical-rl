# SurRoL Severity Sweep For Visual-State Error And Near-Target Drift

## 一句话结论

这一步完成了 error/drift severity sweep：在 NeedlePick 和 GauzeRetrieve 上分别测试低、中、高三档 perception bias、depth scale error 和 near-target drift。结果支持一个更细的分流边界：视觉/深度状态错误一旦造成失败，短窗 recovery 基本不能解决，应进入视觉状态重估或人工复核；near-target drift 在中高强度下可以被 monitor 自动恢复，但低强度 drift 在 NeedlePick 上存在漏触发，说明阈值还需要校准。

## Paired Severity Results

| Task | Failure | Severity | Seeds | Perturbed | Monitor | Triggers | Perturbed Dist | Monitor Dist | Suggested Route |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| GauzeRetrieve | depth_scale_error | low | 5 | 0.000 | 0.000 | 2.000 | 0.268 | 0.268 | human_review / re-estimate state |
| GauzeRetrieve | depth_scale_error | medium | 5 | 0.000 | 0.000 | 0.000 | 0.265 | 0.265 | human_review / re-estimate state |
| GauzeRetrieve | depth_scale_error | high | 5 | 0.000 | 0.000 | 0.000 | 0.265 | 0.265 | human_review / re-estimate state |
| NeedlePick | depth_scale_error | low | 5 | 0.000 | 0.000 | 0.400 | 0.219 | 0.213 | human_review / re-estimate state |
| NeedlePick | depth_scale_error | medium | 5 | 0.000 | 0.000 | 1.600 | 0.218 | 0.233 | human_review / re-estimate state |
| NeedlePick | depth_scale_error | high | 5 | 0.000 | 0.000 | 0.200 | 0.205 | 0.204 | human_review / re-estimate state |
| GauzeRetrieve | near_target_drift | low | 5 | 1.000 | 1.000 | 0.000 | 0.018 | 0.018 | auto_execute |
| GauzeRetrieve | near_target_drift | medium | 5 | 0.000 | 1.000 | 1.000 | 0.046 | 0.011 | auto_recovery |
| GauzeRetrieve | near_target_drift | high | 5 | 0.000 | 1.000 | 1.000 | 0.105 | 0.011 | auto_recovery |
| NeedlePick | near_target_drift | low | 5 | 0.200 | 0.200 | 0.000 | 0.028 | 0.028 | threshold_needs_calibration |
| NeedlePick | near_target_drift | medium | 5 | 0.200 | 1.000 | 1.000 | 0.096 | 0.019 | auto_recovery |
| NeedlePick | near_target_drift | high | 5 | 0.000 | 1.000 | 1.000 | 0.123 | 0.019 | auto_recovery |
| GauzeRetrieve | perception_bias | low | 5 | 1.000 | 1.000 | 0.000 | 0.013 | 0.013 | auto_execute_or_review_by_threshold |
| GauzeRetrieve | perception_bias | medium | 5 | 0.000 | 0.000 | 0.000 | 0.265 | 0.265 | human_review / re-estimate state |
| GauzeRetrieve | perception_bias | high | 5 | 0.000 | 0.000 | 0.000 | 0.265 | 0.265 | human_review / re-estimate state |
| NeedlePick | perception_bias | low | 5 | 0.600 | 0.600 | 0.000 | 0.087 | 0.087 | human_review / re-estimate state |
| NeedlePick | perception_bias | medium | 5 | 0.000 | 0.000 | 1.600 | 0.226 | 0.226 | human_review / re-estimate state |
| NeedlePick | perception_bias | high | 5 | 0.000 | 0.000 | 0.400 | 0.224 | 0.222 | human_review / re-estimate state |

## 边界解读

- `perception_bias`: GauzeRetrieve 低强度仍可承受，但中高强度失败；NeedlePick 低强度已有 2/5 失败，中高强度 0/5。
- `depth_scale_error`: 两个任务即使低强度也较脆弱，说明深度/三维状态误差是更高优先级的复核对象。
- `near_target_drift`: 中高强度漂移可由 monitor 恢复到 5/5；低强度下 GauzeRetrieve 本身成功，NeedlePick 存在漏触发，应调低 near-target drift 的检测阈值或增加终点误差监测。

## 和初衷的关系

这组实验没有改变主流手术机器人工作流，而是在现有视觉状态估计与 final control 交接处增加可靠性边界：
可逆漂移允许自动恢复，视觉/深度状态不可靠则进入复核或重估。

## 局限

- Severity 是状态空间代理，不是真实 FastSAM/IGEV 图像错误。
- 每个任务每档 5 seed，仍然是轻量研究原型证据。
- Monitor 阈值仍是规则型，下一步应把漏触发样本用于校准。

## Outputs

- `reports/tables/surrol_severity_sweep_summary.csv`
- `reports/tables/surrol_severity_sweep_paired.csv`
- `reports/figures/surrol_severity_sweep/needlepick_severity_sweep.png`
- `reports/figures/surrol_severity_sweep/gauzeretrieve_severity_sweep.png`