# Full Research Report: Failure-Aware Reliability Supervision for Surgical RL

## Executive Takeaway

This project develops a simulation-only reliability-supervision framework for
surgical robot learning. The core contribution is not a larger RL model. The
core contribution is a structured runtime supervisor that decides when a policy
should continue, recover, request review, or stop. The project begins in a
custom constrained surgical-tool proxy, migrates the same reliability logic into
SurRoL/PyBullet tasks, then adds learned routing, observable supervision,
risk-gated tangent backup, ECG-inspired mechanism-separated routing, and
embedding-risk-guided PPO training pilots.

The strongest evidence is that runtime supervision can reduce unsafe proxy
behavior and recover several injected SurRoL failure families in simulation. The
main limitation is that the system is not a real-robot or clinical validation,
and some recovery primitives remain scripted/oracle-assisted.

## 1. Problem Framing

### What Problem Is Being Studied?

Standard RL evaluation often asks whether the policy succeeds. This project
asks a more safety-oriented question:

> When the policy becomes unreliable, can the system identify the failure
> mechanism and choose an appropriate runtime response?

In surgical robotics, treating every failure as the same kind of failure is not
useful. A reversible execution drift, a visual-state error, a jaw-stuck grasp
problem, and a near-target unsafe recovery should not receive the same response.

### Why This Matters

In safety-adjacent robot learning, a controller should not only output actions.
It should also expose:

- whether the action is safe enough to execute;
- whether automatic recovery is reasonable;
- whether the system should ask for review or re-estimation;
- whether recovery should be stopped because it may become unsafe.

This is why the repository is framed as **failure-aware reliability
supervision**, not simply surgical RL training.

## 2. ECG-Inspired Upgrade Standard

The project was recently upgraded using the same structural logic as the VT/VF
ECG reliability project. The ECG project moved from accuracy-only
classification toward mechanism-separated reliability routing. This RL project
uses the same principle.

| ECG reliability idea | Surgical RL translation |
|---|---|
| Do not rely only on accuracy. | Do not rely only on task success. |
| Identify boundary ambiguity. | Identify forbidden-zone, workspace, force, and unsafe recovery boundaries. |
| Separate mechanisms instead of one total uncertainty score. | Separate boundary risk, residual mechanism risk, visual-state uncertainty, grasp/contact failure, and action drift. |
| Use review routing, not blind prediction. | Use `auto_execute`, `auto_recovery`, `human_review`, and `abort_candidate`. |
| Keep claims proportional to internal evidence. | State simulation-only limitations and avoid real-robot claims. |

The most direct ECG-style upgrade is the new
`MechanismRoutedTangentSafetyShieldAction`: a two-stage controller-level router
that separates boundary safety risks from residual mechanism risks.

## 3. Full Research Roadmap

| Stage | Goal | Implementation | Evidence | Limitation |
|---|---|---|---|---|
| 1. Custom proxy | Build a fast testbed for surgical-tool safety ideas | 3D constrained navigation environment with forbidden region, force proxy, and safety budget | proxy rollouts, PPO checkpoints, controller reports | simplified geometry |
| 2. Tangent backup | Correct unsafe actions without stopping | tangent backup controller | 0.000 budget exhaustion under always tangent | over-intervention |
| 3. Risk-gated tangent | Intervene only when needed | interpretable risk gate before tangent backup | activation drops to 0.450/0.426 with 0.000 budget exhaustion | one total risk score |
| 4. Mechanism-routed tangent | Separate boundary and residual mechanisms | ECG-inspired two-stage router | activation drops to 0.443/0.416 with mechanism routes | modest gain; Stage 2 not yet a learned recovery |
| 5. SurRoL migration | Move beyond proxy into surgical simulation | NeedleReach, NeedlePick, GauzeRetrieve rollouts | rendered GIF/MP4/PNG and trace CSV | still simulation |
| 6. Fault taxonomy | Give failures interpretable route labels | action/perception/grasp/unsafe recovery taxonomy | fault taxonomy report and tables | engineered labels |
| 7. Multi-seed recovery | Test recovery under repeated seeds | 10-seed paired recovery suites | recovered success improves from 0/10 to 9/10 or 10/10 for key faults | scripted/oracle components |
| 8. Learned route classifier | Learn route prediction from features | safety-biased classifier | accuracy 0.846, macro-F1 0.828, missed review-or-abort 0.000 | labels are distilled |
| 9. Observable supervisor | Reduce privileged-state dependence | observable jaw-stuck risk signals | detects 10/10 jaw-stuck perturbations on two tasks | recovery remains scripted |
| 10. Embedding-risk PPO | Feed instability analysis into training | reward shaping and hard-negative curriculum | improves return and strict final distance, not robust success | preliminary training result |

## 4. Stage-by-Stage Explanation

### Stage 1: Custom Constrained Surgical Proxy

**What was done.** A lightweight 3D surgical-tool navigation environment was
built. It includes a tool position, target position, forbidden region, force
proxy, and per-episode safety budget.

**Why it was done.** SurRoL experiments are heavier and slower. The proxy makes
it possible to quickly test controller ideas such as backup actions, risk
gates, and safety-budget supervision.

**What it shows.** The proxy creates a controlled setting where safety-control
logic can be tested before moving to richer surgical simulation.

**Limitation.** It is not a realistic surgical environment. Its value is fast
method development, not direct surgical validation.

### Stage 2: Tangent Backup Controller

**What was done.** A tangent backup controller was implemented. When the policy
action risks entering a forbidden region, the controller steers around the
boundary rather than simply stopping.

**Why it was done.** In surgical manipulation, stopping may be safe but can
stall the task; pushing directly away may be inefficient. Tangential correction
models the idea of moving along a safety boundary.

**Evidence.** Always-tangent backup reaches 0.000 budget exhaustion in both
prototype and strict proxy settings.

**Limitation.** Always-on tangent backup over-intervenes because it is available
at every timestep.

### Stage 3: Risk-Gated Tangent Backup

**What was done.** A risk gate was placed before tangent backup. It checks
interpretable risk features before allowing the backup controller to activate.

Risk reasons include:

- proposed forbidden-zone proximity;
- current clearance;
- force proxy;
- remaining budget;
- stalled progress;
- large action magnitude.

**Why it was done.** This turns reliability analysis from a post-hoc
explanation into a runtime decision signal.

**Evidence.**

| Preset | Method | Budget exhaustion | Supervisor activation |
|---|---|---:|---:|
| prototype | always tangent | 0.000 | 1.000 |
| prototype | risk-gated tangent | 0.000 | 0.450 |
| strict | always tangent | 0.000 | 1.000 |
| strict | risk-gated tangent | 0.000 | 0.426 |

**Interpretation.** Risk-gated tangent preserves always-tangent safety while
cutting supervisor activation by roughly half.

**Limitation.** It still collapses different risk mechanisms into one gate.

### Stage 4: Mechanism-Routed Tangent Backup

**What was done.** The risk gate was upgraded into an ECG-inspired two-stage
mechanism router.

Stage 1 handles boundary risks:

- forbidden-zone risk;
- workspace boundary risk;
- force/contact proxy risk.

Stage 2 logs residual mechanisms:

- low remaining budget;
- stalled progress;
- late failure to approach the goal;
- large or abnormal action.

**Why it was done.** This matches the VT/VF ECG project's stronger reliability
standard: do not compress all uncertainty into one score; separate the failure
mechanism and route accordingly.

**Evidence.**

| Preset | Method | Budget exhaustion | Supervisor activation | Non-correction activation |
|---|---|---:|---:|---:|
| prototype | risk-gated tangent | 0.000 | 0.450 | 0.027 |
| prototype | mechanism-routed tangent | 0.000 | 0.443 | 0.020 |
| strict | risk-gated tangent | 0.000 | 0.426 | 0.030 |
| strict | mechanism-routed tangent | 0.000 | 0.416 | 0.021 |

**Interpretation.** The numerical improvement is modest, but the structure is
stronger: the supervisor now reports why it intervened and which mechanism was
responsible.

**Limitation.** Stage 2 currently records residual review evidence; it does not
yet trigger a separate learned recovery policy.

### Stage 5: SurRoL Migration

**What was done.** The reliability-supervision idea was migrated into
SurRoL/PyBullet surgical simulation tasks:

- `NeedleReach`;
- `NeedlePick`;
- `GauzeRetrieve`.

**Why it was done.** The proxy proves controller logic, but the project needs
visual surgical simulation evidence to show that the idea is not only a toy
environment.

**Evidence.** The repository includes rendered GIF/MP4 rollouts, selected frame
PNGs, and CSV traces under `reports/media/surrol_render_evidence/`.

**Limitation.** SurRoL evidence is still simulation evidence and does not imply
real-robot readiness.

### Stage 6: Fault Taxonomy and Four Routes

**What was done.** Failures were organized into a formal route taxonomy:

| Failure family | Route |
|---|---|
| nominal execution | `auto_execute` |
| reversible execution drift | `auto_recovery` |
| grasp/contact uncertainty | `human_review` |
| visual-state error | `human_review` |
| near-target unsafe recovery | `abort_candidate` |

**Why it was done.** Without a taxonomy, the project becomes a list of unrelated
failures. With a taxonomy, every failure has a reason and a runtime response.

**Evidence.** The taxonomy is documented in
`reports/surrol_fault_taxonomy_step2.md` and
`reports/tables/surrol_fault_taxonomy.csv`.

**Limitation.** The route labels are engineered from current experiments; they
are not independent clinical or expert annotations.

### Stage 7: Multi-Seed SurRoL Recovery

**What was done.** Key recovery tests were run with 10 seeds on `NeedlePick` and
`GauzeRetrieve`.

**Evidence.**

| Task family | Perturbed success | Recovered success |
|---|---:|---:|
| action noise/dropout/slip | 0/10 | 9/10 or 10/10 |
| perception bias/depth scale error | 0/10 | 10/10 |
| jaw-stuck open | 0/10 | 10/10 |

**Interpretation.** The project shows that route-specific recovery can improve
simulated rollouts under several injected fault families.

**Limitation.** Recovery uses scripted/oracle task primitives in parts of the
harness, so this is not proof of learned autonomous recovery.

### Stage 8: Learned Route Classifier

**What was done.** A learned route classifier was trained to predict whether an
episode should be routed to execute, recover, review, or abort candidate.

**Evidence.**

| Metric | Value |
|---|---:|
| held-out episodes | 460 |
| accuracy | 0.846 |
| macro-F1 | 0.828 |
| missed review-or-abort rate | 0.000 |
| false review-or-abort rate | 0.162 |

**Interpretation.** Route prediction is learnable in the current setup, and the
classifier is safety-biased: it avoids missing review-or-abort cases in the
held-out split.

**Limitation.** The labels are distilled from the current routing system. This
does not replace expert labels.

### Stage 9: Observable Supervisor

**What was done.** The jaw-stuck recovery decision was moved away from direct
privileged phase/contact checks toward observable command/progress signals.

**Evidence.** At threshold 3.0, the observable risk score detects 10/10
jaw-stuck perturbed episodes for both `NeedlePick` and `GauzeRetrieve`, with
0/10 nominal monitor-corrected alarms in current logs.

**Interpretation.** The supervisor can reduce dependence on privileged internal
simulator state for the decision trigger.

**Limitation.** The executed recovery primitive still uses scripted SurRoL
waypoint regeneration.

### Stage 10: Embedding-Risk Training Pilot

**What was done.** Embedding/KNN instability analysis was connected back into
PPO training through:

- reward penalties;
- hard-negative curriculum reset;
- two-stage curriculum fine-tuning.

**Evidence.** A three-seed follow-up shows that curriculum fine-tuning improves
mean return and strict final distance, but not success rate or budget
exhaustion.

**Interpretation.** Embedding risk is no longer just an explanation method; it
can affect training behavior.

**Limitation.** It is not yet a reliable model-improvement method.

## 5. Explanation of the Main Innovation

The project's main idea is not "make the policy bigger". It is:

> Build a runtime reliability layer that identifies failure mechanisms and
> routes each situation to an appropriate action.

This is why the project includes both controller-level work and SurRoL recovery
work. They are connected by the same reliability-supervision question.

The ECG-inspired upgrade makes this clearer. Instead of a single total risk
score, the system now separates:

- boundary safety risk;
- residual mechanism risk;
- visual-state uncertainty;
- grasp/contact uncertainty;
- action drift;
- unsafe recovery candidates.

This is the same type of conceptual upgrade as the VT/VF ECG project: reliability
analysis becomes a structured decision system, not just a diagnostic plot.

## 6. What Is Strong, What Is Preliminary

### Stronger Evidence

- Risk-gated tangent preserves 0.000 budget exhaustion while reducing
  supervisor activation.
- Mechanism-routed tangent preserves the same safety while improving
  interpretability and slightly reducing unnecessary activation.
- SurRoL recovery has 10-seed evidence for several injected fault families.
- The learned route classifier has a held-out evaluation split.
- The observable supervisor reduces privileged-state dependence for jaw-stuck
  detection.

### Preliminary Evidence

- Embedding-risk curriculum training changes behavior and improves some metrics,
  but not robust success/safety outcomes.
- Mechanism-routed Stage 2 residual routes are currently logged, not connected
  to a learned residual recovery policy.
- `abort_candidate` remains a low-support route based on geometry proxies.

## 7. What Should Not Be Claimed

The project should not claim:

- real-robot validation;
- clinical validation;
- formal safety guarantees;
- complete end-to-end learned surgical autonomy;
- expert-validated route labels;
- robust policy improvement from embedding-risk training.

The project can claim:

- simulation evidence for runtime reliability supervision;
- interpretable route decisions for different failure mechanisms;
- proxy-controller evidence for risk-gated and mechanism-routed tangent backup;
- SurRoL evidence for route-specific recovery under injected faults;
- preliminary training-loop evidence for embedding-risk signals.

## 8. Recommended Paper/Presentation Wording

**Short version.** We propose a failure-aware runtime reliability supervisor for
simulated surgical robot learning. The system routes uncertain or unsafe
rollouts into automatic execution, automatic recovery, review/re-estimation, or
abort-candidate states. In a custom constrained proxy, risk-gated and
mechanism-routed tangent backup preserve the safety-budget behavior of
always-on tangent correction while substantially reducing unnecessary
supervisor activation. In SurRoL/PyBullet tasks, the same reliability-routing
logic supports multi-seed recovery from injected action, perception, and
jaw-stuck failures. The results are simulation-only and should be interpreted
as internal reliability evidence rather than real-robot validation.

**Plain-language version.** The project is about teaching the robot system to
know when it should not blindly continue. If the problem is small and
recoverable, it can recover automatically. If the visual state or grasp state is
uncertain, it should request review. If recovery may become unsafe, it should
stop or flag the episode. The main contribution is this reliability decision
structure, not just a higher success number.

## 9. Reproducibility Index

| Purpose | Command or file |
|---|---|
| unit tests | `python -m pytest tests\test_tool_navigation.py` |
| risk-gated/mechanism-routed tangent | `scripts\evaluate_risk_gated_tangent.py` |
| SurRoL master results | `scripts\build_surrol_master_results.py` |
| fault taxonomy | `scripts\build_surrol_fault_taxonomy.py` |
| learned route classifier | `scripts\train_surrol_route_classifier.py` |
| observable supervisor | `scripts\analyze_observable_proxy_risk.py`, `scripts\build_surrol_observable_supervisor_step4.py` |
| embedding-risk PPO pilot | `scripts\run_embedding_risk_multiseed_curriculum.py` |
| evidence map | `docs\evidence_index.md` |

## 10. Final Conclusion

The project has developed from a simple safe-control proxy into a structured
reliability-supervision study for surgical robot learning. Its most coherent
story is:

1. build a fast proxy to test safety-control ideas;
2. show that tangent backup can preserve safety budgets;
3. reduce over-intervention with risk gating;
4. upgrade the controller into mechanism-separated reliability routing;
5. migrate the reliability idea into SurRoL tasks;
6. evaluate route-specific recovery under injected failures;
7. learn and audit route decisions;
8. test whether embedding instability can feed back into training.

The current evidence supports a simulation research claim: reliability analysis
can become a runtime decision layer for safer and more explainable surgical RL.
The remaining work is to replace scripted recovery components with learned
recovery policies, validate route labels externally, and test generalization
beyond the current simulation setup.
