# SurRoL Unsafe-Zone / Abort-Candidate Proxy

## 一句话结论

这一步给 SurRoL 增加了一个不可逆风险代理：在目标附近放置 forbidden/danger zone，如果 near-target drift 的恢复轨迹进入危险半径，risk-aware policy 不再继续 recovery，而是触发 abort_candidate。当前 NeedlePick 5-seed 中，正常轨迹 0/5 中止，near-target drift 在 monitor 下 2/5 中止、3/5 安全恢复。

## Summary

- Source: `runs\surrol_needlepick_unsafe_abort_r052_w16_20seed.csv`

| Failure | Controller | Episodes | Success | Unsafe Abort | Warning Events | Min Danger Dist | Triggers |
|---|---|---:|---:|---:|---:|---:|---:|
| near_target_drift | clean | 20 | 1.000 | 0.000 | 2.500 | 0.061 | 0.000 |
| near_target_drift | monitor_corrected | 20 | 0.550 | 0.450 | 2.500 | 0.053 | 1.450 |
| near_target_drift | perturbed | 20 | 0.000 | 0.000 | 4.650 | 0.036 | 0.000 |
| none | clean | 20 | 1.000 | 0.000 | 2.500 | 0.061 | 0.000 |
| none | monitor_corrected | 20 | 0.850 | 0.150 | 2.100 | 0.062 | 0.150 |

## Interpretation

- This is not a real tissue-damage model; it is a forbidden-zone proxy for irreversible-risk reasoning.
- The result demonstrates the intended behavior: recovery is allowed only if it stays outside the danger radius.
- With 20 seeds, radius 0.052 still produces some nominal false aborts under monitor_corrected, so the current danger-zone proxy should be treated as a conservative research signal rather than a deployable threshold.

## Limitations

- Only NeedlePick is reported in this first unsafe-zone pass.
- The danger zone is a geometric proxy near the goal, not force/contact/tissue deformation.
- The next step is to define task-specific forbidden regions and include them in learned risk-head labels.