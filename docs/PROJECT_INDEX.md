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
| Self-built proxy simulation | The core safety-control idea works in a simple constrained surgical-tool environment. | PPO/controller logs, prototype/strict trajectories, top-down snapshots |
| SurRoL migration | The same reliability-supervision idea is embedded into surgical simulation tasks. | Rendered NeedleReach, NeedlePick, and GauzeRetrieve GIF/MP4 rollouts |
| Four intervention routes | Failures are not treated as one generic failure; they are routed to continue, recover, review, or abort-candidate. | Fault taxonomy, paired recovery tables, route labels |
| Final reliability results | SurRoL recovery is stress-tested, and the proxy tangent controller is changed from always-on to risk-gated, then to ECG-style mechanism-routed supervision. | Multi-seed SurRoL results, learned route classifier, observable proxy audit, risk-gated tangent report, mechanism-routed tangent report |

## What To Read

| Time budget | File | Purpose |
|---|---|---|
| 2 minutes | [README](../README.md) | Main question, key numbers, setup, limitations |
| 5 minutes | [Project overview](project_overview.md) | Concise project narrative |
| 10 minutes | [Research report](RESEARCH_REPORT.md) | ECG-style structured explanation of what was done, why, evidence, and limits |
| 10 minutes | [Experiment evidence summary](EXPERIMENT_EVIDENCE_SUMMARY.md) | Compact result narrative for a quick supervisor read |
| 15 minutes | [Learning-to-routing flow](LEARNING_TO_ROUTING_FLOW.md) | How PPO training, weak labels, embedding/KNN, visual risk, failed retraining, and runtime routing connect |
| 15 minutes | [ECG-style RL upgrade](ECG_STYLE_RL_UPGRADE.md) | Broad ECG-style diagnostics and model upgrade beyond embedding alone |
| 15 minutes | [Method overview](METHOD_OVERVIEW.md) | Reliability signal families, routing logic, and scope boundary |
| Visual | [Figure atlas](FIGURE_ATLAS.md) | Visual evidence inventory across proxy and SurRoL stages |
| 10 minutes | [Evidence index](evidence_index.md) | Claim-by-claim evidence map |
| 20 minutes | [Research sequence](research_sequence.md) | How the project developed from proxy RL to SurRoL supervision |
| 20 minutes | [Risk-gated tangent report](../reports/risk_gated_tangent_report.md) | Proxy controller-level result and proxy visual evidence |
| 20 minutes | [Mechanism-routed tangent report](../reports/mechanism_routed_tangent_v5d_report.md) | ECG-inspired v5d-style reliability-routing upgrade |
| Deep dive | [SurRoL master report](../reports/surrol_master_results.md) | Main paired recovery tables |

## Evidence Snapshot

| Claim | Current evidence | Strength |
|---|---|---|
| The proxy backup controller is no longer just always-on. | Risk-gated tangent keeps 0.000 budget exhaustion while reducing supervisor activation to 0.450/0.426. | Strong for the proxy controller setting |
| The proxy supervisor now has mechanism-separated routing. | Mechanism-routed tangent keeps 0.000 budget exhaustion while reducing activation to 0.443/0.416 and logging Stage 1 boundary versus Stage 2 residual routes. | Moderate-to-strong for the proxy controller setting |
| The idea moved beyond a toy proxy. | Rendered SurRoL rollouts for NeedleReach, NeedlePick, and GauzeRetrieve with traces. | Strong for simulation migration |
| Failure routing helps under injected faults. | 10-seed NeedlePick/GauzeRetrieve recovery suites for action, perception, and jaw-stuck faults. | Strong within current SurRoL setup |
| Route prediction is learnable. | Held-out route classifier: 460 episodes, 84.6% accuracy, 82.8% macro-F1, 0.0 missed review-or-abort rate. | Moderate; labels are distilled |
| Embedding/KNN can be connected to training but does not solve policy robustness. | Multi-seed embedding-risk PPO improves return/distance in some settings but not robust success or budget exhaustion. | Preliminary; useful as a negative result |
| ECG-style broad reliability analysis is now present. | Representation quality, centroid/prototype/KNN diagnostics, uncertainty scores, injected-failure robustness, and multi-signal risk-head/router tables. | Stronger internal research evidence; still simulator-only |
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
