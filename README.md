# Failure-Aware Reliability Supervision for Surgical RL

This repository is a research prototype for reliability-supervised surgical
robot learning. It starts from a custom constrained 3D surgical-tool proxy and
migrates the same failure-aware supervision idea into SurRoL/PyBullet surgical
simulation tasks.

The project is not presented as a finished surgical autonomy system. Its goal
is narrower and research-oriented: evaluate when a surgical RL or scripted
controller should continue autonomously, recover automatically, request human
review, or stop because recovery may be unsafe.

![SurRoL NeedlePick rendered rollout](reports/media/surrol_render_evidence/needlepick/frames/needlepick_step_040.png)

## Research Question

Can a runtime reliability supervisor make surgical robot rollouts more robust
to execution drift, grasp/contact uncertainty, visual-state errors, and unsafe
recovery situations, while keeping the claims simulation-only and evidence
based?

The current supervisor studies four intervention routes:

| Route | Meaning |
|---|---|
| `auto_execute` | continue nominal execution |
| `auto_recovery` | allow automatic recovery for reversible execution drift |
| `human_review` | route uncertain grasp/contact or visual-state errors to review/re-estimation |
| `abort_candidate` | stop or flag recovery when an unsafe proxy is triggered |

## Main Contributions

1. Custom constrained surgical proxy environment for fast method development:
   3D tool navigation, forbidden-region costs, safety budgets, and recovery
   monitors.
2. SurRoL migration evidence across `NeedleReach`, `NeedlePick`, and
   `GauzeRetrieve`, including rendered RGB rollouts, traces, figures, and CSV
   summaries.
3. Formal fault taxonomy covering nominal execution, reversible execution
   drift, grasp/contact uncertainty, visual-state error, and near-target
   recovery risk.
4. Multi-seed recovery experiments showing that runtime supervision can recover
   corrupted SurRoL rollouts in simulation.
5. Learned route classifier that predicts whether an episode should be routed
   to `auto_execute`, `auto_recovery`, `human_review`, or `abort_candidate`.
6. Observable-supervisor audit that reduces the jaw-stuck replan decision's
   dependence on privileged SurRoL phase/contact state.

## Key Results

### 10-Seed SurRoL Recovery Evidence

| Task | Fault | Intervention | Perturbed | Recovered |
|---|---|---|---:|---:|
| NeedlePick | `action_noise` | internal phase-aware recovery | 0/10 | 9/10 |
| NeedlePick | `action_dropout` | internal phase-aware recovery | 0/10 | 10/10 |
| NeedlePick | `execution_slip` | internal phase-aware recovery | 0/10 | 10/10 |
| GauzeRetrieve | `action_noise` | internal phase-aware recovery | 0/10 | 10/10 |
| GauzeRetrieve | `action_dropout` | internal phase-aware recovery | 0/10 | 10/10 |
| GauzeRetrieve | `execution_slip` | internal phase-aware recovery | 0/10 | 10/10 |
| NeedlePick | `perception_bias` | review/re-estimation | 0/10 | 10/10 |
| NeedlePick | `depth_scale_error` | review/re-estimation | 0/10 | 10/10 |
| GauzeRetrieve | `perception_bias` | review/re-estimation | 0/10 | 10/10 |
| GauzeRetrieve | `depth_scale_error` | review/re-estimation | 0/10 | 10/10 |
| NeedlePick | `jaw_stuck_open` | observable proxy recovery | 0/10 | 10/10 |
| GauzeRetrieve | `jaw_stuck_open` | observable proxy recovery | 0/10 | 10/10 |

Full tables:

- [SurRoL master paired results](reports/tables/surrol_master_paired_results.csv)
- [SurRoL master report](reports/surrol_master_results_round13_zh.md)
- [Fault taxonomy report](reports/surrol_fault_taxonomy_step2.md)

### Learned Route Classifier

The safety-biased episode-level route classifier is evaluated with an even/odd
seed split.

| Metric | Value |
|---|---:|
| held-out episodes | 460 |
| accuracy | 0.846 |
| macro-F1 | 0.828 |
| missed review-or-abort rate | 0.000 |
| false review-or-abort rate | 0.162 |

Report and tables:

- [Step 3 learned route classifier report](reports/surrol_learned_route_classifier_step3.md)
- [Per-route metrics](reports/tables/surrol_learned_route_classifier_metrics.csv)
- [Confusion table](reports/tables/surrol_learned_route_classifier_confusion.csv)

### Observable Supervisor

For silent `jaw_stuck_open` failures, the replan decision is moved away from
SurRoL internal waypoint/contact checks toward observable command/progress
signals:

- jaw close command count;
- goal-distance stagnation;
- minimum-distance improvement;
- offline observable risk score.

At threshold 3.0, the observable risk score detects 10/10 jaw-stuck perturbed
episodes for both `NeedlePick` and `GauzeRetrieve`, with 0/10 nominal
monitor-corrected alarms in the current logs.

Report and tables:

- [Step 4 observable supervisor report](reports/surrol_observable_supervisor_step4.md)
- [Observable signal audit](reports/tables/surrol_observable_signal_audit.csv)
- [Observable versus privileged comparison](reports/tables/surrol_observable_vs_privileged_jaw_stuck.csv)

## Visual Evidence

The repository includes rendered SurRoL/PyBullet rollout evidence:

| Task | GIF | MP4 | Trace |
|---|---|---|---|
| NeedleReach | [GIF](reports/media/surrol_render_evidence/needlereach/needlereach_oracle_rollout.gif) | [MP4](reports/media/surrol_render_evidence/needlereach/needlereach_oracle_rollout.mp4) | [CSV](reports/media/surrol_render_evidence/needlereach/rollout_trace.csv) |
| NeedlePick | [GIF](reports/media/surrol_render_evidence/needlepick/needlepick_oracle_rollout.gif) | [MP4](reports/media/surrol_render_evidence/needlepick/needlepick_oracle_rollout.mp4) | [CSV](reports/media/surrol_render_evidence/needlepick/rollout_trace.csv) |
| GauzeRetrieve | [GIF](reports/media/surrol_render_evidence/gauzeretrieve/gauzeretrieve_oracle_rollout.gif) | [MP4](reports/media/surrol_render_evidence/gauzeretrieve/gauzeretrieve_oracle_rollout.mp4) | [CSV](reports/media/surrol_render_evidence/gauzeretrieve/rollout_trace.csv) |

More evidence is indexed in [docs/evidence_index.md](docs/evidence_index.md).

## Repository Structure

```text
src/                         custom constrained surgical RL environments
scripts/                     experiment, analysis, plotting, and report scripts
tests/                       lightweight unit and regression tests
reports/                     research reports, figures, media, and result tables
reports/tables/              CSV summaries for SurRoL reliability experiments
reports/media/               rendered SurRoL rollout evidence
docs/                        application-facing project notes and upload guide
```

Local training outputs and checkpoints are intentionally not committed:

```text
runs/
.conda/
*.zip
```

## Setup

For the custom proxy environment:

```powershell
conda create --prefix E:\RL_projects\constraint_surgical_rl\.conda python=3.10 pip -y
conda activate E:\RL_projects\constraint_surgical_rl\.conda
pip install -e .[rl,dev]
```

Run smoke tests:

```powershell
$env:PYTHONPATH="E:\RL_projects\constraint_surgical_rl\src"
python -m pytest tests\test_tool_navigation.py tests\test_surrol_ppo_reward_and_vision.py
```

For SurRoL experiments, this repository assumes a separate local SurRoL checkout
and environment. The local runner used during development points to:

```text
SurRoL source: /mnt/e/RL_projects/SurRoL_clean_SR-VPPV
SurRoL env:    /mnt/e/RL_projects/surrol_py38_env
```

See [reports/surrol_wsl_deployment_notes_zh.md](reports/surrol_wsl_deployment_notes_zh.md)
for environment notes.

## Reproduce Key Summaries

The generated reports can be rebuilt from stored CSV logs:

```powershell
python scripts\build_surrol_master_results.py
python scripts\build_surrol_fault_taxonomy.py
python scripts\train_surrol_route_classifier.py
python scripts\analyze_observable_proxy_risk.py
python scripts\build_surrol_observable_supervisor_step4.py
python scripts\audit_surrol_upgrade_status.py
```

Regenerate rendered SurRoL media:

```powershell
.\scripts\export_surrol_render_assets.ps1 -Tasks "NeedleReach,NeedlePick,GauzeRetrieve" -MaxSteps 80 -FrameStride 4
```

## Application Notes

For a concise PhD-application style description, see:

- [Project brief](docs/phd_application_project_brief.md)
- [Evidence index](docs/evidence_index.md)
- [GitHub upload guide in Chinese](docs/github_upload_guide_zh.md)

## Limitations

- This is a simulation-only research prototype.
- SurRoL recovery experiments use scripted/oracle task primitives as part of
  the evaluation harness.
- The learned route classifier is episode-level and uses labels distilled from
  current rule/proxy routing, not independent expert annotations.
- `abort_candidate` remains low-support and geometry-proxy based.
- The observable supervisor reduces decision dependence on privileged
  phase/contact state for jaw-stuck recovery, but the executed recovery
  primitive still uses scripted SurRoL waypoint regeneration.
- The project should not be described as clinical validation, real-robot
  deployment, or a complete end-to-end surgical autonomy solution.

## Suggested One-Sentence Summary

This project studies failure-aware runtime supervision for SurRoL-based
surgical robot learning, moving from a custom constrained 3D proxy to
multi-seed SurRoL recovery, risk routing, learned route classification, and
observable proxy supervision.
