# Project Index

This page is the public entry point for the repository. It gives a concise map
of the research question, evidence, and report structure before a reader opens
the longer reports.

## Summary

This repository studies runtime reliability supervision for surgical robot
learning in simulation. The project begins with a custom constrained 3D
surgical-tool proxy for obstacle avoidance, tangent backup control, and safety
budget testing. The same reliability-routing idea is then migrated into
SurRoL/PyBullet manipulation tasks. The supervisor decides whether execution
should continue, recover automatically, request human-style review or
re-estimation, or stop because recovery may be unsafe.

The first controller-level result is risk-gated tangent backup: an action-level
supervisor that decides when the tangent backup controller should be active.
The ECG-inspired upgrade is mechanism-routed tangent backup, which separates
boundary safety risks from residual mechanism risks instead of collapsing every
signal into one total risk score. In the proxy PPO experiment, the
mechanism-routed supervisor preserves the 0.000 budget exhaustion of
risk-gated tangent while reducing supervisor activation from 0.450 to 0.443 on
prototype and from 0.426 to 0.416 on strict.

## Project Logic

| Stage | What It Shows | Evidence Type |
|---|---|---|
| Teacher-facing experiment process | The project is explained as a progression from proxy RL to ECG-style mechanism analysis to VPPV reliability routing. | Supervisor-facing narrative document |
| Self-built proxy simulation | The core safety-control idea works in a simple constrained surgical-tool environment. | PPO/controller logs, prototype/strict trajectories, top-down snapshots |
| CircleRL recovery media | A biased target estimate can visibly drive the proxy tool off route, then monitor recovery re-estimates the target and returns toward completion. | MP4/GIF recovery demo, selected frames, trace CSV |
| SurRoL migration | The same reliability-supervision idea is embedded into surgical simulation tasks. | Rendered NeedleReach, NeedlePick, and GauzeRetrieve GIF/MP4 rollouts |
| Task-specific SurRoL upgrade framework | The proxy idea is expanded into NeedleReach, NeedlePick, GauzeRetrieve, PickAndPlace, and unsafe-zone near-target settings. | Task-failure-route matrix and machine-readable CSV |
| ECG-style SurRoL mechanism routing | The reliable-ECG method is adapted into SurRoL failure families, evidence signals, and v5d-style boundary/residual routing. | Mechanism-routing blueprint and machine-readable map |
| Failure-aware VPPV reframing | The project is reframed around VPPV visual-state estimation, high-level approach policy, final servoing handoff, and unsafe continuation. | Multi-evidence framework, composite router report, route-summary CSV |
| VPPV supervisor brief | The VPPV pain point, mechanism-specific routes, evidence, and scope boundary are condensed for a quick teacher read. | One-page brief and supervisor-pack figure |
| Step-level VPPV evidence | The VPPV reframing is tested on per-step SurRoL traces for nominal, visual bias, depth-scale error, and policy approach drift. | Step dataset, single-evidence ablation, early-warning table, mechanism evidence figure |
| Cross-task VPPV check | The step router is calibrated on one SurRoL task and tested with frozen thresholds on another. | Cross-task generalization report, threshold sweep, confusion table |
| Severity-held-out VPPV check | Low/medium severity conditions define intervention boundaries, then high severity is held out. | Severity holdout report, boundary table, held-out route figure |
| Mixed-priority VPPV audit | Existing single-mechanism traces are composed to test co-active visual/depth/policy evidence. | Mixed-priority report, scenario table, evidence figure |
| Behavior-derived VPPV routing | Rollout behavior is embedded, clustered, fingerprinted, and converted into route assignments. | Behavior-derived routing report, cluster table, PCA figure |
| True mixed-fault VPPV rollouts | Mixed visual/depth/near-target fault proxies are executed inside SurRoL/PyBullet. | True mixed rollout report, paired table, success/distance figures |
| Final VPPV evidence package | The VPPV evidence ladder is condensed into a teacher brief, machine-readable matrix, and readiness audit. | Final teacher brief, final evidence matrix, GitHub readiness audit |
| Four intervention routes | Failures are not treated as one generic failure; they are routed to continue, recover, review, or abort-candidate. | Fault taxonomy, paired recovery tables, route labels |
| Final reliability results | SurRoL recovery is stress-tested, and the proxy tangent controller is changed from always-on to risk-gated, then to ECG-style mechanism-routed supervision. | Multi-seed SurRoL results, learned route classifier, observable proxy audit, risk-gated tangent report, mechanism-routed tangent report |

## What To Read

| Time budget | File | Purpose |
|---|---|---|
| 2 minutes | [README](../README.md) | Main question, key numbers, setup, limitations |
| 8 minutes | [Teacher-facing experiment process](TEACHER_EXPERIMENT_PROCESS.md) | Best first deep read: why this is VPPV reliability routing, not a collection of gripper-action fixes |
| 10 minutes | [Research report](RESEARCH_REPORT.md) | ECG-style structured explanation of what was done, why, evidence, and limits |
| 10 minutes | [Experiment evidence summary](EXPERIMENT_EVIDENCE_SUMMARY.md) | Compact result narrative for a quick supervisor read |
| 15 minutes | [Learning-to-routing flow](LEARNING_TO_ROUTING_FLOW.md) | How PPO training, weak labels, embedding/KNN, visual risk, failed retraining, and runtime routing connect |
| 15 minutes | [SurRoL task upgrade framework](SURROL_TASK_UPGRADE_FRAMEWORK.md) | Task-level framework beyond CircleRL: NeedleReach, NeedlePick, GauzeRetrieve, PickAndPlace, unsafe-zone recovery |
| 15 minutes | [SurRoL ECG-style mechanism routing](SURROL_ECG_STYLE_MECHANISM_ROUTING.md) | How ECG-style boundary/residual mechanism routing becomes SurRoL failure diagnosis and intervention routing |
| 15 minutes | [Failure-aware VPPV framework](FAILURE_AWARE_VPPV_MULTIEVIDENCE_FRAMEWORK.md) | Why the project targets VPPV visual-state, approach-policy, handoff, and unsafe-continuation reliability rather than gripper mechanics |
| 5 minutes | [Failure-aware VPPV supervisor brief](../reports/failure_aware_vppv_supervisor_brief.md) | One-page explanation plus the VPPV supervisor-pack figure |
| 15 minutes | [Failure-aware VPPV step evidence](../reports/failure_aware_vppv_step_evidence.md) | Step-level evidence, early warning, and single-family versus composite route comparison |
| 15 minutes | [Failure-aware VPPV cross-task generalization](../reports/failure_aware_vppv_cross_task_generalization.md) | Frozen-threshold transfer between NeedlePick and GauzeRetrieve |
| 15 minutes | [Failure-aware VPPV severity holdout](../reports/failure_aware_vppv_severity_holdout.md) | Low/medium intervention-boundary calibration tested on held-out high severity |
| 15 minutes | [Failure-aware VPPV mixed-priority audit](../reports/failure_aware_vppv_mixed_perturbation_priority.md) | Co-active evidence priority test: depth before visual before policy correction |
| 15 minutes | [Failure-aware VPPV behavior-derived routing](../reports/failure_aware_vppv_model_derived_routing.md) | Route assignment derived from rollout behavior regions rather than direct mechanism labels |
| 15 minutes | [Failure-aware VPPV true mixed rollouts](../reports/failure_aware_vppv_true_mixed_rollouts.md) | Actual SurRoL/PyBullet mixed-fault rollouts with perturbed and priority-routed controllers |
| 5 minutes | [Failure-aware VPPV final teacher brief](../reports/failure_aware_vppv_final_teacher_brief.md) | Final evidence ladder, strongest safe claim, and current limitations |
| 10 minutes | [Failure-aware VPPV final evidence matrix](../reports/tables/failure_aware_vppv_final_evidence_matrix.csv) | Machine-readable claim, metric, report, table, figure, and rebuild-command map |
| 15 minutes | [ECG-style RL upgrade](ECG_STYLE_RL_UPGRADE.md) | Broad ECG-style diagnostics and model upgrade beyond embedding alone |
| 15 minutes | [Method overview](METHOD_OVERVIEW.md) | Reliability signal families, routing logic, and scope boundary |
| Visual | [Figure atlas](FIGURE_ATLAS.md) | Visual evidence inventory across proxy and SurRoL stages |
| 10 minutes | [Evidence index](evidence_index.md) | Claim-by-claim evidence map |
| 20 minutes | [Risk-gated tangent report](../reports/risk_gated_tangent_report.md) | Proxy controller-level result and proxy visual evidence |
| 20 minutes | [Mechanism-routed tangent report](../reports/mechanism_routed_tangent_v5d_report.md) | ECG-inspired v5d-style reliability-routing upgrade |
| Deep dive | [SurRoL master report](../reports/surrol_master_results.md) | Main paired recovery tables |

## Evidence Snapshot

| Claim | Current evidence | Strength |
|---|---|---|
| The proxy backup controller is no longer just always-on. | Risk-gated tangent keeps 0.000 budget exhaustion while reducing supervisor activation to 0.450/0.426. | Strong for the proxy controller setting |
| The proxy supervisor now has mechanism-separated routing. | Mechanism-routed tangent keeps 0.000 budget exhaustion while reducing activation to 0.443/0.416 and logging Stage 1 boundary versus Stage 2 residual routes. | Moderate-to-strong for the proxy controller setting |
| The idea moved beyond a toy proxy. | Rendered SurRoL rollouts for NeedleReach, NeedlePick, and GauzeRetrieve with traces. | Strong for simulation migration |
| The proxy recovery mechanism is visible. | CircleRL MP4/GIF shows biased-target drift followed by monitor recovery and successful completion. | Strong as a proxy visualization; not SurRoL |
| The next tasks are structured, not ad hoc. | SurRoL task upgrade framework maps NeedleReach, NeedlePick, GauzeRetrieve, PickAndPlace, and unsafe-zone recovery to failures, signals, routes, and limitations. | Strong as framework; evidence maturity differs by task |
| Failure routing helps under injected faults. | 10-seed NeedlePick/GauzeRetrieve recovery suites for action, perception, and jaw-stuck faults. | Strong within current SurRoL setup |
| Route prediction is learnable. | Held-out route classifier: 460 episodes, 84.6% accuracy, 82.8% macro-F1, 0.0 missed review-or-abort rate. | Moderate; labels are distilled |
| Embedding/KNN can be connected to training but does not solve policy robustness. | Multi-seed embedding-risk PPO improves return/distance in some settings but not robust success or budget exhaustion. | Preliminary; useful as a negative result |
| ECG-style broad reliability analysis is now present. | Representation quality, centroid/prototype/KNN diagnostics, uncertainty scores, injected-failure robustness, and multi-signal risk-head/router tables. | Stronger internal research evidence; still simulator-only |
| VPPV-specific composite routing is now explicit. | Composite router over 370 weak-labeled SurRoL episodes reaches 0.732 weak-label accuracy and 0.713 macro-F1 while separating visual, depth, policy, handoff, and unsafe routes. | Prototype-level; labels are simulator-derived |
| Step-level evidence is now present. | 10,823 VPPV-style step rows cover nominal, visual-estimation bias, depth-scale error, and policy-approach drift; composite route consistency reaches 0.999 against weak mechanism rules with 0.005 nominal false-alert rate. | Strong as weak-label consistency evidence; not an independent expert-label benchmark |
| Step-level VPPV routing transfers across two SurRoL tasks. | Thresholds calibrated on NeedlePick reach 1.000 macro-F1 on GauzeRetrieve; thresholds calibrated on GauzeRetrieve reach 0.996 macro-F1 on NeedlePick. | Stronger than within-task consistency; still simulator-derived weak-label evidence |
| Mechanism boundaries survive held-out high severity. | Boundary router trained on low/medium severity reaches 1.000 macro-F1 on 6 high-severity task/failure conditions, while uniform retry is 0.167. | Lightweight 30-seed aggregate check; not a full external validation |
| Mixed evidence needs priority routing. | In an offline compositional mixed-perturbation audit, the priority router reaches 1.000 macro-F1, while max-signal routing reaches 0.033 and uniform retry reaches 0.000. | Priority audit over composed evidence; larger learned-policy mixed rollouts remain future work |
| Routes can be derived from model behavior regions. | PCA/cluster route assignment on held-out episodes reaches 0.995 macro-F1, 0.000 missed high-risk rate, and 0.025 nominal false alarm. | Simulator rollout behavior and weak labels; not real-world discovery |
| True mixed faults have been smoke-tested in SurRoL. | Across 2 tasks, 4 mixed fault combinations, and 5 seeds, perturbed mixed faults are 0/40 success while priority-routed mixed faults are 40/40 success. | Smoke-scale scripted-oracle simulation; not learned-policy or hardware validation |
| The final VPPV story is now packaged. | The final teacher brief and evidence matrix link each major VPPV claim to its metric, report, table, figure, and rebuild command. | Strong as a GitHub/research-package organization step; it does not add new experimental validation |
| Privileged-state dependence is being reduced. | Observable jaw-stuck supervisor uses command/progress signals rather than direct phase/contact checks for the decision. | Promising, still partial |

## What Is Shown

- A working action-level reliability supervisor that gates tangent backup
  control by interpretable risk, now upgraded into a two-stage
  mechanism-routed supervisor.
- A working reliability-supervision research pipeline for simulated surgical
  robot rollouts.
- Multi-seed evidence for recovery from several fault families.
- A clear taxonomy connecting failures to intervention routes.
- A complete learning-to-routing chain: baseline PPO, weak risk labels,
  embedding/KNN analysis, risk-aware retraining attempt, visual risk modules,
  and runtime route supervision.
- A broad ECG-style reliability suite: representation geometry, uncertainty,
  trajectory structure, perturbation robustness, multi-signal model training,
  and mechanism routing.
- Visual media, CSV traces, tables, unit tests, and reproducibility scripts.
- Conservative scope language that separates simulation evidence from clinical
  or real-robot claims.

## What Remains Unproven

- Real-robot or clinical validation.
- End-to-end learned surgical autonomy.
- Independent expert labels for review/abort decisions.
- Task-agnostic learned recovery primitives.
- Formal safety guarantees.

## Research Positioning

| Direction | How to position the project |
|---|---|
| Surgical robotics | Runtime supervision for tool navigation, contact uncertainty, and unsafe recovery. |
| Surgical embodied AI | Failure-aware autonomy and selective human review around learned policies. |
| Medical robotics reliability | Simulation evidence for deciding when autonomous recovery is trustworthy. |
| Safe robot learning | Backup-controller selection, route prediction, and recovery-risk boundaries. |
| Runtime assurance | Transparent states: continue, recover, review, abort candidate. |
