# SurRoL Reliability Upgrade Project

This document tracks the four-step upgrade plan for turning the current
failure-aware SurRoL prototype into a stronger PhD-application research
artifact.

## Research Goal

Upgrade the project from "SurRoL migration and recovery demo" to a defensible
failure-aware surgical autonomy prototype:

```text
custom constrained 3D proxy
-> SurRoL task migration
-> failure taxonomy
-> risk routing
-> learned/observable reliability supervisor
```

The project should remain explicitly simulation-only and research-prototype
level. It should not claim real-robot deployment, clinical validation, or a
finished learned surgical policy.

## Step 1: Upgrade Key Experiments To 10 Seeds

Purpose: reduce the weakness of 5-seed pilot claims.

Current status:

- 10-seed evidence already exists for observable jaw-stuck recovery on
  `NeedlePick` and `GauzeRetrieve`.
- Standard action corruptions are still mainly 5-seed:
  `action_noise`, `action_dropout`, `execution_slip`.
- Visual-state errors and review/re-estimation are still mainly 5-seed:
  `perception_bias`, `depth_scale_error`.
- `NeedleReach` currently serves as a third-task sanity check, not a full
  complex manipulation task.

Priority experiments:

1. `NeedlePick` standard corruptions, 10 seeds.
2. `GauzeRetrieve` standard corruptions, 10 seeds.
3. `NeedlePick` and `GauzeRetrieve` perception/re-estimation, 10 seeds.
4. Optional: `NeedleReach` action-freeze, 10 seeds, as breadth evidence.

Smoke status:

- `NeedlePick/action_noise`, 1 seed, 20 steps, `phase_replan`: passed on
  2026-06-22. This only validates the runner and output path; it is not a
  formal result.

Completed formal batch:

| Task | Failure | Seeds | Perturbed success | Recovered success | Mean recovered distance | Note |
|---|---:|---:|---:|---:|---:|---|
| NeedlePick | action_noise | 10 | 0.000 | 0.900 | 0.0426 | one high-trigger failure case remains |
| NeedlePick | action_dropout | 10 | 0.000 | 1.000 | 0.0208 | recovered |
| NeedlePick | execution_slip | 10 | 0.000 | 1.000 | 0.0212 | recovered |
| GauzeRetrieve | action_noise | 10 | 0.000 | 1.000 | 0.0159 | recovered |
| GauzeRetrieve | action_dropout | 10 | 0.000 | 1.000 | 0.0132 | recovered |
| GauzeRetrieve | execution_slip | 10 | 0.000 | 1.000 | 0.0127 | recovered |
| NeedlePick | perception_bias | 10 | 0.000 | 1.000 | 0.0202 | review/re-estimation |
| NeedlePick | depth_scale_error | 10 | 0.000 | 1.000 | 0.0202 | review/re-estimation |
| GauzeRetrieve | perception_bias | 10 | 0.000 | 1.000 | 0.0134 | review/re-estimation |
| GauzeRetrieve | depth_scale_error | 10 | 0.000 | 1.000 | 0.0134 | review/re-estimation |

Output files:

- `runs/surrol_needlepick_phase_replan_w32_10seed.csv`
- `runs/surrol_needlepick_phase_replan_w32_10seed_steps.csv`
- `reports/surrol_needlepick_phase_replan_w32_10seed.md`
- `runs/surrol_gauzeretrieve_phase_replan_w32_10seed.csv`
- `runs/surrol_gauzeretrieve_phase_replan_w32_10seed_steps.csv`
- `reports/surrol_gauzeretrieve_phase_replan_w32_10seed.md`
- `runs/surrol_needlepick_review_reestimate_w16_10seed.csv`
- `runs/surrol_needlepick_review_reestimate_w16_10seed_steps.csv`
- `reports/surrol_needlepick_review_reestimate_w16_10seed.md`
- `runs/surrol_gauzeretrieve_review_reestimate_w16_10seed.csv`
- `runs/surrol_gauzeretrieve_review_reestimate_w16_10seed_steps.csv`
- `reports/surrol_gauzeretrieve_review_reestimate_w16_10seed.md`
- `reports/tables/surrol_master_paired_results.csv`

Suggested first formal batch:

```powershell
.\scripts\run_surrol_monitor_recovery.ps1 `
  -Task NeedlePick `
  -Failures "none,action_noise,action_dropout,execution_slip" `
  -Seeds 10 -Episodes 1 -MaxSteps 200 -RecoverySteps 32 `
  -TriggerMode goalaware -RecoveryPolicy phase_replan `
  -EpisodeOut "/mnt/e/RL_projects/constraint_surgical_rl/runs/surrol_needlepick_phase_replan_w32_10seed.csv" `
  -StepOut "/mnt/e/RL_projects/constraint_surgical_rl/runs/surrol_needlepick_phase_replan_w32_10seed_steps.csv" `
  -Report "/mnt/e/RL_projects/constraint_surgical_rl/reports/surrol_needlepick_phase_replan_w32_10seed.md"

.\scripts\run_surrol_monitor_recovery.ps1 `
  -Task GauzeRetrieve `
  -Failures "none,action_noise,action_dropout,execution_slip" `
  -Seeds 10 -Episodes 1 -MaxSteps 200 -RecoverySteps 32 `
  -TriggerMode goalaware -RecoveryPolicy phase_replan `
  -EpisodeOut "/mnt/e/RL_projects/constraint_surgical_rl/runs/surrol_gauzeretrieve_phase_replan_w32_10seed.csv" `
  -StepOut "/mnt/e/RL_projects/constraint_surgical_rl/runs/surrol_gauzeretrieve_phase_replan_w32_10seed_steps.csv" `
  -Report "/mnt/e/RL_projects/constraint_surgical_rl/reports/surrol_gauzeretrieve_phase_replan_w32_10seed.md"
```

## Step 2: Formalize Fault Taxonomy

Purpose: make the contribution read as a structured reliability problem rather
than a list of ad hoc failure cases.

Taxonomy:

| Fault family | Example failures | Intended route |
|---|---|---|
| Nominal execution | none | `auto_execute` |
| Reversible execution drift | action noise, dropout, slip, freeze | `auto_recovery` |
| Grasp/contact uncertainty | jaw stuck, grasp retry failure | `human_review` or observable grasp retry |
| Visual-state error | perception bias, depth scale error | `human_review` / re-estimation |
| Unsafe recovery risk | near-target danger-zone entry | `abort_candidate` |

Deliverable:

- A clean table in README/report showing task, fault family, failure, route,
  seeds, perturbed success, recovered success, and limitation.

Completed deliverables:

- `scripts/build_surrol_fault_taxonomy.py`
- `reports/tables/surrol_fault_taxonomy.csv`
- `reports/surrol_fault_taxonomy_step2.md`

Current taxonomy families:

- `nominal_execution`
- `reversible_execution_drift`
- `grasp_contact_uncertainty`
- `visual_state_error`
- `near_target_recovery_risk`

## Step 3: Learn A Risk Classifier

Purpose: move beyond hand-written routing rules.

Minimum useful model:

- Inputs: step-level traces already present in SurRoL logs, including distance,
  progress, action deviation, trigger counts, visual-state error proxies, and
  grasp progress features.
- Labels: `auto_execute`, `auto_recovery`, `human_review`, `abort_candidate`.
- Baselines: rule route, logistic regression, small MLP or random forest.
- Metrics: macro-F1, per-class recall, false review rate, missed-review rate,
  and coverage-risk curve.

Current status:

- A learned risk head table already exists with high precision and recall for a
  binary review-style decision.
- Reliability-memory results already exist, but `abort_candidate` is weak due
  to low support.
- A multiclass learned route classifier has been trained on episode-level
  SurRoL rollout features with an even/odd seed split.
- The current safety-biased logistic route classifier reaches 84.6% held-out
  accuracy and 82.8% macro-F1 across `auto_execute`, `auto_recovery`,
  `human_review`, and `abort_candidate`.
- The classifier achieves 0.0% missed review-or-abort rate on the current
  held-out split, at the cost of a 16.2% false review-or-abort rate. This is a
  deliberately conservative reliability trade-off.

Upgrade target:

- Report route-level performance with train/test split by episode or seed.
- Avoid leakage from multiple steps of the same episode appearing in both train
  and test.
- Emphasize whether the classifier catches important unsafe or review-worthy
  errors, not only overall accuracy.

Completed deliverables:

- `scripts/train_surrol_route_classifier.py`
- `reports/tables/surrol_learned_route_classifier_scored.csv`
- `reports/tables/surrol_learned_route_classifier_metrics.csv`
- `reports/tables/surrol_learned_route_classifier_confusion.csv`
- `reports/tables/surrol_learned_route_classifier_weights.csv`
- `reports/tables/surrol_learned_route_classifier_summary.csv`
- `reports/surrol_learned_route_classifier_step3.md`

Important limitation:

- This is an episode-level classifier with labels distilled from the current
  rule/proxy routing policy. It is research evidence for risk routing, not an
  independently validated online surgical supervisor.

## Step 4: Reduce Privileged Simulator-State Dependence

Purpose: make the recovery monitor closer to deployable surgical autonomy.

Current status:

- Internal `phase_replan` uses SurRoL waypoint/contact state.
- `observable_phase_replan` already reduces this for jaw-stuck recovery by
  using command history and progress stagnation.
- `render_proprio_vision` exists, but learned visual policy success is still
  preliminary and low.
- A Step 4 observable-supervisor audit now separates privileged simulator
  signals from observable proxy signals and compares observable recovery against
  internal phase-aware recovery.
- On 10-seed `jaw_stuck_open` experiments, observable proxy recovery keeps the
  result at 0/10 perturbed success to 10/10 recovered success for both
  `NeedlePick` and `GauzeRetrieve`.
- At threshold 3.0, the offline observable risk score detects 10/10 jaw-stuck
  perturbed episodes for both tasks and has 0/10 nominal monitor-corrected
  alarms in the current logs.

Upgrade target:

- Replace internal phase/contact checks with observable signals whenever
  possible:
  - jaw close command count;
  - distance stagnation;
  - action deviation;
  - progress slope;
  - rendered RGB pooled features;
  - risk-head score.
- Keep internal-state experiments as an upper-bound baseline.
- Report observable proxy versus privileged oracle side by side.

Completed deliverables:

- `scripts/analyze_observable_proxy_risk.py`
- `scripts/build_surrol_observable_supervisor_step4.py`
- `reports/tables/observable_proxy_scored_steps_10seed.csv`
- `reports/tables/observable_proxy_threshold_sweep_10seed.csv`
- `reports/tables/surrol_observable_signal_audit.csv`
- `reports/tables/surrol_observable_vs_privileged_jaw_stuck.csv`
- `reports/figures/observable_proxy_risk/observable_proxy_threshold_sweep.png`
- `reports/surrol_observable_supervisor_step4.md`

Important limitation:

- The replan decision is observable-proxy based for jaw-stuck recovery, but the
  executed recovery primitive still uses scripted SurRoL waypoint regeneration.
  Standard action corruptions also still use the internal phase-aware recovery
  path in the strongest 10-seed suite.

## Application Framing

Recommended claim:

> This project studies failure-aware runtime recovery for SurRoL-based surgical
> embodied intelligence. It starts from a custom constrained proxy environment
> and migrates the reliability-supervision idea into SurRoL tasks, where it
> evaluates execution drift, grasp/contact failures, visual-state errors, and
> unsafe recovery routing.

Avoid claiming:

- real surgical autonomy;
- clinical or real-robot validation;
- a mature end-to-end learned policy;
- parity with the SurRoL platform itself.
