# Evidence Index

This page indexes the most important evidence files for a repository reader. It
is organized by claim so that each statement in the README has a traceable
report, table, figure, or media file.

## Visual SurRoL Migration Evidence

This section is the actual SurRoL/PyBullet visual evidence. It is separate from
the `prototype` and `strict` risk-gated tangent snapshots, which belong to the
custom proxy controller experiment.

| Claim | Evidence |
|---|---|
| The project moved beyond the custom proxy into SurRoL/PyBullet simulation. | [NeedleReach GIF](../reports/media/surrol_render_evidence/needlereach/needlereach_oracle_rollout.gif), [NeedlePick GIF](../reports/media/surrol_render_evidence/needlepick/needlepick_oracle_rollout.gif), [GauzeRetrieve GIF](../reports/media/surrol_render_evidence/gauzeretrieve/gauzeretrieve_oracle_rollout.gif) |
| Rendered rollouts have step traces, not only screenshots. | [NeedleReach trace](../reports/media/surrol_render_evidence/needlereach/rollout_trace.csv), [NeedlePick trace](../reports/media/surrol_render_evidence/needlepick/rollout_trace.csv), [GauzeRetrieve trace](../reports/media/surrol_render_evidence/gauzeretrieve/rollout_trace.csv) |
| Rendered rollouts also have selected frame PNGs. | [NeedleReach frames](../reports/media/surrol_render_evidence/needlereach/frames/), [NeedlePick frames](../reports/media/surrol_render_evidence/needlepick/frames/), [GauzeRetrieve frames](../reports/media/surrol_render_evidence/gauzeretrieve/frames/) |
| Recovery behavior is visualized. | [phase-aware success figure](../reports/figures/surrol_phase_aware/success_rate_by_failure.png), [distance curves](../reports/figures/surrol_phase_aware/representative_distance_curves.png), [observable jaw-stuck recovery](../reports/figures/surrol_cross_task_observable_jaw_stuck_10seed/cross_task_jaw_stuck_recovery.png) |

## Risk-Gated Tangent Backup In The Custom Proxy

This section is the controller-level result from the self-built proxy
environment. The `prototype` and `strict` figures are top-down/controller
visualizations from the proxy simulator; they are not SurRoL screenshots.

| Claim | Evidence |
|---|---|
| Reliability analysis can become a runtime action-level decision signal. | [risk-gated tangent report](../reports/risk_gated_tangent_report.md) |
| Risk-gated tangent preserves always-tangent safety while reducing supervisor activation. | [aggregate summary](../outputs/risk_gated_tangent/aggregate_summary.csv), [budget/intervention figure](../reports/figures/risk_gated_tangent_visuals/aggregate_budget_intervention.png) |
| The gate is interpretable rather than a black-box always-on correction. | [risk architecture](../reports/figures/risk_gated_tangent_visuals/risk_gate_architecture.png), [risk coefficients](../reports/figures/risk_gated_tangent_visuals/risk_model_coefficients.png) |
| ECG-style mechanism-separated routing can be transferred to the proxy RL supervisor. | [mechanism-routed tangent report](../reports/mechanism_routed_tangent_v5d_report.md), [mechanism aggregate](../outputs/mechanism_routed_tangent_v5d_aggregate_summary.csv), [stage split figure](../reports/figures/mechanism_routed_tangent_v5d/mechanism_router_stage_split.png) |
| The process can be shown visually as trajectories and simulated snapshots. | [prototype snapshots](../reports/figures/risk_gated_tangent_visuals/render_snapshots_prototype.png), [strict trajectory](../reports/figures/risk_gated_tangent_visuals/trajectory_strict.png), [strict snapshots](../reports/figures/risk_gated_tangent_visuals/render_snapshots_strict.png) |

## Project Logic And Research Evidence

| Step | Purpose | Main Files |
|---|---|---|
| Stage 1 | Build a self-contained constrained proxy to test obstacle avoidance, tangent backup, and safety-budget supervision | [source environments](../src/constraint_surgical_rl/envs/), [custom proxy recovery report](../reports/cross_task_recovery_report.md) |
| Stage 2 | Migrate the reliability-supervision idea into SurRoL/PyBullet tasks | [SurRoL rendered evidence](../reports/media/surrol_render_evidence/) |
| Stage 3 | Formalize four runtime intervention routes: auto-execute, auto-recovery, human-review, abort-candidate | [taxonomy table](../reports/tables/surrol_fault_taxonomy.csv), [taxonomy report](../reports/surrol_fault_taxonomy_step2.md) |
| Stage 4 | Stress-test SurRoL recovery with multi-seed fault injections | [master paired results](../reports/tables/surrol_master_paired_results.csv), [master report](../reports/surrol_master_results.md) |
| Stage 5 | Add learned/observable reliability supervisors and risk-gated proxy backup control | [route classifier report](../reports/surrol_learned_route_classifier_step3.md), [observable supervisor report](../reports/surrol_observable_supervisor_step4.md), [risk-gated tangent report](../reports/risk_gated_tangent_report.md) |
| Stage 6 | Upgrade the proxy controller to ECG-style mechanism-separated routing | [mechanism-routed tangent report](../reports/mechanism_routed_tangent_v5d_report.md), [mechanism aggregate](../outputs/mechanism_routed_tangent_v5d_aggregate_summary.csv), [mechanism figures](../reports/figures/mechanism_routed_tangent_v5d/) |
| Stage 7 | Test whether embedding/KNN risk can become a training signal | [embedding-risk training pilot](../reports/embedding_risk_training_pilot.md), [reward-only pilot comparison](../outputs/embedding_risk_training_pilot_comparison.csv), [curriculum fine-tune summary](../outputs/embedding_risk_curriculum_finetune_pilot_summary.csv), [multi-seed aggregate](../outputs/embedding_risk_multiseed_curriculum_aggregate_summary.csv), [multi-seed figure](../reports/figures/embedding_risk_training_pilot/multiseed_curriculum_metrics.png) |
| Stage 8 | Explain the complete learning-to-routing chain | [learning-to-routing flow](LEARNING_TO_ROUTING_FLOW.md), [risk dataset](../outputs/risk_dataset/risk_dataset.csv), [visual action risk head script](../scripts/train_surrol_visual_action_risk_head.py), [visual recovery memory script](../scripts/train_surrol_visual_recovery_memory.py) |
| Stage 9 | Run ECG-style broad reliability suite and model upgrade | [ECG-style RL upgrade](ECG_STYLE_RL_UPGRADE.md), [suite report](../reports/ecg_style_rl_reliability_suite.md), [multi-signal report](../reports/multisignal_reliability_upgrade.md), [suite figure](../reports/figures/ecg_style_rl_reliability_suite/ecg_style_rl_reliability_suite.png), [multi-signal figure](../reports/figures/multisignal_reliability_upgrade/multisignal_reliability_upgrade.png) |
| Stage 10 | Reframe the work around the real VPPV bottleneck and run a composite mechanism router | [failure-aware VPPV framework](FAILURE_AWARE_VPPV_MULTIEVIDENCE_FRAMEWORK.md), [composite router report](../reports/failure_aware_vppv_composite_router.md), [route summary](../reports/tables/failure_aware_vppv_route_summary.csv) |
| Stage 11 | Condense the VPPV pain point, route logic, and evidence into a supervisor-facing brief | [VPPV supervisor brief](../reports/failure_aware_vppv_supervisor_brief.md), [VPPV supervisor-pack figure](../reports/figures/failure_aware_vppv/failure_aware_vppv_supervisor_pack.png) |
| Stage 12 | Build step-level VPPV evidence for early warning and single-evidence ablation | [step evidence report](../reports/failure_aware_vppv_step_evidence.md), [step dataset](../reports/tables/failure_aware_vppv_step_dataset.csv), [step evidence figure](../reports/figures/failure_aware_vppv/failure_aware_vppv_step_evidence.png) |
| Stage 13 | Test whether VPPV mechanism evidence transfers across SurRoL tasks | [cross-task VPPV report](../reports/failure_aware_vppv_cross_task_generalization.md), [cross-task summary](../reports/tables/failure_aware_vppv_cross_task_summary.csv), [cross-task confusion](../reports/tables/failure_aware_vppv_cross_task_confusion.csv) |
| Stage 14 | Test whether low/medium severity boundaries survive held-out high severity | [severity holdout report](../reports/failure_aware_vppv_severity_holdout.md), [severity holdout summary](../reports/tables/failure_aware_vppv_severity_holdout_summary.csv), [severity holdout figure](../reports/figures/failure_aware_vppv/failure_aware_vppv_severity_holdout.png) |
| Stage 15 | Audit whether mixed visual/depth/policy evidence follows the intended priority order | [mixed-priority report](../reports/failure_aware_vppv_mixed_perturbation_priority.md), [mixed-priority summary](../reports/tables/failure_aware_vppv_mixed_priority_summary.csv), [mixed-priority evidence figure](../reports/figures/failure_aware_vppv/failure_aware_vppv_mixed_priority_evidence.png) |
| Stage 16 | Derive routes from rollout behavior regions | [behavior-derived routing report](../reports/failure_aware_vppv_model_derived_routing.md), [behavior-derived summary](../reports/tables/failure_aware_vppv_model_derived_summary.csv), [behavior-derived PCA figure](../reports/figures/failure_aware_vppv/failure_aware_vppv_model_derived_pca.png) |
| Stage 17 | Execute true mixed visual/depth/near-target fault proxies inside SurRoL/PyBullet | [true mixed rollout report](../reports/failure_aware_vppv_true_mixed_rollouts.md), [true mixed paired table](../reports/tables/failure_aware_vppv_true_mixed_rollout_paired.csv), [true mixed success figure](../reports/figures/failure_aware_vppv/failure_aware_vppv_true_mixed_success.png) |
| Stage 18 | Package the final VPPV evidence ladder and claim boundaries | [final teacher brief](../reports/failure_aware_vppv_final_teacher_brief.md), [final evidence matrix](../reports/tables/failure_aware_vppv_final_evidence_matrix.csv), [GitHub readiness audit](../reports/failure_aware_vppv_github_readiness_audit.md) |

## Key Result Tables

| Table | Description |
|---|---|
| [surrol_master_episode_rows.csv](../reports/tables/surrol_master_episode_rows.csv) | episode-level source rows from the SurRoL reliability suites |
| [surrol_master_paired_results.csv](../reports/tables/surrol_master_paired_results.csv) | clean, perturbed, and recovered paired summary |
| [surrol_fault_taxonomy.csv](../reports/tables/surrol_fault_taxonomy.csv) | task/failure/family/route taxonomy with seed counts |
| [surrol_learned_route_classifier_summary.csv](../reports/tables/surrol_learned_route_classifier_summary.csv) | held-out summary for the learned route classifier |
| [surrol_observable_vs_privileged_jaw_stuck.csv](../reports/tables/surrol_observable_vs_privileged_jaw_stuck.csv) | internal phase-aware versus observable proxy recovery comparison |
| [observable_proxy_threshold_sweep_10seed.csv](../reports/tables/observable_proxy_threshold_sweep_10seed.csv) | threshold sweep for observable risk scoring |
| [risk_gated_tangent/aggregate_summary.csv](../outputs/risk_gated_tangent/aggregate_summary.csv) | cross-seed prototype/strict comparison of unshielded, always tangent, and risk-gated tangent |
| [risk_gated_tangent/summary.csv](../outputs/risk_gated_tangent/summary.csv) | seed-level formal PPO comparison for the risk-gated tangent result |
| [mechanism_routed_tangent_v5d_aggregate_summary.csv](../outputs/mechanism_routed_tangent_v5d_aggregate_summary.csv) | ECG-inspired mechanism-routed tangent comparison against always tangent and risk-gated tangent |
| [mechanism_routed_tangent_v5d_route_summary.csv](../outputs/mechanism_routed_tangent_v5d_route_summary.csv) | Stage 1 boundary versus Stage 2 residual route activity for the mechanism router |
| [embedding_risk_training_pilot_comparison.csv](../outputs/embedding_risk_training_pilot_comparison.csv) | one-seed PPO pilot comparing baseline training against embedding-risk reward shaping |
| [embedding_risk_curriculum_finetune_pilot_summary.csv](../outputs/embedding_risk_curriculum_finetune_pilot_summary.csv) | one-seed PPO pilot comparing reward shaping, hard-negative curriculum, and curriculum fine-tuning |
| [ecg_style_rl_representation_quality.csv](../reports/tables/ecg_style_rl_representation_quality.csv) | silhouette, Davies-Bouldin, and PCA variance for the multi-signal route space |
| [ecg_style_rl_uncertainty_diagnostics.csv](../reports/tables/ecg_style_rl_uncertainty_diagnostics.csv) | MSP, entropy, margin, and review-score AUROC diagnostics |
| [ecg_style_rl_robustness_by_failure.csv](../reports/tables/ecg_style_rl_robustness_by_failure.csv) | injected-failure risk ranking |
| [multisignal_review_ablation.csv](../reports/tables/multisignal_review_ablation.csv) | single-family versus multi-signal review/abort risk-head ablation |
| [multisignal_mechanism_router_summary.csv](../reports/tables/multisignal_mechanism_router_summary.csv) | four-way mechanism-router held-out summary |
| [failure_aware_vppv_multievidence_framework.csv](../reports/tables/failure_aware_vppv_multievidence_framework.csv) | VPPV-specific problem, mechanism, evidence-family, and route map |
| [failure_aware_vppv_route_summary.csv](../reports/tables/failure_aware_vppv_route_summary.csv) | composite VPPV router compared with uniform retry, single-score, embedding-only, and visual-only baselines |
| [failure_aware_vppv_mechanism_fingerprints.csv](../reports/tables/failure_aware_vppv_mechanism_fingerprints.csv) | evidence fingerprints for visual, depth, approach-policy, handoff, nominal, and unsafe mechanisms |
| [failure_aware_vppv_step_dataset.csv](../reports/tables/failure_aware_vppv_step_dataset.csv) | VPPV-style step-level dataset for nominal, visual bias, depth-scale error, and policy approach drift |
| [failure_aware_vppv_step_route_summary.csv](../reports/tables/failure_aware_vppv_step_route_summary.csv) | step-route single-evidence and composite weak-label consistency comparison |
| [failure_aware_vppv_step_early_warning_summary.csv](../reports/tables/failure_aware_vppv_step_early_warning_summary.csv) | mechanism-wise alert rate and lead-time summary |
| [failure_aware_vppv_cross_task_summary.csv](../reports/tables/failure_aware_vppv_cross_task_summary.csv) | frozen-threshold cross-task router metrics between NeedlePick and GauzeRetrieve |
| [failure_aware_vppv_cross_task_evidence_transfer.csv](../reports/tables/failure_aware_vppv_cross_task_evidence_transfer.csv) | budgeted evidence capture for visual, depth, policy-proxy, action-outcome, and composite scores |
| [failure_aware_vppv_cross_task_confusion.csv](../reports/tables/failure_aware_vppv_cross_task_confusion.csv) | route confusion matrices for the two cross-task transfer directions |
| [failure_aware_vppv_severity_holdout_summary.csv](../reports/tables/failure_aware_vppv_severity_holdout_summary.csv) | low/medium calibration and high-severity held-out route metrics |
| [failure_aware_vppv_severity_holdout_boundaries.csv](../reports/tables/failure_aware_vppv_severity_holdout_boundaries.csv) | learned first intervention severity for each task/failure pair |
| [failure_aware_vppv_severity_holdout_confusion.csv](../reports/tables/failure_aware_vppv_severity_holdout_confusion.csv) | route confusion tables for severity holdout baselines |
| [failure_aware_vppv_mixed_priority_summary.csv](../reports/tables/failure_aware_vppv_mixed_priority_summary.csv) | priority-router, max-signal, uniform-retry, and single-score comparison on composed mixed evidence |
| [failure_aware_vppv_mixed_priority_scenarios.csv](../reports/tables/failure_aware_vppv_mixed_priority_scenarios.csv) | scenario-level route matching for visual+depth, visual+policy, depth+policy, and all-three mixtures |
| [failure_aware_vppv_mixed_priority_confusion.csv](../reports/tables/failure_aware_vppv_mixed_priority_confusion.csv) | route confusion tables for mixed-priority baselines |
| [failure_aware_vppv_model_derived_summary.csv](../reports/tables/failure_aware_vppv_model_derived_summary.csv) | held-out metrics for rollout behavior-derived route assignment |
| [failure_aware_vppv_model_derived_clusters.csv](../reports/tables/failure_aware_vppv_model_derived_clusters.csv) | behavior cluster fingerprints and assigned routes |
| [failure_aware_vppv_model_derived_transition_points.csv](../reports/tables/failure_aware_vppv_model_derived_transition_points.csv) | first alert step and lead-time check for behavior-derived routes |
| [failure_aware_vppv_true_mixed_rollout_summary.csv](../reports/tables/failure_aware_vppv_true_mixed_rollout_summary.csv) | true SurRoL/PyBullet mixed-fault rollout summary by task, fault combination, and controller |
| [failure_aware_vppv_true_mixed_rollout_paired.csv](../reports/tables/failure_aware_vppv_true_mixed_rollout_paired.csv) | paired clean, perturbed, and priority-routed mixed-fault results |
| [failure_aware_vppv_true_mixed_rollout_steps.csv](../reports/tables/failure_aware_vppv_true_mixed_rollout_steps.csv) | step-signal summary for priority-routed true mixed-fault episodes |
| [failure_aware_vppv_final_evidence_matrix.csv](../reports/tables/failure_aware_vppv_final_evidence_matrix.csv) | final VPPV claim-to-evidence matrix with reports, tables, figures, limitations, and rebuild commands |
| [failure_aware_vppv_final_key_numbers.csv](../reports/tables/failure_aware_vppv_final_key_numbers.csv) | compact key-number table used to generate the final teacher brief and readiness audit |

## Important Reports

| Report | Why It Matters |
|---|---|
| [RESEARCH_REPORT.md](RESEARCH_REPORT.md) | ECG-style structured research report: what was done, why, evidence, interpretation, limitations, and claims |
| [EXPERIMENT_EVIDENCE_SUMMARY.md](EXPERIMENT_EVIDENCE_SUMMARY.md) | compact evidence narrative for explaining the main upgrades quickly |
| [METHOD_OVERVIEW.md](METHOD_OVERVIEW.md) | mechanism diagram, evidence families, and routing policy |
| [LEARNING_TO_ROUTING_FLOW.md](LEARNING_TO_ROUTING_FLOW.md) | explains how baseline RL, weak risk labels, embedding/KNN analysis, risk-aware retraining, visual reliability, and runtime routing connect |
| [FAILURE_AWARE_VPPV_MULTIEVIDENCE_FRAMEWORK.md](FAILURE_AWARE_VPPV_MULTIEVIDENCE_FRAMEWORK.md) | reframes the project around VPPV visual-state, high-level approach-policy, handoff, and unsafe-continuation reliability |
| [failure_aware_vppv_supervisor_brief.md](../reports/failure_aware_vppv_supervisor_brief.md) | one-page VPPV pain-point, mechanism-routing, evidence, and limitation summary |
| [failure_aware_vppv_step_evidence.md](../reports/failure_aware_vppv_step_evidence.md) | step-level VPPV evidence, early warning, and mechanism evidence figure |
| [failure_aware_vppv_cross_task_generalization.md](../reports/failure_aware_vppv_cross_task_generalization.md) | cross-task frozen-threshold check for the VPPV mechanism router |
| [failure_aware_vppv_severity_holdout.md](../reports/failure_aware_vppv_severity_holdout.md) | low/medium-to-high severity holdout check for VPPV mechanism boundaries |
| [failure_aware_vppv_mixed_perturbation_priority.md](../reports/failure_aware_vppv_mixed_perturbation_priority.md) | offline mixed-perturbation priority audit for co-active evidence |
| [failure_aware_vppv_model_derived_routing.md](../reports/failure_aware_vppv_model_derived_routing.md) | rollout representation clustering and route assignment analysis |
| [failure_aware_vppv_true_mixed_rollouts.md](../reports/failure_aware_vppv_true_mixed_rollouts.md) | true SurRoL/PyBullet mixed-fault rollout report |
| [failure_aware_vppv_final_teacher_brief.md](../reports/failure_aware_vppv_final_teacher_brief.md) | final teacher-facing VPPV evidence ladder, strongest safe claim, and current limitations |
| [failure_aware_vppv_github_readiness_audit.md](../reports/failure_aware_vppv_github_readiness_audit.md) | public-repository readiness check for framing, evidence traceability, reproducibility, and claim calibration |
| [ECG_STYLE_RL_UPGRADE.md](ECG_STYLE_RL_UPGRADE.md) | explains the broad ECG-style analysis and model upgrade now added to the RL project |
| [FIGURE_ATLAS.md](FIGURE_ATLAS.md) | visual evidence inventory separating proxy snapshots from SurRoL renders |
| [surrol_master_results.md](../reports/surrol_master_results.md) | overview of paired SurRoL recovery evidence |
| [surrol_fault_taxonomy_step2.md](../reports/surrol_fault_taxonomy_step2.md) | formalizes failure families and intervention routes |
| [surrol_learned_route_classifier_step3.md](../reports/surrol_learned_route_classifier_step3.md) | shows learned route-classifier metrics and boundary errors |
| [surrol_observable_supervisor_step4.md](../reports/surrol_observable_supervisor_step4.md) | separates observable supervisor decisions from privileged simulator state |
| [risk_gated_tangent_report.md](../reports/risk_gated_tangent_report.md) | proxy controller-level result: always-on tangent correction becomes explainable risk-gated supervision |
| [embedding_risk_training_pilot.md](../reports/embedding_risk_training_pilot.md) | tests whether embedding/KNN instability analysis can be fed back into PPO training |

## Reproducibility Commands

Rebuild the main result summaries from stored CSV logs:

```powershell
python scripts\build_surrol_master_results.py
python scripts\build_surrol_fault_taxonomy.py
python scripts\train_surrol_route_classifier.py
python scripts\analyze_observable_proxy_risk.py
python scripts\build_surrol_observable_supervisor_step4.py
python scripts\build_risk_dataset.py
python scripts\train_explainable_risk.py
python scripts\offline_risk_gated_intervention.py
python scripts\evaluate_risk_gated_tangent.py --policy ppo --model runs\pilot_3d_50k_prototype_conditioned_seed0\model.zip --episodes 100 --seeds 0,1,2 --presets prototype,strict --threshold 0.5 --deterministic --risk-model-mode default_rule --out-dir outputs\risk_gated_tangent
python scripts\generate_risk_gated_visuals.py
python scripts\run_embedding_risk_training_pilot.py --timesteps 8192 --episodes 40 --penalty-scale 0.25 --risk-threshold 0.55 --curriculum-probability 0.35 --curriculum-candidates 8 --out-dir outputs\embedding_risk_curriculum_finetune_pilot
python scripts\build_failure_aware_vppv_composite_router.py
python scripts\build_failure_aware_vppv_step_evidence.py
python scripts\evaluate_failure_aware_vppv_cross_task.py
python scripts\evaluate_failure_aware_vppv_severity_holdout.py
python scripts\evaluate_failure_aware_vppv_mixed_priority.py
python scripts\build_failure_aware_vppv_model_derived_routing.py
.\scripts\run_surrol_true_mixed_faults.ps1 -Seeds 5 -Episodes 1 -MaxSteps 180
python scripts\build_failure_aware_vppv_true_mixed_rollout_report.py
python scripts\generate_failure_aware_vppv_supervisor_pack.py
python scripts\build_failure_aware_vppv_final_package.py
```

Run lightweight tests:

```powershell
$env:PYTHONPATH="$PWD\src"
python -m pytest tests\test_tool_navigation.py tests\test_surrol_ppo_reward_and_vision.py
```

## Claim Boundaries

The evidence supports a simulation research prototype for reliability
supervision. It does not support claims of clinical validation, real-robot
deployment, or a complete end-to-end learned surgical autonomy system. The
risk-gated tangent `prototype`/`strict` visuals support the custom proxy
controller result; the SurRoL evidence is the rendered `NeedleReach`,
`NeedlePick`, and `GauzeRetrieve` media and associated recovery tables.
