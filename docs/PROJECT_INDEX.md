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

The current controller-level result is risk-gated tangent backup: an
action-level supervisor that decides when the tangent backup controller should
be active. This result is in the custom proxy controller setting, not yet the
SurRoL policy wrapper. In the proxy PPO experiment, risk-gated tangent
preserves the 0.000 budget exhaustion of always tangent while reducing
supervisor activation from 1.000 to 0.450 on prototype and 0.426 on strict.

## Project Logic

| Stage | What It Shows | Evidence Type |
|---|---|---|
| Self-built proxy simulation | The core safety-control idea works in a simple constrained surgical-tool environment. | PPO/controller logs, prototype/strict trajectories, top-down snapshots |
| SurRoL migration | The same reliability-supervision idea is embedded into surgical simulation tasks. | Rendered NeedleReach, NeedlePick, and GauzeRetrieve GIF/MP4 rollouts |
| Four intervention routes | Failures are not treated as one generic failure; they are routed to continue, recover, review, or abort-candidate. | Fault taxonomy, paired recovery tables, route labels |
| Final reliability results | SurRoL recovery is stress-tested, and the proxy tangent controller is changed from always-on to risk-gated. | Multi-seed SurRoL results, learned route classifier, observable proxy audit, risk-gated tangent report |

## What To Read

| Time budget | File | Purpose |
|---|---|---|
| 2 minutes | [README](../README.md) | Main question, key numbers, setup, limitations |
| 5 minutes | [Project overview](project_overview.md) | Concise project narrative |
| 10 minutes | [Evidence index](evidence_index.md) | Claim-by-claim evidence map |
| 20 minutes | [Research sequence](research_sequence.md) | How the project developed from proxy RL to SurRoL supervision |
| 20 minutes | [Risk-gated tangent report](../reports/risk_gated_tangent_report.md) | Proxy controller-level result and proxy visual evidence |
| Deep dive | [SurRoL master report](../reports/surrol_master_results.md) | Main paired recovery tables |

## Evidence Snapshot

| Claim | Current evidence | Strength |
|---|---|---|
| The proxy backup controller is no longer just always-on. | Risk-gated tangent keeps 0.000 budget exhaustion while reducing supervisor activation to 0.450/0.426. | Strong for the proxy controller setting |
| The idea moved beyond a toy proxy. | Rendered SurRoL rollouts for NeedleReach, NeedlePick, and GauzeRetrieve with traces. | Strong for simulation migration |
| Failure routing helps under injected faults. | 10-seed NeedlePick/GauzeRetrieve recovery suites for action, perception, and jaw-stuck faults. | Strong within current SurRoL setup |
| Route prediction is learnable. | Held-out route classifier: 460 episodes, 84.6% accuracy, 82.8% macro-F1, 0.0 missed review-or-abort rate. | Moderate; labels are distilled |
| Privileged-state dependence is being reduced. | Observable jaw-stuck supervisor uses command/progress signals rather than direct phase/contact checks for the decision. | Promising, still partial |

## What Is Shown

- A working action-level reliability supervisor that gates tangent backup
  control by interpretable risk.
- A working reliability-supervision research pipeline for simulated surgical
  robot rollouts.
- Multi-seed evidence for recovery from several fault families.
- A clear taxonomy connecting failures to intervention routes.
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
