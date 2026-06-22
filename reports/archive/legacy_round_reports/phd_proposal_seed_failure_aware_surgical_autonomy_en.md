# Proposal Seed: Failure-Aware Runtime Recovery for Surgical Embodied Intelligence

## Positioning

This project should not be framed as a replacement for a full surgical embodied intelligence system. A more realistic and stronger framing is:

> I am interested in extending surgical embodied intelligence from task execution to failure-aware autonomy. Current simulation-trained policies can perform nominal tasks, but abnormal execution remains under-characterized. My work explores whether runtime risk monitoring, failure diagnosis, and recovery triggering can provide a lightweight reliability layer for surgical robot learning systems.

## Relationship to Existing Surgical Autonomy Systems

| Existing system component | Reliability extension |
|---|---|
| Surgical simulator | Failure injection and abnormal execution benchmark |
| RL policy / task execution | Runtime reliability monitor |
| Visual servoing / control | Recovery trigger and intervention policy |
| Sim-to-real evaluation | Failure-aware robustness evaluation |
| Success rate | Success, recovery, false intervention, trigger delay |
| Task autonomy | Selective autonomy and human review |

The goal is not to claim a full system-level contribution yet. The goal is to identify a focused reliability gap and show that it can become a PhD-scale research direction.

## Current Evidence

I deployed a clean SurRoL environment and verified multiple task entry points, including `ECMReach`, `NeedleReach`, `NeedlePick`, `GauzeRetrieve`, `BiPegTransfer`, and `NeedleRegrasp`.

The main experiment currently focuses on SurRoL `NeedlePick`, because it has a useful failure-aware structure:

- clean oracle succeeds: 3/3;
- perturbed oracle under action noise fails: 0/3;
- perturbed oracle under action dropout fails: 0/3;
- perturbed oracle under execution slip fails: 0/3.

A simple runtime recovery layer using a coarse trigger and 32-step recovery window gives the following 5-seed pilot result with generic oracle override:

| Failure | Perturbed Success | Monitor-Corrected Success |
|---|---:|---:|
| action_noise | 0/5 | 5/5 |
| action_dropout | 0/5 | 1/5 |
| execution_slip | 0/5 | 3/5 |

This supports a prototype-level claim: a lightweight runtime recovery layer can recover some abnormal executions in SurRoL NeedlePick, but recovery effectiveness depends strongly on failure type.

After diagnosing failed seeds, I found that several dropout/slip failures consumed all waypoints without maintaining a valid grasp/contact constraint. Adding a phase-aware recovery policy, especially grasp-stage retry, improves the 5-seed result to:

| Failure | Perturbed Success | Phase-Aware Recovery Success |
|---|---:|---:|
| action_noise | 0/5 | 5/5 |
| action_dropout | 0/5 | 5/5 |
| execution_slip | 0/5 | 5/5 |

This suggests that failure-aware recovery should be task-phase and contact-state aware, rather than a generic action override.

## Research Gap

Simulation-trained surgical policies are often evaluated by nominal success rate. However, surgical autonomy also needs to answer:

- When is the policy becoming unreliable?
- What type of failure is happening?
- Should the system continue, recover, stop, or ask for human review?
- How can recovery be triggered without excessive unnecessary intervention?

This motivates a focused research direction:

> Failure-aware recovery for surgical embodied intelligence.

## Candidate PhD Research Questions

1. How should abnormal execution be defined and benchmarked in surgical robot learning tasks?
2. Which state, action, representation, or trajectory residual signals predict failure early?
3. Do different failure types require different recovery policies?
4. How can a system balance missed failure against false intervention?
5. When should surgical autonomy recover automatically, and when should it defer to human review?

## Proposed Roadmap

### Stage 1: Reliability Prototype in VLA / RL Benchmarks

Develop and evaluate runtime risk monitoring, failure-state retrieval, and demo-anchored recovery in controlled VLA/RL settings.

### Stage 2: Transfer to SurRoL Surgical Tasks

Extend the same reliability interface to SurRoL tasks such as NeedlePick, GauzeRetrieve, NeedleRegrasp, and PegTransfer. Build a failure taxonomy including action noise, execution slip, dropout, grasp miss, target drift, tool-object misalignment, stagnation, and unsafe contact.

### Stage 3: Surgical Runtime Recovery Benchmark

Report not only success rate, but also early failure detection, failure-type classification, recovery success, unnecessary intervention rate, trigger delay, intervention budget, human-review trigger accuracy, and robustness under task shift.

## Suggested Email Paragraph

I understand that my current work is still an early-stage prototype and much smaller in scope than a full surgical embodied intelligence system. However, I see it as a possible reliability layer rather than a replacement of the main policy or controller. My goal is to investigate whether failure-aware monitoring and recovery can complement simulation-trained surgical policies, especially in abnormal or distribution-shifted execution states. As an initial step, I deployed SurRoL and tested NeedlePick under action noise, dropout, and execution slip. The clean oracle succeeds, while perturbed execution fails; a simple runtime recovery layer can recover action-noise failures and partially recover slip/dropout failures, exposing a concrete trade-off between recovery success and unnecessary intervention.

## Limitations

The current evidence remains preliminary. It uses 3 seeds, one main SurRoL task, rule-based triggers, and oracle override rather than a learned recovery policy. These limitations should be stated explicitly; they also define the next research steps.
