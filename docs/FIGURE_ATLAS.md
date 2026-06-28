# Figure Atlas

This document explains how the public figures and media are organized. The goal
is to make the visual evidence readable as a research story rather than as a
loose folder of PNG files.

## Figure And Media Groups

| Stage | Folder | What The Reader Should Look For |
| --- | --- | --- |
| SurRoL rendered evidence | `reports/media/surrol_render_evidence/` | Actual SurRoL/PyBullet rendered rollouts for NeedleReach, NeedlePick, and GauzeRetrieve. |
| Risk-gated tangent visuals | `reports/figures/risk_gated_tangent_visuals/` | Proxy controller architecture, budget/intervention result, trajectories, and snapshots. |
| Mechanism-routed tangent visuals | `reports/figures/mechanism_routed_tangent_v5d/` | ECG-inspired mechanism router metrics and Stage 1/Stage 2 activation split. |
| SurRoL phase-aware recovery | `reports/figures/surrol_phase_aware/` | Recovery success rates and representative distance curves. |
| Observable supervisor | `reports/figures/observable_proxy_risk/` and related observable folders | Threshold behavior and observable jaw-stuck recovery evidence. |
| Learned route classifier | `reports/tables/surrol_learned_route_classifier_*.csv` and report tables | Route prediction metrics, confusion table, and feature weights. |
| Embedding-risk PPO | `reports/figures/embedding_risk_training_pilot/` | Reward shaping and hard-negative curriculum training summaries. |
| ECG-style RL reliability suite | `reports/figures/ecg_style_rl_reliability_suite/` | Representation PCA, injected-failure risk ranking, and review-score separation. |
| Multi-signal reliability upgrade | `reports/figures/multisignal_reliability_upgrade/` | Single-family versus multi-signal risk ablation and mechanism-router metrics. |
| Failure-aware VPPV evidence | `reports/figures/failure_aware_vppv/` | VPPV step evidence, severity holdout, mixed-priority audit, model-derived route assignment, and true mixed-fault rollout figures. |

## Representative Visual Evidence

| Question | Representative figure or media | What it supports | Scope boundary |
| --- | --- | --- | --- |
| What does proxy recovery look like in motion? | [CircleRL recovery MP4](../reports/media/circlerl_recovery_demo/circlerl_bias_recovery.mp4), [GIF preview](../reports/media/circlerl_recovery_demo/circlerl_bias_recovery.gif), [trace CSV](../reports/media/circlerl_recovery_demo/circlerl_bias_recovery_trace.csv) | A biased target estimate first causes drift; monitor recovery re-estimates the target and routes control back toward completion. | Custom proxy media, not SurRoL/PyBullet and not real-robot footage. |
| Is there rendered surgical simulation evidence? | [NeedleReach frame](../reports/media/surrol_render_evidence/needlereach/frames/needlereach_step_020.png), [NeedlePick frame](../reports/media/surrol_render_evidence/needlepick/frames/needlepick_step_040.png), [GauzeRetrieve frame](../reports/media/surrol_render_evidence/gauzeretrieve/frames/gauzeretrieve_step_034.png) | The work was migrated from the custom proxy environment into SurRoL/PyBullet tasks. | Rendered simulator frames only. |
| Are full task rollouts available? | [NeedleReach GIF](../reports/media/surrol_render_evidence/needlereach/needlereach_oracle_rollout.gif), [NeedlePick MP4](../reports/media/surrol_render_evidence/needlepick/needlepick_oracle_rollout.mp4), [GauzeRetrieve MP4](../reports/media/surrol_render_evidence/gauzeretrieve/gauzeretrieve_oracle_rollout.mp4) | The repository contains visual rollout evidence, not only static plots. | Oracle rollout media used for evidence and reproducibility context. |
| Does risk-gated tangent reduce unnecessary supervision? | [Aggregate budget/intervention](../reports/figures/risk_gated_tangent_visuals/aggregate_budget_intervention.png), [safety-intervention frontier](../reports/figures/risk_gated_tangent_visuals/safety_intervention_frontier.png) | Budget exhaustion remains controlled while activation is lower than always-on tangent supervision. | Custom constrained surgical-tool proxy. |
| When does the risk gate activate? | [Strict risk timeline](../reports/figures/risk_gated_tangent_visuals/risk_timeline_strict.png), [prototype trajectory](../reports/figures/risk_gated_tangent_visuals/trajectory_prototype.png), [strict trajectory](../reports/figures/risk_gated_tangent_visuals/trajectory_strict.png) | The risk signal is used as a runtime decision variable rather than only a post-hoc explanation. | Controller diagnostic plot, not a physical robot trace. |
| Does mechanism routing separate different failure causes? | [Router metrics](../reports/figures/mechanism_routed_tangent_v5d/mechanism_router_metrics.png), [stage split](../reports/figures/mechanism_routed_tangent_v5d/mechanism_router_stage_split.png) | Boundary-risk intervention and residual review risk are analyzed separately. | Route labels are simulation-derived, not expert annotations. |
| Which execution faults are recoverable? | [Phase-aware success by failure](../reports/figures/surrol_phase_aware/success_rate_by_failure.png), [representative distance curves](../reports/figures/surrol_phase_aware/representative_distance_curves.png), [phase replan timeline](../reports/figures/surrol_phase_aware/phase_replan_timeline.png) | Action noise, dropout, and execution slip can be routed to short-window recovery in these simulator settings. | Recovery primitives are still scripted. |
| Can observable signals handle grasp/contact uncertainty? | [10-seed observable jaw-stuck recovery](../reports/figures/surrol_cross_task_observable_jaw_stuck_10seed/cross_task_jaw_stuck_recovery.png), [observable proxy threshold sweep](../reports/figures/observable_proxy_risk/observable_proxy_threshold_sweep.png) | The supervisor can use observable proxies rather than relying only on privileged internal state. | Observable proxy is not a validated real sensor model. |
| Which perception-like errors should route to review or re-estimation? | [NeedlePick severity sweep](../reports/figures/surrol_severity_sweep/needlepick_severity_sweep.png), [GauzeRetrieve severity sweep](../reports/figures/surrol_severity_sweep/gauzeretrieve_severity_sweep.png) | Visual-state and depth-scale errors behave differently from recoverable near-target drift. | State-space proxy for perception error, not direct segmentation/depth output. |
| Is there representation-level reliability evidence? | [Embedding by route](../reports/figures/surrol_reliability_memory/embedding_by_route.png), [embedding by failure family](../reports/figures/surrol_reliability_memory/embedding_by_family.png) | Failure families and recovery routes can be inspected in a learned reliability-memory space. | Offline diagnostic analysis. |
| Did the ECG-style upgrade go beyond embedding alone? | [ECG-style RL reliability suite](../reports/figures/ecg_style_rl_reliability_suite/ecg_style_rl_reliability_suite.png), [multi-signal reliability upgrade](../reports/figures/multisignal_reliability_upgrade/multisignal_reliability_upgrade.png) | The analysis combines representation, uncertainty, robustness, prototype, KNN, and route evidence. | Research prototype; not clinical validation. |
| Can routes be derived from model behavior regions? | [Model-derived PCA](../reports/figures/failure_aware_vppv/failure_aware_vppv_model_derived_pca.png), [cluster fingerprints](../reports/figures/failure_aware_vppv/failure_aware_vppv_model_derived_cluster_fingerprints.png) | Behavior clusters are mapped to route assignments before held-out weak-label evaluation. | Simulator rollout representation, not real clinical data. |
| Does VPPV mixed-fault routing recover in SurRoL? | [True mixed success](../reports/figures/failure_aware_vppv/failure_aware_vppv_true_mixed_success.png), [distance traces](../reports/figures/failure_aware_vppv/failure_aware_vppv_true_mixed_distance_traces.png) | Perturbed mixed faults fail while priority-routed mixed faults recover in the 5-seed smoke run. | Scripted-oracle PyBullet simulation. |
| Did risk-informed training improve the policy? | [Multi-seed curriculum metrics](../reports/figures/embedding_risk_training_pilot/multiseed_curriculum_metrics.png), [curriculum fine-tune metrics](../reports/figures/embedding_risk_training_pilot/curriculum_finetune_metrics.png) | Embedding-risk signals were connected to the training loop and evaluated. | Preliminary; not the main claimed improvement. |

## Recommended Reading Order

1. Start with `reports/media/surrol_render_evidence/` to see that the project
   includes SurRoL/PyBullet rendered surgical simulation, not only proxy plots.
2. Open `reports/figures/risk_gated_tangent_visuals/aggregate_budget_intervention.png`
   to understand the controller-level safety/activation tradeoff.
3. Open `reports/figures/mechanism_routed_tangent_v5d/mechanism_router_metrics.png`
   and `mechanism_router_stage_split.png` to understand the ECG-inspired
   mechanism-routing upgrade.
4. Read SurRoL recovery figures and tables together with
   `reports/surrol_master_results.md`.
5. Use embedding-risk training figures only as preliminary training-loop
   evidence, not as the main project claim.
6. Use ECG-style and multi-signal reliability figures to show the broader
   upgrade beyond embedding alone.
7. Use `reports/figures/failure_aware_vppv/` for the final VPPV route story:
   step evidence, model-derived route assignment, and true mixed-fault rollout.

## Interpretation Notes

The proxy trajectory and controller figures are not SurRoL screenshots. They
belong to the custom constrained surgical-tool environment.

The SurRoL media are actual rendered simulation rollouts. They support the
claim that the project migrated beyond the custom proxy, but they are still
simulation evidence.

The mechanism-routed figures should be read as controller-level reliability
evidence. They show that the supervisor preserves budget safety while slightly
reducing unnecessary activation and separating route mechanisms.
