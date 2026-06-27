# Failure-Aware Reliability Supervision for Surgical RL

## One-Page Summary

This repository is a simulation research prototype for **runtime reliability
supervision in surgical robot learning**. The central question is not simply
"can an RL policy finish the task?", but:

> When a surgical robot policy becomes unreliable, how should the system decide
> whether to continue, recover automatically, request review, or stop?

The project follows the same reliability-first logic as the VT/VF ECG work:
accuracy or task success is not enough. The system should expose **why** a
state/action is risky, **which mechanism** produced the risk, and **what runtime
route** should be taken.

The research path is staged:

1. build a custom constrained surgical-tool proxy for fast safety-control
   experiments;
2. migrate the reliability-supervision idea into SurRoL/PyBullet surgical
   simulation tasks;
3. organize failures into explicit intervention routes;
4. evaluate multi-seed recovery, learned route prediction, and observable
   supervision;
5. upgrade the proxy controller from always-on tangent backup to risk-gated
   and then ECG-inspired mechanism-routed tangent supervision;
6. test whether embedding/KNN instability signals can feed back into PPO
   training.

This is **not** a clinical, hardware, or deployment claim. It is internal
simulation evidence that reliability analysis can become a runtime decision
signal for surgical RL.

![SurRoL NeedlePick rendered rollout](reports/media/surrol_render_evidence/needlepick/frames/needlepick_step_040.png)

## Main Research Question

Can a runtime reliability supervisor make simulated surgical robot rollouts
more robust to execution drift, grasp/contact uncertainty, visual-state errors,
and unsafe recovery situations, while keeping the claims simulation-only and
evidence based?

The supervisor uses four runtime routes:

| Route | Meaning | Typical trigger |
|---|---|---|
| `auto_execute` | continue nominal execution | no strong risk signal |
| `auto_recovery` | allow automatic recovery | reversible execution drift |
| `human_review` | route to review or re-estimation | visual-state uncertainty, grasp/contact ambiguity |
| `abort_candidate` | stop or flag recovery as unsafe | near-target forbidden-zone or irreversible-risk proxy |

## Method Logic

The project is easiest to understand as a staged reliability system, not as one
mixed experiment.

| Stage | What Was Built | Why It Was Needed | Main Evidence | Main Limitation |
|---|---|---|---|---|
| 1. Custom proxy environment | 3D constrained surgical-tool navigation with forbidden region, force proxy, safety budget, and PPO/controller interfaces | Fast environment for testing safety-control ideas before SurRoL | proxy rollouts, risk-gated tangent, mechanism-routed tangent | simplified geometry, not a real surgical simulator |
| 2. Tangent backup control | backup action that moves tangentially around forbidden regions | safer than stopping or pushing into the forbidden zone | always-tangent gives 0.000 budget exhaustion | always-on correction over-intervenes |
| 3. Risk-gated tangent | interpretable risk gate activates tangent backup only when needed | turns post-hoc reliability analysis into runtime control | activation falls from 1.000 to 0.450/0.426 while keeping 0.000 budget exhaustion | still one total risk decision |
| 4. Mechanism-routed tangent | ECG-inspired two-stage router: boundary-first plus residual-mechanism review | separates irreversible boundary risk from residual mechanisms | activation falls to 0.443/0.416 with 0.000 budget exhaustion | improvement over risk-gated is modest; Stage 2 is logged, not yet a learned recovery policy |
| 5. SurRoL migration | NeedleReach, NeedlePick, GauzeRetrieve rendered rollouts and traces | proves the project moved beyond the proxy into surgical simulation | GIF/MP4/PNG/CSV rollout evidence | uses scripted/oracle primitives in parts of the evaluation harness |
| 6. Fault taxonomy and recovery routes | formal route labels for action drift, perception drift, jaw-stuck, unsafe recovery | makes failures explainable and comparable | fault taxonomy, 10-seed paired recovery tables | route labels are engineered, not expert annotated |
| 7. Learned and observable supervisors | route classifier and observable jaw-stuck supervisor | reduces dependence on hand-written rules and privileged simulator state | held-out classifier metrics, observable signal audit | still simulation-only; observable recovery still uses scripted primitives |
| 8. Embedding-risk training | reward shaping and hard-negative curriculum from embedding/KNN risk | tests whether instability analysis can improve training, not only explain failure | multi-seed PPO pilot | improves return/distance metrics, not robust success/budget outcomes |

## Key Results

### 1. Risk-Gated Tangent Backup

This is a custom proxy/controller experiment, not a SurRoL experiment. It
compares the same PPO policy under unshielded execution, always-on tangent
backup, and risk-gated tangent backup.

| Preset | Method | Budget exhaustion | Supervisor activation |
|---|---|---:|---:|
| prototype | unshielded PPO | 0.907 | 0.000 |
| prototype | always tangent | 0.000 | 1.000 |
| prototype | risk-gated tangent | 0.000 | 0.450 |
| strict | unshielded PPO | 0.977 | 0.000 |
| strict | always tangent | 0.000 | 1.000 |
| strict | risk-gated tangent | 0.000 | 0.426 |

Interpretation: risk-gated tangent preserves the safety-budget behavior of
always-on tangent backup while cutting supervisor-on timesteps by roughly half.

Limitations: the risk labels are weak simulation labels; offline risk coverage
does not prove online causal safety; this is still the custom proxy setting.

### 2. Mechanism-Routed Tangent Backup

Inspired by the VT/VF ECG reliability-routing upgrade, the proxy supervisor was
upgraded from one total risk gate into a two-stage mechanism router:

- Stage 1: boundary/force/workspace risks trigger tangent backup.
- Stage 2: residual mechanisms such as low budget, stagnation, late progress,
  and large actions are logged as review evidence.

| Preset | Method | Budget exhaustion | Supervisor activation | Non-correction activation |
|---|---|---:|---:|---:|
| prototype | risk-gated tangent | 0.000 | 0.450 | 0.027 |
| prototype | mechanism-routed tangent | 0.000 | 0.443 | 0.020 |
| strict | risk-gated tangent | 0.000 | 0.426 | 0.030 |
| strict | mechanism-routed tangent | 0.000 | 0.416 | 0.021 |

Interpretation: this is a modest but cleaner upgrade. Safety is preserved,
unnecessary supervisor activation is slightly reduced, and every intervention
has a mechanism-level explanation rather than a single black-box risk label.

Limitations: Stage 2 is currently a logging/review route, not a separate learned
recovery controller; the numerical improvement over risk-gated tangent is
small.

### 3. SurRoL Recovery Evidence

The reliability-supervision idea was migrated into SurRoL/PyBullet tasks. The
main recovery evidence uses 10-seed paired experiments.

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

Interpretation: the project demonstrates a reliability-supervision pipeline
for routing and recovering several injected failure families in simulation.

Limitations: some recovery behavior uses scripted/oracle primitives; these
experiments do not prove end-to-end learned surgical autonomy.

### 4. Learned Route Classifier

The route classifier tests whether route decisions can be learned from episode
features rather than only hand-written rules.

| Metric | Value |
|---|---:|
| held-out episodes | 460 |
| accuracy | 0.846 |
| macro-F1 | 0.828 |
| missed review-or-abort rate | 0.000 |
| false review-or-abort rate | 0.162 |

Interpretation: route prediction is learnable with a safety-biased classifier,
and the held-out split avoids missing review-or-abort cases in the current
data.

Limitations: labels are distilled from the current routing logic, not
independent human/expert labels; the classifier is episode-level rather than a
full online policy.

### 5. Observable Supervisor

The observable supervisor reduces dependence on privileged SurRoL internal
state for silent `jaw_stuck_open` failures. It uses:

- jaw close command count;
- goal-distance stagnation;
- minimum-distance improvement;
- offline observable risk score.

At threshold 3.0, the observable risk score detects 10/10 jaw-stuck perturbed
episodes for both `NeedlePick` and `GauzeRetrieve`, with 0/10 nominal
monitor-corrected alarms in the current logs.

Limitations: the decision trigger is more observable, but the executed recovery
primitive still uses scripted SurRoL waypoint regeneration.

### 6. Embedding-Risk Training Pilot

The embedding/KNN instability signal was connected to PPO training in two ways:

- risk-aware reward shaping;
- hard-negative curriculum reset sampling.

The three-seed follow-up shows that curriculum fine-tuning improves mean return
and strict final distance, but does **not** reliably improve success rate or
safety-budget exhaustion.

Interpretation: embedding risk can affect training and change learned behavior,
but it is not yet a robust policy-improvement method.

Limitations: short-horizon PPO, only three seeds, and no stable success/safety
improvement yet.

## Claim-Evidence-Limitation Map

| Claim | Evidence | Strength | Boundary |
|---|---|---|---|
| Runtime reliability can decide when tangent backup is needed. | risk-gated tangent preserves 0.000 budget exhaustion while reducing activation | strong for proxy controller | custom proxy only |
| Mechanism-separated routing makes the controller more interpretable. | Stage 1/Stage 2 mechanism-routed tangent report and route summary | moderate-to-strong | modest numerical improvement |
| The idea moved beyond the toy proxy. | SurRoL rendered GIF/MP4/PNG rollouts for NeedleReach, NeedlePick, GauzeRetrieve | strong for simulation migration | not real robot |
| Failure routing improves recovery under injected faults. | 10-seed paired recovery tables | strong within current SurRoL setup | scripted recovery components |
| Route prediction is learnable. | held-out route classifier metrics | moderate | labels are distilled |
| Observable signals can reduce privileged-state dependence. | jaw-stuck observable supervisor audit | promising | recovery primitive remains scripted |
| Embedding risk can enter training. | reward shaping and curriculum PPO pilots | preliminary | not robust success/safety improvement |

## Recommended Reading Order

For a teacher or reviewer, read in this order:

1. [Full research report](reports/full_research_report.md)
2. [Project index](docs/PROJECT_INDEX.md)
3. [Evidence index](docs/evidence_index.md)
4. [SurRoL master results](reports/surrol_master_results.md)
5. [Risk-gated tangent report](reports/risk_gated_tangent_report.md)
6. [Mechanism-routed tangent v5d report](reports/mechanism_routed_tangent_v5d_report.md)
7. [Embedding-risk training pilot](reports/embedding_risk_training_pilot.md)

## Visual Evidence

The repository contains two kinds of visual evidence, and they should not be
confused:

| Visual family | What it shows | Where |
|---|---|---|
| Custom proxy controller visuals | top-down proxy trajectories, tangent backup behavior, controller activation | `reports/figures/risk_gated_tangent_visuals/`, `reports/figures/mechanism_routed_tangent_v5d/` |
| SurRoL/PyBullet rendered evidence | rendered surgical simulation rollouts for NeedleReach, NeedlePick, GauzeRetrieve | `reports/media/surrol_render_evidence/` |

## Repository Structure

```text
src/                         custom constrained surgical RL environments
scripts/                     experiment, analysis, plotting, and report scripts
tests/                       unit and regression tests
reports/                     research reports, figures, media, and tables
reports/tables/              CSV summaries for SurRoL reliability experiments
reports/media/               rendered SurRoL rollout evidence
docs/                        project index, evidence map, research sequence
outputs/                     selected lightweight experiment summaries
runs/                        local training outputs and checkpoints, not committed
```

## Reproduce Key Summaries

Custom proxy tests:

```powershell
$env:PYTHONPATH="$PWD\src"
python -m pytest tests\test_tool_navigation.py
```

Risk-gated and mechanism-routed tangent comparison:

```powershell
python scripts\evaluate_risk_gated_tangent.py --policy ppo --model runs\pilot_3d_50k_prototype_conditioned_seed0\model.zip --episodes 100 --seeds 0,1,2 --presets prototype,strict --threshold 0.5 --deterministic --risk-model-mode default_rule --out-dir outputs\mechanism_routed_tangent_v5d
```

SurRoL summaries:

```powershell
python scripts\build_surrol_master_results.py
python scripts\build_surrol_fault_taxonomy.py
python scripts\train_surrol_route_classifier.py
python scripts\analyze_observable_proxy_risk.py
python scripts\build_surrol_observable_supervisor_step4.py
```

Embedding-risk PPO pilot:

```powershell
python scripts\run_embedding_risk_multiseed_curriculum.py --seeds 0,1,2 --timesteps 8192 --episodes 50 --penalty-scale 0.25 --risk-threshold 0.55 --curriculum-probability 0.35 --curriculum-candidates 8
```

## What Not To Overclaim

- Do not describe the project as clinical validation.
- Do not describe it as real-robot deployment.
- Do not claim formal safety guarantees.
- Do not claim complete end-to-end learned surgical autonomy.
- Do not claim embedding-risk curriculum reliably improves success rate; the
  current evidence only supports partial return/distance improvements.

## Suggested One-Sentence Summary

This project studies failure-aware runtime supervision for simulated surgical
robot learning, moving from a custom constrained 3D proxy to SurRoL recovery,
learned route classification, observable supervision, risk-gated tangent
backup, ECG-inspired mechanism-routed reliability control, and preliminary
embedding-risk-guided PPO training.
