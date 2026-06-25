# SurRoL Fault Taxonomy And Intervention Routing

## Takeaway

The SurRoL prototype organizes failures into a small runtime-reliability taxonomy rather than treating every failure as a generic control disturbance. Reversible action/execution faults are routed to automatic recovery, visual-state errors are routed to review/re-estimation, and silent grasp-contact faults are handled by observable grasp retry or human-review style routing. This is still a simulation-only research prototype; the current routes are rule/proxy based and should not be described as clinical or real-robot validation.

## Route Definitions

| Route | Meaning | Current Evidence |
|---|---|---|
| `auto_execute` | Continue nominal execution | clean/no-alarm SurRoL rollouts remain successful |
| `auto_recovery` | Try bounded automatic recovery | action noise/dropout/slip/freeze and near-target drift |
| `human_review` | Stop blind recovery and request review/re-estimation | visual-state errors and uncertain grasp outcomes |
| `abort_candidate` | Candidate for stopping recovery under irreversible risk | only a geometric danger-zone proxy so far |

## Evidence Table

| Fault Family | Task | Failure | Intended Route | Observed Route | Seeds | Perturbed | Recovered | Limitation |
|---|---|---|---|---|---:|---:|---:|---|
| grasp_contact_uncertainty | GauzeRetrieve | jaw_stuck_open | `human_review_or_observable_grasp_retry` | `human_review` | 10 | 0.000 | 1.000 | Observable proxy works, but the retry primitive still calls SurRoL task logic. |
| grasp_contact_uncertainty | NeedlePick | jaw_stuck_open | `human_review_or_observable_grasp_retry` | `human_review` | 10 | 0.000 | 1.000 | Observable proxy works, but the retry primitive still calls SurRoL task logic. |
| near_target_recovery_risk | GauzeRetrieve | near_target_drift | `auto_recovery` | `auto_recovery` | 5 | 0.000 | 1.000 | Unsafe-zone routing is still geometric, not force/tissue-damage based. |
| near_target_recovery_risk | NeedlePick | near_target_drift | `auto_recovery` | `auto_recovery` | 5 | 0.200 | 1.000 | Unsafe-zone routing is still geometric, not force/tissue-damage based. |
| nominal_execution | GauzeRetrieve | none | `auto_execute` | `auto_execute` | 10 |  | 1.000 | This is a specificity check rather than a failure case. |
| nominal_execution | NeedlePick | none | `auto_execute` | `auto_execute` | 10 |  | 1.000 | This is a specificity check rather than a failure case. |
| nominal_execution | NeedleReach | none | `auto_execute` | `auto_execute` | 5 |  | 1.000 | This is a specificity check rather than a failure case. |
| reversible_execution_drift | GauzeRetrieve | action_dropout | `auto_recovery` | `auto_recovery` | 10 | 0.000 | 1.000 | Current recovery still uses simulator task primitives. |
| reversible_execution_drift | GauzeRetrieve | action_noise | `auto_recovery` | `auto_recovery` | 10 | 0.000 | 1.000 | Current recovery still uses simulator task primitives. |
| reversible_execution_drift | GauzeRetrieve | execution_slip | `auto_recovery` | `auto_recovery` | 10 | 0.000 | 1.000 | Slip is synthetic and should not be presented as real actuator validation. |
| reversible_execution_drift | NeedlePick | action_dropout | `auto_recovery` | `auto_recovery` | 10 | 0.000 | 1.000 | Current recovery still uses simulator task primitives. |
| reversible_execution_drift | NeedlePick | action_noise | `auto_recovery` | `auto_recovery` | 10 | 0.000 | 0.900 | NeedlePick has one remaining 10-seed failure case under action noise. |
| reversible_execution_drift | NeedlePick | execution_slip | `auto_recovery` | `auto_recovery` | 10 | 0.000 | 1.000 | Slip is synthetic and should not be presented as real actuator validation. |
| reversible_execution_drift | NeedleReach | action_freeze | `auto_recovery` | `auto_recovery` | 5 | 0.000 | 1.000 | NeedleReach is a simpler reach task, not a full complex manipulation benchmark. |
| visual_state_error | GauzeRetrieve | depth_scale_error | `human_review_reestimate` | `human_review` | 10 | 0.000 | 1.000 | Re-estimation currently uses a clean simulator-state proxy, not a calibrated vision model. |
| visual_state_error | GauzeRetrieve | perception_bias | `human_review_reestimate` | `human_review` | 10 | 0.000 | 1.000 | Re-estimation currently uses a clean simulator-state proxy, not a real perception rerun. |
| visual_state_error | NeedlePick | depth_scale_error | `human_review_reestimate` | `human_review` | 10 | 0.000 | 1.000 | Re-estimation currently uses a clean simulator-state proxy, not a calibrated vision model. |
| visual_state_error | NeedlePick | perception_bias | `human_review_reestimate` | `human_review` | 10 | 0.000 | 1.000 | Re-estimation currently uses a clean simulator-state proxy, not a real perception rerun. |

## What Is Shown

- The standard action-corruption suite now has 10-seed evidence on NeedlePick and GauzeRetrieve.
- Visual-state errors now have 10-seed review/re-estimation evidence on both core tasks.
- Observable jaw-stuck recovery already has 10-seed evidence on both core tasks.
- The taxonomy separates recoverable execution drift from failures that should be reviewed or re-estimated.

## What Remains Unproven

- The routing policy is not yet a fully learned calibrated risk classifier.
- `abort_candidate` remains weak because current evidence uses a danger-zone proxy with low support.
- Several recovery primitives still use SurRoL task logic; Step 4 should reduce privileged simulator-state dependence.
- No real-robot, clinical, or sim-to-real claim is supported.

## Summary Claim

The SurRoL migration is formalized as a runtime-reliability taxonomy:
reversible execution drift is routed to bounded automatic recovery,
visual-state errors are routed to review/re-estimation, and grasp-contact
uncertainty is handled through observable retry or human-review style routing.
In 10-seed SurRoL pilots, the system restores most injected failures from zero
perturbed success to successful monitor-corrected execution, while retaining
clear limitations around learned risk calibration and privileged simulator
primitives.
