# SurRoL Human-Review Re-Estimation Closed-Loop Experiment

## 一句话结论

这一步把前面的 `human_review` 从离线路由变成了可验证的闭环：当 SurRoL 中出现 perception bias 或 depth scale error 时，盲目 oracle override 不能恢复；但如果触发 review/re-estimation，即停止使用错误视觉状态并重新估计状态，NeedlePick 和 GauzeRetrieve 都能从 0/5 恢复到 5/5。

## Paired Results

| Task | Failure | Seeds | Perturbed | Blind Monitor | Review/Re-estimate | Blind Dist | Re-est Dist | Re-est Triggers |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| GauzeRetrieve | perception_bias | 5 | 0.000 | 0.000 | 1.000 | 0.265 | 0.013 | 1.000 |
| GauzeRetrieve | depth_scale_error | 5 | 0.000 | 0.000 | 1.000 | 0.265 | 0.013 | 1.000 |
| NeedlePick | perception_bias | 5 | 0.000 | 0.000 | 1.000 | 0.226 | 0.020 | 1.000 |
| NeedlePick | depth_scale_error | 5 | 0.000 | 0.000 | 1.000 | 0.233 | 0.020 | 1.000 |

## Interpretation

- This supports the project framing that visual-state errors should not be handled as ordinary motion drift.
- The supervisor's job is to route unreliable visual states to re-estimation, not to repeatedly apply the same recovery primitive.
- The result is an upper-bound proxy because the re-estimation step uses the clean simulator state rather than a real FastSAM/IGEV re-run.

## Thesis-Ready Wording

In VPPV-style surgical autonomy, failures caused by perceptual state errors require a different intervention from recoverable execution drift. In our SurRoL proxy, blind monitor override failed to recover perception-bias and depth-scale corruptions, whereas a review-triggered state re-estimation policy restored task success across both NeedlePick and GauzeRetrieve.

## Outputs

- `runs/surrol_needlepick_review_reestimate_w16_5seed.csv`
- `runs/surrol_gauzeretrieve_review_reestimate_w16_5seed.csv`
- `reports/tables/surrol_review_reestimate_summary.csv`
- `reports/tables/surrol_review_reestimate_paired.csv`