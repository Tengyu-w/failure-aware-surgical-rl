# Teacher-Facing Experiment Process

This document explains the project in the order a supervisor should read it.
The main point is not that the repository adds many isolated surgical actions.
The main point is that a simple RL proxy is used to define a reliability
problem, then an ECG-style error-mechanism analysis is migrated into
SurRoL/VPPV-style surgical simulation.

## 1. What The Project Is Actually About

The project studies runtime reliability supervision for simulated surgical
robot learning.

The target setting is a VPPV/RL-style pipeline where the policy can move the
tool toward an estimated target. The important failure is not mainly "the jaw
open/close action was learned incorrectly." The more useful problem is:

- the visual-state estimate may be biased;
- depth may be mis-scaled;
- the high-level approach policy may drift toward the wrong local target;
- the near-target servoing handoff may continue after the state becomes
  unreliable;
- recovery itself may be unsafe if it blindly continues.

So the project asks:

> Can the system identify which mechanism caused unreliable execution, then
> route to re-estimation, cautious approach, low-gain correction, review, or
> abort-candidate behavior instead of treating every failure as retry?

## 2. Why The Project Starts With A Small Proxy

The first environment is a controlled CircleRL-style surgical-tool proxy. It is
not claimed to be realistic surgery. It is used because the reliability problem
can be isolated cleanly:

- the tool must move from a start state to a target;
- it must avoid a forbidden region;
- the rollout has force/contact proxies, workspace limits, and a safety budget;
- PPO learns continuous motion from simulator reward;
- injected faults can bias the target, drop state, slip execution, or move the
  tool toward unsafe geometry.

This proxy establishes the first project idea:

```text
policy action
  -> runtime evidence
  -> route decision
  -> execute, recover, review, or abort-candidate
```

The proxy result is not "this is a surgical robot." The result is that the
project can convert a generic failure into interpretable mechanism evidence:
boundary risk, progress stall, state-estimation error, action-outcome mismatch,
and safety-budget exhaustion.

## 3. How The ECG Project Is Migrated Into RL

The ECG project is useful because it does not stop at embedding visualization.
It studies multiple reliability signals and maps different error mechanisms to
different interventions.

This project transfers that style into robot rollouts:

| ECG-style idea | Surgical RL translation |
| --- | --- |
| representation geometry | route-space embeddings, centroid/prototype/KNN diagnostics |
| uncertainty | MSP, entropy, margin, review-score evidence |
| perturbation robustness | action noise, dropout, perception bias, depth error, near-target drift |
| mechanism labels | visual-state, depth, policy drift, action-outcome mismatch, unsafe continuation |
| selective routing | continue, recover, review/re-estimate, abort-candidate |

This is why the project moves beyond "embedding analysis." It builds a
multi-evidence reliability suite and then uses those signals as a routing layer
around the policy.

## 4. Why SurRoL/VPPV Changes The Focus

After reading the SurRoL/VPPV setup, the project focus becomes more precise.
The low-level jaw or gripper behavior is not the central learned contribution
we should claim. In this setting, the relevant learned or policy-like component
is closer to visual-state estimation and high-level movement toward a target,
with later servoing/control handling the final execution details.

Therefore the final project does not claim:

- "we learned all surgical grasping actions";
- "we fixed the teacher's low-level gripper controller";
- "we trained a real surgical policy from clinical demonstrations."

The final project does claim:

- "we built a mechanism-specific reliability supervisor around VPPV-style
  target approach";
- "we can separate visual bias, depth error, policy drift, action mismatch, and
  unsafe continuation";
- "under injected simulator faults, the route-specific response is more
  informative than retrying every failure."

## 5. Final Evidence Ladder

The final evidence package is deliberately layered. Each stage answers a
different question.

| Stage | Question | Result |
| --- | --- | --- |
| Step-level evidence | Can individual timestep evidence identify the mechanism? | 10,823 rows; composite route macro-F1 0.998; missed high-risk 0.000 |
| Single-evidence ablation | Is one evidence family enough? | visual 0.367, depth 0.381, policy 0.355, single-score 0.131 macro-F1 |
| Cross-task transfer | Do thresholds transfer between NeedlePick and GauzeRetrieve? | macro-F1 1.000 and 0.996 with frozen thresholds |
| Severity holdout | Do low/medium boundaries survive held-out high severity? | boundary router 1.000 macro-F1; uniform retry 0.167 |
| Mixed-priority audit | What if visual/depth/policy evidence co-activate? | priority router 1.000 macro-F1; max-signal 0.033; uniform retry 0.000 |
| True mixed rollouts | Does routing still work when mixed faults execute in PyBullet? | perturbed 0/40 success; priority-routed 40/40 success |

The strongest current evidence is the 5-seed true mixed-fault SurRoL smoke
test:

```text
2 tasks
4 mixed fault combinations
5 seeds per task/fault/controller cell
40 episodes per controller

clean:           40/40 success, mean final distance 0.015
perturbed:        0/40 success, mean final distance 0.224
priority-routed: 40/40 success, mean final distance 0.016
```

## 6. What The Router Actually Does

The composite route is priority-based rather than retry-based:

```text
runtime evidence
  -> depth evidence?
       -> depth_reestimate_or_cautious_approach
  -> visual-state evidence?
       -> reobserve_reestimate
  -> policy/action-outcome drift?
       -> low_gain_correction_or_replan
  -> unsafe continuation?
       -> abort_candidate
  -> otherwise
       -> continue
```

This matters because a max-score rule can pick the largest signal rather than
the safest causal mechanism. For example, a depth-scale error may create visual
residuals, but the route should still prioritize depth re-estimation before
trusting the visual residual.

## 7. What A Supervisor Should Take Away

The project's cleanest positioning is:

> Failure-aware VPPV routing: an ECG-inspired, multi-evidence reliability
> supervisor that identifies visual-state, depth, policy-approach, and unsafe
> continuation mechanisms in simulated surgical robot rollouts, then routes
> recovery or review accordingly.

This is stronger and more accurate than saying the project simply adds grasping
actions or repeats failed attempts.

The key contribution is the mechanism mapping:

| Failure mechanism | Evidence | Route |
| --- | --- | --- |
| visual-state bias | residual state mismatch and visual evidence | reobserve / re-estimate |
| depth-scale error | depth evidence and corrupted z behavior | depth re-estimate / cautious approach |
| policy approach drift | action-outcome mismatch and progress loss | low-gain correction / replan |
| compound visual-depth-policy faults | co-active evidence | priority route: depth before visual before policy |
| unsafe recovery | risk remains high during correction | abort-candidate or review |

## 8. What Remains Unproven

The repository is careful about the boundary:

- It is simulator-only.
- The labels are weak labels from injected faults and routing rules.
- The true mixed rollout is scripted-oracle PyBullet evidence.
- It is not hardware validation.
- It is not clinical validation.
- It is not an end-to-end learned surgical autonomy system.
- It has not yet replaced the scripted route with the teacher's original
  learned VPPV policy path.

## 9. Where To Read The Evidence

- Final teacher brief:
  [reports/failure_aware_vppv_final_teacher_brief.md](../reports/failure_aware_vppv_final_teacher_brief.md)
- Evidence matrix:
  [reports/tables/failure_aware_vppv_final_evidence_matrix.csv](../reports/tables/failure_aware_vppv_final_evidence_matrix.csv)
- True mixed rollout report:
  [reports/failure_aware_vppv_true_mixed_rollouts.md](../reports/failure_aware_vppv_true_mixed_rollouts.md)
- VPPV multi-evidence framework:
  [docs/FAILURE_AWARE_VPPV_MULTIEVIDENCE_FRAMEWORK.md](FAILURE_AWARE_VPPV_MULTIEVIDENCE_FRAMEWORK.md)
- Claim-to-evidence index:
  [docs/evidence_index.md](evidence_index.md)

