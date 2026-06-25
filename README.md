# Failure-Aware Reliability Supervision for Surgical RL

This repository is a research prototype for reliability-supervised surgical
robot learning. The research path is deliberately staged: first build a simple
custom constrained surgical-tool proxy to test obstacle avoidance, backup
control, and safety-budget ideas; then migrate the same reliability-supervision
logic into SurRoL/PyBullet surgical simulation tasks.

The project is not presented as a finished surgical autonomy system. Its goal
is narrower and research-oriented: evaluate when a surgical RL or scripted
controller should continue autonomously, recover automatically, request human
review, or stop because recovery may be unsafe.

The current controller-level result is an action-level risk-gated tangent backup
supervisor in the custom proxy controller setting. Instead of allowing the
tangent backup controller to supervise every timestep, an interpretable risk
gate first checks whether the proposed state/action is unsafe. Reliability
analysis therefore becomes a runtime decision signal, not only a post-hoc
explanation.

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

## Project Logic

The project should be read as a staged research path, not as one mixed experiment:

1. **Self-built proxy simulation.** A simplified constrained surgical-tool
   environment was built first. It supports obstacle/forbidden-region avoidance,
   safety budgets, tangent backup control, and fast PPO/controller experiments.
   The `prototype` and `strict` risk-gated tangent figures belong to this proxy
   setting; they are controller-level visualizations, not SurRoL renders.
2. **SurRoL migration.** The same reliability-supervision idea was then embedded
   into SurRoL/PyBullet surgical tasks, using `NeedleReach`, `NeedlePick`, and
   `GauzeRetrieve` rendered rollouts.
3. **Four intervention routes.** SurRoL rollout failures were organized into
   `auto_execute`, `auto_recovery`, `human_review`, and `abort_candidate`, so
   the project is about deciding what type of runtime response is appropriate.
4. **Final reliability results.** The SurRoL side was stress-tested with
   multi-seed recovery, route classification, and observable-proxy supervision;
   the proxy controller side was changed from always-on tangent backup to
   risk-gated tangent backup.

## Main Contributions

1. Custom constrained surgical proxy environment for fast method development:
   3D tool navigation, forbidden-region costs, safety budgets, and recovery
   monitors.
2. Risk-gated tangent backup in the proxy controller setting: an action-level
   reliability supervisor that keeps always-tangent budget safety while reducing
   always-on supervisor activation.
3. SurRoL migration evidence across `NeedleReach`, `NeedlePick`, and
   `GauzeRetrieve`, including rendered RGB rollouts, traces, figures, and CSV
   summaries.
4. Formal fault taxonomy covering nominal execution, reversible execution
   drift, grasp/contact uncertainty, visual-state error, and near-target
   recovery risk.
5. Multi-seed recovery experiments showing that runtime supervision can recover
   corrupted SurRoL rollouts in simulation.
6. Learned route classifier that predicts whether an episode should be routed
   to `auto_execute`, `auto_recovery`, `human_review`, or `abort_candidate`.
7. Observable-supervisor audit that reduces the jaw-stuck replan decision's
   dependence on privileged SurRoL phase/contact state.

## Recommended Reading Order

For a quick review, do not browse the full `reports/` folder first. Read the
project-facing path in this order:

1. [Project index](docs/PROJECT_INDEX.md)
2. [Project overview](docs/project_overview.md)
3. [Evidence index](docs/evidence_index.md)
4. [Research sequence](docs/research_sequence.md)
5. [SurRoL master results](reports/surrol_master_results.md)
6. [Learned route classifier](reports/surrol_learned_route_classifier_step3.md)
7. [Observable supervisor](reports/surrol_observable_supervisor_step4.md)
8. [Risk-gated tangent backup report](reports/risk_gated_tangent_report.md)
9. [Embedding-risk training pilot](reports/embedding_risk_training_pilot.md)

## Key Results

### Risk-Gated Tangent Backup

This is a custom proxy/controller experiment, not a SurRoL experiment. It
compares the same PPO policy under three execution modes: unshielded PPO,
always-on tangent backup, and risk-gated tangent backup. The risk gate records
interpretable intervention reasons such as proposed forbidden-zone proximity,
low clearance, low safety budget, stalled progress, force proxy, and large
action magnitude.

| Preset | Method | Budget exhaustion | Supervisor activation |
|---|---|---:|---:|
| prototype | unshielded PPO | 0.907 | 0.000 |
| prototype | always tangent | 0.000 | 1.000 |
| prototype | risk-gated tangent | 0.000 | 0.450 |
| strict | unshielded PPO | 0.977 | 0.000 |
| strict | always tangent | 0.000 | 1.000 |
| strict | risk-gated tangent | 0.000 | 0.426 |

This is the controller-level result: risk-gated tangent preserves the 0.000
budget-exhaustion safety of always tangent while cutting supervisor-on
timesteps by roughly half.

Report and visuals:

- [Risk-gated tangent report](reports/risk_gated_tangent_report.md)
- [Aggregate summary](outputs/risk_gated_tangent/aggregate_summary.csv)
- [Budget/intervention figure](reports/figures/risk_gated_tangent_visuals/aggregate_budget_intervention.png)
- [Risk-gate architecture](reports/figures/risk_gated_tangent_visuals/risk_gate_architecture.png)

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
- [SurRoL master report](reports/surrol_master_results.md)
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

### Embedding-Risk Training Pilot

The embedding/KNN instability signal is now tested inside the PPO training
loop in two ways: risk-aware reward shaping and hard-negative curriculum reset
sampling. This is a pilot training-loop result in the custom proxy environment,
not yet a formal multi-seed model-improvement claim.

The latest two-stage curriculum fine-tune improves the prototype pilot relative
to baseline: success rises from 0.025 to 0.050, budget exhaustion falls from
0.975 to 0.950, mean return improves from -41.783 to -27.116, and final
distance improves from 0.650 to 0.630. The strict preset does not yet show a
stable safety improvement, so the honest claim is that embedding risk can be
used as a training signal and can produce partial improvement, not that it
reliably improves the final policy across all settings.

- [Embedding-risk training pilot report](reports/embedding_risk_training_pilot.md)
- [Pilot comparison CSV](outputs/embedding_risk_training_pilot_comparison.csv)
- [Curriculum fine-tune summary CSV](outputs/embedding_risk_curriculum_finetune_pilot_summary.csv)
- [Curriculum pilot figure](reports/figures/embedding_risk_training_pilot/curriculum_finetune_metrics.png)

## Visual Evidence

The repository has two different kinds of visual evidence. They should not be
merged when explaining the project.

### Custom Proxy Controller Visuals

These figures explain the risk-gated tangent result in the self-built proxy
environment. The `prototype` and `strict` snapshots are top-down/controller
visualizations from this proxy setting, not SurRoL/PyBullet screenshots.

| Visual | File |
|---|---|
| architecture | [risk_gate_architecture.png](reports/figures/risk_gated_tangent_visuals/risk_gate_architecture.png) |
| budget/intervention result | [aggregate_budget_intervention.png](reports/figures/risk_gated_tangent_visuals/aggregate_budget_intervention.png) |
| safety/intervention frontier | [safety_intervention_frontier.png](reports/figures/risk_gated_tangent_visuals/safety_intervention_frontier.png) |
| prototype snapshots | [render_snapshots_prototype.png](reports/figures/risk_gated_tangent_visuals/render_snapshots_prototype.png) |
| strict trajectory | [trajectory_strict.png](reports/figures/risk_gated_tangent_visuals/trajectory_strict.png) |

### SurRoL/PyBullet Rendered Evidence

These media files are the actual SurRoL visual evidence. They show rendered
rollouts for the surgical simulation tasks and include GIF/MP4 media, selected
frame PNGs, and trace CSVs.

| Task | GIF | MP4 | Selected frames | Trace |
|---|---|---|---|---|
| NeedleReach | [GIF](reports/media/surrol_render_evidence/needlereach/needlereach_oracle_rollout.gif) | [MP4](reports/media/surrol_render_evidence/needlereach/needlereach_oracle_rollout.mp4) | [000](reports/media/surrol_render_evidence/needlereach/frames/needlereach_step_000.png), [020](reports/media/surrol_render_evidence/needlereach/frames/needlereach_step_020.png) | [CSV](reports/media/surrol_render_evidence/needlereach/rollout_trace.csv) |
| NeedlePick | [GIF](reports/media/surrol_render_evidence/needlepick/needlepick_oracle_rollout.gif) | [MP4](reports/media/surrol_render_evidence/needlepick/needlepick_oracle_rollout.mp4) | [000](reports/media/surrol_render_evidence/needlepick/frames/needlepick_step_000.png), [020](reports/media/surrol_render_evidence/needlepick/frames/needlepick_step_020.png), [040](reports/media/surrol_render_evidence/needlepick/frames/needlepick_step_040.png) | [CSV](reports/media/surrol_render_evidence/needlepick/rollout_trace.csv) |
| GauzeRetrieve | [GIF](reports/media/surrol_render_evidence/gauzeretrieve/gauzeretrieve_oracle_rollout.gif) | [MP4](reports/media/surrol_render_evidence/gauzeretrieve/gauzeretrieve_oracle_rollout.mp4) | [000](reports/media/surrol_render_evidence/gauzeretrieve/frames/gauzeretrieve_step_000.png), [020](reports/media/surrol_render_evidence/gauzeretrieve/frames/gauzeretrieve_step_020.png), [034](reports/media/surrol_render_evidence/gauzeretrieve/frames/gauzeretrieve_step_034.png) | [CSV](reports/media/surrol_render_evidence/gauzeretrieve/rollout_trace.csv) |

More evidence is indexed in [docs/evidence_index.md](docs/evidence_index.md).

## Repository Structure

```text
src/                         custom constrained surgical RL environments
scripts/                     experiment, analysis, plotting, and report scripts
tests/                       lightweight unit and regression tests
reports/                     research reports, figures, media, and result tables
reports/tables/              CSV summaries for SurRoL reliability experiments
reports/media/               rendered SurRoL rollout evidence
docs/                        ordered research sequence and project notes
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
conda create --prefix .\.conda python=3.10 pip -y
conda activate .\.conda
pip install -e .[rl,dev]
```

Run smoke tests:

```powershell
$env:PYTHONPATH="$PWD\src"
python -m pytest tests\test_tool_navigation.py tests\test_surrol_ppo_reward_and_vision.py
```

For SurRoL experiments, this repository assumes a separate SurRoL/PyBullet
checkout and compatible Python environment. The committed CSV, figure, and
media evidence can be inspected without committing a local SurRoL installation
path.

## Reproduce Key Summaries

The generated reports can be rebuilt from stored CSV logs:

```powershell
python scripts\build_surrol_master_results.py
python scripts\build_surrol_fault_taxonomy.py
python scripts\train_surrol_route_classifier.py
python scripts\analyze_observable_proxy_risk.py
python scripts\build_surrol_observable_supervisor_step4.py
```

Regenerate rendered SurRoL media:

```powershell
.\scripts\export_surrol_render_assets.ps1 -Tasks "NeedleReach,NeedlePick,GauzeRetrieve" -MaxSteps 80 -FrameStride 4
```

## Project Notes

For a concise project-level description, see:

- [Research sequence](docs/research_sequence.md)
- [Project overview](docs/project_overview.md)
- [Evidence index](docs/evidence_index.md)

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
