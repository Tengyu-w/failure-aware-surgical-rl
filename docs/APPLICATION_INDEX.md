# Application Index

This page is the supervisor-facing entry point. It is meant to help a PhD
reviewer understand the project in five minutes before deciding whether to read
the longer reports.

##  Summary

This repository studies runtime reliability supervision for surgical robot
learning in simulation. The project begins with a custom constrained 3D
surgical-tool proxy and then migrates the same reliability-routing idea into
SurRoL/PyBullet manipulation tasks. The supervisor decides whether execution
should continue, recover automatically, request human-style review or
re-estimation, or stop because recovery may be unsafe.

The newest upgrade is risk-gated tangent backup: an action-level supervisor
that decides when the tangent backup controller should be active. In the proxy
PPO experiment, risk-gated tangent preserves the 0.000 budget exhaustion of
always tangent while reducing supervisor activation from 1.000 to 0.450 on
prototype and 0.426 on strict.

## Best Application Framing

Use this project when writing to supervisors in medical robotics, surgical
embodied AI, robot learning safety, runtime assurance, or image-guided robotic
systems.

Suggested wording:

> I built a simulation-based reliability-supervision prototype for surgical
> robot learning. It evaluates failure-aware routing across execution drift,
> grasp/contact uncertainty, visual-state errors, and unsafe recovery proxies,
> with a controller-level risk-gated tangent supervisor, multi-seed SurRoL
> evidence, and explicit limitations.

## What To Read

| Time budget | File | Purpose |
|---|---|---|
| 2 minutes | [README](../README.md) | Main question, key numbers, setup, limitations |
| 5 minutes | [PhD application brief](phd_application_project_brief.md) | Concise supervisor-facing project narrative |
| 10 minutes | [Evidence index](evidence_index.md) | Claim-by-claim evidence map |
| 20 minutes | [Research sequence](research_sequence.md) | How the project developed from proxy RL to SurRoL supervision |
| 20 minutes | [Risk-gated tangent report](../reports/risk_gated_tangent_report.md) | Main controller-level upgrade and visual evidence |
| Deep dive | [SurRoL master report](../reports/surrol_master_results_round13_zh.md) | Main paired recovery tables |

## Evidence Snapshot

| Claim | Current evidence | Strength |
|---|---|---|
| The backup controller is no longer just always-on. | Risk-gated tangent keeps 0.000 budget exhaustion while reducing supervisor activation to 0.450/0.426. | Strong for the proxy controller setting |
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

## Best-Fit Supervisor Directions

| Direction | How to position the project |
|---|---|
| Surgical robotics | Runtime supervision for tool navigation, contact uncertainty, and unsafe recovery. |
| Surgical embodied AI | Failure-aware autonomy and selective human review around learned policies. |
| Medical robotics reliability | Simulation evidence for deciding when autonomous recovery is trustworthy. |
| Safe robot learning | Backup-controller selection, route prediction, and recovery-risk boundaries. |
| Runtime assurance | Transparent states: continue, recover, review, abort candidate. |

## Next Upgrade Before Submission

1. Transfer the risk-gated tangent supervisor from the custom proxy into a
   SurRoL-style policy wrapper.
2. Convert the learned route classifier from episode-level to window-level or
   step-level supervision.
3. Add an externally labelled or manually audited review/abort subset.
4. Replace more scripted recovery primitives with learned or task-agnostic
   recovery actions.
5. Add calibration and coverage-risk curves for learned route decisions.
