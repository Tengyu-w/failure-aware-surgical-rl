# Documentation Guide

This folder contains the supervisor-facing documentation for the project. The
repository is intentionally organized as a research portfolio, not as a raw
experiment dump.

## Recommended Reading Order

| Time | File | Purpose |
| --- | --- | --- |
| 2 min | [Project README](../README.md) | Main contribution, result snapshot, and limitations. |
| 5 min | [Project index](PROJECT_INDEX.md) | Public entry point and evidence snapshot. |
| 10 min | [Experiment evidence summary](EXPERIMENT_EVIDENCE_SUMMARY.md) | Compact story of what was tested, why, what worked, and what failed. |
| 15 min | [Evidence index](evidence_index.md) | Claim-by-claim pointers to figures, tables, and reports. |
| 15 min | [Learning-to-routing flow](LEARNING_TO_ROUTING_FLOW.md) | How RL training, weak labels, embedding/KNN analysis, failed retraining, visual risk, and runtime routing connect. |
| 15 min | [SurRoL task upgrade framework](SURROL_TASK_UPGRADE_FRAMEWORK.md) | How NeedleReach, NeedlePick, GauzeRetrieve, PickAndPlace, and unsafe-zone recovery extend the CircleRL proxy. |
| 15 min | [ECG-style RL upgrade](ECG_STYLE_RL_UPGRADE.md) | Broad reliability analysis and model upgrade mapped from the ECG project. |
| 20 min | [Method overview](METHOD_OVERVIEW.md) | Method diagram and reliability signal families. |
| 30 min | [Research report](RESEARCH_REPORT.md) | Detailed stage-ordered final report. |
| Visual | [Figure atlas](FIGURE_ATLAS.md) | Public visual evidence inventory. |

## Core Documents

- [RESEARCH_REPORT.md](RESEARCH_REPORT.md): full stage-ordered final report.
- [EXPERIMENT_EVIDENCE_SUMMARY.md](EXPERIMENT_EVIDENCE_SUMMARY.md): compact
  explanation for a supervisor.
- [METHOD_OVERVIEW.md](METHOD_OVERVIEW.md): method diagram and route logic.
- [LEARNING_TO_ROUTING_FLOW.md](LEARNING_TO_ROUTING_FLOW.md): full
  learning-to-routing explanation.
- [SURROL_TASK_UPGRADE_FRAMEWORK.md](SURROL_TASK_UPGRADE_FRAMEWORK.md):
  task-level upgrade framework beyond the CircleRL proxy.
- [ECG_STYLE_RL_UPGRADE.md](ECG_STYLE_RL_UPGRADE.md): broad ECG-style
  reliability analysis and model-upgrade summary.
- [FIGURE_ATLAS.md](FIGURE_ATLAS.md): visual evidence inventory.
- [evidence_index.md](evidence_index.md): claim-to-evidence map.
- [PROJECT_INDEX.md](PROJECT_INDEX.md): short public entry point.

## Scope Boundary

This repository does not claim real-robot or clinical validation. It is a
simulation research prototype for runtime reliability supervision in surgical
robot learning.
