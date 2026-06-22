# Observable Proxy Risk Sweep

## Takeaway

Using the existing 10-seed step logs, an offline observable risk score detects silent jaw-stuck faults in both NeedlePick and GauzeRetrieve. At threshold 3.0, fault alarm rate is 10/10 for both tasks, while nominal monitor-corrected runs also alarm late because the current proxy treats normal pre-grasp stalls as risk. This means the proxy is useful but not yet well calibrated.

## Risk Score

```text
risk_score = close_score + stall_score + far_score + no_improve_score
```

- `close_score`: close command count >= 4.
- `stall_score`: stalled_count / 8, clipped to [0, 1].
- `far_score`: current distance is still high relative to the initial distance.
- `no_improve_score`: cumulative best distance has barely improved.

## Threshold 3.0 Summary

| Task | Failure | Controller | Alarm Rate | Mean Alarm Step |
|---|---|---|---:|---:|
| GauzeRetrieve | jaw_stuck_open | monitor_corrected | 1.000 | 30.0 |
| GauzeRetrieve | jaw_stuck_open | perturbed | 1.000 | 30.0 |
| GauzeRetrieve | none | monitor_corrected | 0.000 |  |
| NeedlePick | jaw_stuck_open | monitor_corrected | 1.000 | 34.7 |
| NeedlePick | jaw_stuck_open | perturbed | 1.000 | 34.7 |
| NeedlePick | none | monitor_corrected | 0.000 |  |

## Interpretation

- Fault sensitivity is strong: jaw-stuck perturbed episodes are detected for both tasks.
- Specificity is still weak: nominal episodes can trigger late alarms because normal approach/grasp phases contain stalls.
- The next improvement should add phase gating or a learned calibration layer so normal pre-grasp pauses are not treated the same as failed grasps.

## Outputs

- `reports/tables/observable_proxy_scored_steps_10seed.csv`
- `reports/tables/observable_proxy_threshold_sweep_10seed.csv`
- `reports/figures/observable_proxy_risk/observable_proxy_threshold_sweep.png`