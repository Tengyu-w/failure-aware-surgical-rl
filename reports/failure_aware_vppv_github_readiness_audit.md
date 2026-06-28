# Failure-Aware VPPV GitHub Readiness Audit

## Overall Status

**Ready as a research-prototype evidence package, with explicit scope
limitations.** The repository now has a coherent VPPV-specific story, traceable
tables, figures, scripts, and a final evidence matrix.

## Checks

| Area | Status | Notes |
|---|---|---|
| Entry framing | PASS | README and docs explain that this is runtime reliability supervision, not clinical autonomy. |
| VPPV relevance | PASS | The final framing targets visual-state estimation, high-level approach policy, near-target handoff, and unsafe continuation. |
| Evidence traceability | PASS | Each major claim links to a report, CSV table, figure, and rebuild command. |
| Mechanism specificity | PASS | Step, cross-task, severity, mixed-priority, and true-rollout evidence all preserve visual/depth/policy route distinctions. |
| Claim calibration | PASS | Current reports state simulator-only, weak-label, and scripted-oracle limitations. |
| Reproducibility | PASS WITH WATCH | Rebuild scripts exist; true SurRoL rollout still depends on local SurRoL/PyBullet environment setup. |
| Visual evidence | PASS WITH WATCH | Figures and recovery media exist; the strongest VPPV result is figure/table based, not a polished learned-policy video. |
| Statistical maturity | NEEDS WATCH | True mixed rollouts are 40 episodes per controller; scale seeds before stronger claims. |

## Evidence Files To Highlight

- `reports/failure_aware_vppv_final_teacher_brief.md`
- `reports/tables/failure_aware_vppv_final_evidence_matrix.csv`
- `reports/failure_aware_vppv_true_mixed_rollouts.md`
- `reports/tables/failure_aware_vppv_true_mixed_rollout_paired.csv`
- `reports/figures/failure_aware_vppv/failure_aware_vppv_true_mixed_success.png`
- `reports/failure_aware_vppv_step_evidence.md`
- `reports/failure_aware_vppv_cross_task_generalization.md`
- `reports/failure_aware_vppv_severity_holdout.md`
- `reports/failure_aware_vppv_mixed_perturbation_priority.md`
- `reports/failure_aware_vppv_model_derived_routing.md`

## Claims That Are Safe To Make

- The project implements a mechanism-specific runtime router for simulated
  VPPV-style surgical manipulation failures.
- In weak-label step evidence, composite routing reaches macro-F1
  0.998 over 10823 rows and
  outperforms single-family evidence.
- Frozen thresholds transfer between NeedlePick and GauzeRetrieve with
  macro-F1 1.000 and
  0.996.
- Model-derived route assignment reaches held-out macro-F1
  0.995 over
  3351 step rows without using mechanism labels
  to form the route clusters.
- In smoke-scale true mixed SurRoL rollouts, priority routing recovers
  40/40 cases while the perturbed controller recovers
  0/40.

## Claims To Avoid

- Do not claim real surgical safety.
- Do not claim clinical validation.
- Do not claim the VPPV low-level gripper action policy was retrained or fixed.
- Do not claim independent expert labels.
- Do not claim the true mixed rollout proves end-to-end learned autonomy.

## Remaining Cleanup Before A Public Push

- Keep `scripts/run_surrol_ppo_failure_aware.ps1` separate if it contains
  unrelated local edits.
- Make sure generated files are intentionally added together so the evidence
  package is not half-committed.
- If time allows, rerun true mixed rollouts with more seeds and regenerate this
  package.
