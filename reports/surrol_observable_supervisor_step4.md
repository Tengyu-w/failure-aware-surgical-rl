# SurRoL Observable Supervisor Step 4

## Takeaway

Step 4 reduces the supervisor's decision dependence on privileged SurRoL phase/contact state. For silent jaw-stuck failures, the monitor now uses observable proxy signals--jaw close command count, distance stagnation, and minimum-distance improvement--to trigger grasp retry. On the current 10-seed NeedlePick and GauzeRetrieve evidence, observable recovery keeps the hard-fault result at 0/10 perturbed success to 10/10 recovered success for both tasks.

## Observable Versus Privileged Recovery

| Task | Policy | Seeds | Perturbed | Recovered | Triggers | Replans | Steps | Decision Dependency |
|---|---|---:|---:|---:|---:|---:|---:|---|
| GauzeRetrieve | internal_phase_replan | 5 | 0.000 | 1.000 | 5.000 | 2.000 | 108.6 | internal waypoint/contact state |
| GauzeRetrieve | observable_phase_replan | 5 | 0.000 | 1.000 | 3.000 | 2.000 | 102.0 | observable command/progress proxy |
| GauzeRetrieve | observable_phase_replan | 10 | 0.000 | 1.000 | 3.000 | 2.000 | 101.8 | observable command/progress proxy |
| NeedlePick | internal_phase_replan | 5 | 0.000 | 1.000 | 3.400 | 1.200 | 91.2 | internal waypoint/contact state |
| NeedlePick | observable_phase_replan | 5 | 0.000 | 1.000 | 3.000 | 1.800 | 102.4 | observable command/progress proxy |
| NeedlePick | observable_phase_replan | 10 | 0.000 | 1.000 | 3.000 | 1.700 | 102.6 | observable command/progress proxy |

## Observable Risk Sweep At Threshold 3.0

| Task | Fault Alarm Rate | Nominal Alarm Rate | Interpretation |
|---|---:|---:|---|
| GauzeRetrieve | 1.000 | 0.000 | detects jaw-stuck without nominal false alarms in this 10-seed log |
| NeedlePick | 1.000 | 0.000 | detects jaw-stuck without nominal false alarms in this 10-seed log |

## Signal Audit

| Module | Signal | Status | Role |
|---|---|---|---|
| internal_phase_replan | active waypoint index | privileged | upper-bound baseline for phase-aware recovery |
| internal_phase_replan | activation/contact state | privileged | upper-bound baseline; not a deployable monitor signal |
| observable_phase_replan | jaw close command count | observable_proxy | detects attempted grasp without reading simulator contact labels |
| observable_phase_replan | goal-distance stagnation | observable_proxy | detects lack of progress after repeated close commands |
| observable_phase_replan | minimum-distance improvement | observable_proxy | separates normal approach from failed grasp retry candidates |
| observable risk sweep | risk_score threshold | observable_proxy | calibrates sensitivity/specificity of offline observable detection |
| learned_route_classifier | review/abort routing probability | partly_observable | supports future online learned risk routing, but still includes post-episode features |
| recovery primitive | waypoint regeneration after observable trigger | privileged_primitive | remaining limitation: decision is observable, execution primitive is still simulator/scripted |

## Link To Learned Risk Routing

The Step 3 learned route classifier complements this observable supervisor: it reaches 0.846 held-out accuracy and 0.828 macro-F1, with 0.000 missed review-or-abort rate. However, it is still episode-level and includes post-episode features, so Step 4 treats it as research evidence for future online routing rather than a deployable monitor.

## What Is Confirmed

- The decision trigger for jaw-stuck recovery can be replaced by observable command/progress proxies while retaining 10/10 recovery on both core tasks.
- Threshold-3.0 offline scoring detects 10/10 jaw-stuck perturbed episodes for both tasks and does not alarm on the nominal monitor-corrected episodes in these logs.
- Internal phase/contact recovery remains a useful upper-bound baseline, not the main deployability claim.

## What Remains Limited

- Recovery execution still calls a scripted SurRoL waypoint regeneration primitive.
- The observable proxy is currently validated mainly on silent jaw-stuck; standard action corruptions still rely on internal phase-aware recovery in the strongest 10-seed suite.
- The learned route classifier is not yet window-level or online deployable.
- All results remain simulation-only and should not be presented as clinical or real-robot validation.

## Outputs

- `reports/tables/surrol_observable_signal_audit.csv`
- `reports/tables/surrol_observable_vs_privileged_jaw_stuck.csv`
- `reports/tables/observable_proxy_threshold_sweep_10seed.csv`
- `reports/figures/observable_proxy_risk/observable_proxy_threshold_sweep.png`