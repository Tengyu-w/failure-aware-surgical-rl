# Research Sequence

This page is the recommended reading order for the repository. It is designed
for a supervisor or reviewer who wants the research logic without browsing all
intermediate experiment notes.

## 1. Custom Constrained Surgical Proxy

The project began with a custom 3D surgical-tool proxy environment. This stage
was used to develop the core idea: a controller should be supervised not only by
task reward, but also by safety budgets, recovery triggers, and failure-aware
routing.

Main files:

- [source environments](../src/constraint_surgical_rl/envs/)
- [custom proxy recovery report](../reports/cross_task_recovery_report.md)
- [project brief](../reports/project_brief.md)

## 2. Migration To SurRoL

The reliability-supervision idea was then migrated into SurRoL/PyBullet
surgical simulation tasks. This is the bridge from the original proxy to a
recognized surgical robotics simulator.

Main evidence:

- [NeedleReach GIF](../reports/media/surrol_render_evidence/needlereach/needlereach_oracle_rollout.gif)
- [NeedlePick GIF](../reports/media/surrol_render_evidence/needlepick/needlepick_oracle_rollout.gif)
- [GauzeRetrieve GIF](../reports/media/surrol_render_evidence/gauzeretrieve/gauzeretrieve_oracle_rollout.gif)
- [SurRoL deployment notes](../reports/surrol_wsl_deployment_notes_zh.md)

## 3. Fault Taxonomy And Intervention Routes

After the migration, the project formalized failures into a reliability
taxonomy instead of treating them as isolated demos.

Fault families:

- nominal execution;
- reversible execution drift;
- grasp/contact uncertainty;
- visual-state error;
- near-target recovery risk.

Intervention routes:

- `auto_execute`;
- `auto_recovery`;
- `human_review`;
- `abort_candidate`.

Main files:

- [fault taxonomy report](../reports/surrol_fault_taxonomy_step2.md)
- [fault taxonomy table](../reports/tables/surrol_fault_taxonomy.csv)

## 4. Multi-Seed SurRoL Recovery Experiments

The project then upgraded the key experiments to 10-seed evidence on
`NeedlePick` and `GauzeRetrieve`.

Main result:

- standard action corruptions recover from 0/10 perturbed success to 9/10 or
  10/10 recovered success;
- visual-state errors recover from 0/10 to 10/10 via review/re-estimation;
- jaw-stuck grasp failures recover from 0/10 to 10/10 using observable proxy
  recovery on both core tasks.

Main files:

- [master results report](../reports/surrol_master_results_round13_zh.md)
- [paired results table](../reports/tables/surrol_master_paired_results.csv)
- [episode rows](../reports/tables/surrol_master_episode_rows.csv)

## 5. Learned Route Classifier

The next step moved beyond hand-written routing by training a safety-biased
episode-level route classifier.

Held-out odd-seed result:

| Metric | Value |
|---|---:|
| accuracy | 0.846 |
| macro-F1 | 0.828 |
| missed review-or-abort rate | 0.000 |
| false review-or-abort rate | 0.162 |

Main files:

- [learned route classifier report](../reports/surrol_learned_route_classifier_step3.md)
- [metrics table](../reports/tables/surrol_learned_route_classifier_metrics.csv)
- [confusion table](../reports/tables/surrol_learned_route_classifier_confusion.csv)

## 6. Observable Supervisor

The final upgrade reduced the supervisor decision's dependence on privileged
SurRoL phase/contact state for jaw-stuck recovery. The recovery trigger uses
observable command/progress proxies:

- jaw close command count;
- goal-distance stagnation;
- minimum-distance improvement;
- observable risk score.

Main files:

- [observable supervisor report](../reports/surrol_observable_supervisor_step4.md)
- [observable signal audit](../reports/tables/surrol_observable_signal_audit.csv)
- [observable versus privileged comparison](../reports/tables/surrol_observable_vs_privileged_jaw_stuck.csv)
- [threshold sweep figure](../reports/figures/observable_proxy_risk/observable_proxy_threshold_sweep.png)

## 7. Limitations And Next Steps

The project is deliberately framed as a simulation research prototype.

Confirmed:

- the reliability-supervision idea was migrated from a custom proxy into
  SurRoL;
- the key SurRoL recovery results have multi-seed evidence;
- learned routing and observable-proxy supervision have working prototypes.

Not yet claimed:

- clinical validation;
- real-robot deployment;
- complete end-to-end learned surgical autonomy;
- parity with or improvement over the full SurRoL platform.

Main file:

- [claims and limitations](../reports/claims_limitations_round46.md)

## Archive

All intermediate round notes are preserved under:

- [legacy round reports](../reports/archive/legacy_round_reports/)

They are kept for provenance, but they are not the recommended first reading
path.
