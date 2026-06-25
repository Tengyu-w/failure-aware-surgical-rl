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
| The process can be shown visually as trajectories and simulated snapshots. | [prototype snapshots](../reports/figures/risk_gated_tangent_visuals/render_snapshots_prototype.png), [strict trajectory](../reports/figures/risk_gated_tangent_visuals/trajectory_strict.png), [strict snapshots](../reports/figures/risk_gated_tangent_visuals/render_snapshots_strict.png) |

## Project Logic And Research Evidence

| Step | Purpose | Main Files |
|---|---|---|
| Stage 1 | Build a self-contained constrained proxy to test obstacle avoidance, tangent backup, and safety-budget supervision | [source environments](../src/constraint_surgical_rl/envs/), [custom proxy recovery report](../reports/cross_task_recovery_report.md) |
| Stage 2 | Migrate the reliability-supervision idea into SurRoL/PyBullet tasks | [SurRoL rendered evidence](../reports/media/surrol_render_evidence/) |
| Stage 3 | Formalize four runtime intervention routes: auto-execute, auto-recovery, human-review, abort-candidate | [taxonomy table](../reports/tables/surrol_fault_taxonomy.csv), [taxonomy report](../reports/surrol_fault_taxonomy_step2.md) |
| Stage 4 | Stress-test SurRoL recovery with multi-seed fault injections | [master paired results](../reports/tables/surrol_master_paired_results.csv), [master report](../reports/surrol_master_results.md) |
| Stage 5 | Add learned/observable reliability supervisors and risk-gated proxy backup control | [route classifier report](../reports/surrol_learned_route_classifier_step3.md), [observable supervisor report](../reports/surrol_observable_supervisor_step4.md), [risk-gated tangent report](../reports/risk_gated_tangent_report.md) |

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

## Important Reports

| Report | Why It Matters |
|---|---|
| [research_sequence.md](research_sequence.md) | recommended reading order for the whole project |
| [surrol_master_results.md](../reports/surrol_master_results.md) | overview of paired SurRoL recovery evidence |
| [surrol_fault_taxonomy_step2.md](../reports/surrol_fault_taxonomy_step2.md) | formalizes failure families and intervention routes |
| [surrol_learned_route_classifier_step3.md](../reports/surrol_learned_route_classifier_step3.md) | shows learned route-classifier metrics and boundary errors |
| [surrol_observable_supervisor_step4.md](../reports/surrol_observable_supervisor_step4.md) | separates observable supervisor decisions from privileged simulator state |
| [risk_gated_tangent_report.md](../reports/risk_gated_tangent_report.md) | proxy controller-level result: always-on tangent correction becomes explainable risk-gated supervision |

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
