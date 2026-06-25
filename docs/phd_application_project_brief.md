# PhD Application Project Brief

## Title

Failure-Aware Reliability Supervision for Surgical Robot Learning

## One-Paragraph Summary

This project studies runtime reliability supervision for surgical robot learning
in simulation. It began as a custom constrained 3D surgical-tool proxy and was
then migrated into SurRoL/PyBullet surgical manipulation tasks. The core idea is
to place a reliability supervisor around an existing controller and decide when
the system should continue autonomously, recover automatically, request
human-style review/re-estimation, or stop because recovery may be unsafe. The
current evidence covers a risk-gated tangent backup supervisor, SurRoL rendered
rollouts, multi-seed failure injection, fault taxonomy, learned route
classification, and an observable-proxy supervisor that reduces reliance on
privileged simulator phase/contact state.

## Research Motivation

Surgical autonomy is safety-adjacent: a controller should not only optimize task
success, but also know when its execution is unreliable. Standard success-rate
reporting hides important distinctions between reversible execution drift,
visual-state errors, grasp/contact uncertainty, and unsafe recovery attempts.
This project frames those distinctions as a reliability-routing problem.

## Method Overview

The project has four technical layers:

1. A custom constrained 3D proxy environment for fast RL and safety-budget
   experiments.
2. An action-level risk-gated tangent backup supervisor that decides when the
   safety controller should be activated.
3. SurRoL task migration using `NeedleReach`, `NeedlePick`, and
   `GauzeRetrieve` rollouts.
4. Runtime failure taxonomy and route decisions:
   `auto_execute`, `auto_recovery`, `human_review`, and `abort_candidate`.
5. Learned and observable reliability supervisors built from rollout features,
   step traces, command history, and progress signals.

## Key Evidence

| Component | Evidence |
|---|---|
| Risk-gated tangent backup | prototype/strict both preserve 0.000 budget exhaustion while reducing supervisor activation from 1.000 to 0.450/0.426 |
| SurRoL migration | rendered RGB GIF/MP4 rollouts for NeedleReach, NeedlePick, and GauzeRetrieve |
| Standard corruptions | 10-seed NeedlePick/GauzeRetrieve action noise, dropout, and execution slip |
| Visual-state errors | 10-seed perception-bias and depth-scale error recovery via review/re-estimation |
| Grasp/contact uncertainty | 10-seed jaw-stuck observable proxy recovery on NeedlePick and GauzeRetrieve |
| Learned risk routing | 84.6% accuracy, 82.8% macro-F1, and 0.0 missed review-or-abort rate on held-out odd seeds |
| Observable supervision | jaw-stuck recovery decision uses command/progress proxies instead of internal phase/contact state |

## Strongest Current Result

At the controller level, the risk-gated tangent upgrade keeps the strongest
safety property of the always-on tangent shield while using much less
supervision:

- prototype: budget exhaustion 0.000, supervisor activation 0.450;
- strict: budget exhaustion 0.000, supervisor activation 0.426;
- always tangent baseline: budget exhaustion 0.000, supervisor activation 1.000.

This reframes the project from "I have a shield" to "reliability analysis
becomes a runtime decision signal."

In the strongest 10-seed SurRoL suites:

- standard action corruptions recover from 0/10 perturbed success to 9/10 or
  10/10 recovered success;
- visual-state errors recover from 0/10 perturbed success to 10/10 via
  review/re-estimation;
- jaw-stuck grasp failures recover from 0/10 perturbed success to 10/10 with an
  observable proxy recovery decision on both NeedlePick and GauzeRetrieve.

## Relationship To SurRoL

This project does not claim to improve or replace the SurRoL platform. SurRoL is
used as the surgical simulation environment for evaluating a reliability
supervision idea developed from the custom proxy environment. The research
contribution is the failure-aware supervisor, taxonomy, routing evaluation, and
evidence structure around SurRoL rollouts.

## Limitations

- Simulation-only evidence.
- Recovery primitives still use scripted SurRoL waypoint generation in several
  experiments.
- The learned route classifier is episode-level, not a deployable online
  monitor.
- Labels are distilled from current rule/proxy routing rather than independent
  expert labels.
- `abort_candidate` is low-support and uses a geometric danger-zone proxy.

## Suitable Application Framing

> I developed a simulation-based reliability-supervision prototype for surgical
> robot learning. Starting from a custom constrained 3D proxy, I migrated the
> supervisor into SurRoL tasks and upgraded the proxy controller with a
> risk-gated tangent backup layer. The supervisor decides when action-level
> backup control is necessary and evaluates failure-aware routing across
> execution drift, grasp/contact uncertainty, visual-state errors, and unsafe
> recovery proxies. The project emphasizes multi-seed evidence, explicit
> limitations, and a move from post-hoc reliability analysis toward runtime
> decision signals.

## What I Would Improve Next

1. Convert the risk-gated tangent score into a learned online monitor evaluated
   across additional policies and tasks.
2. Convert the episode-level learned route classifier into a window-level online
   classifier.
3. Add independent labels or stronger evaluation targets for review/abort
   decisions.
4. Replace scripted recovery primitives with learned or task-agnostic recovery
   actions.
5. Evaluate on additional SurRoL tasks and more diverse visual corruptions.
