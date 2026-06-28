# Failure-Aware VPPV Supervisor Brief

## One-Sentence Claim

This project does not try to relearn surgical jaw/gripper mechanics. It adds a
mechanism-aware runtime supervisor around the VPPV-style
perception-policy-servoing loop, so visual-state bias, depth-scale error, and
high-level approach drift are routed to different recovery actions instead of
being treated as one generic failure.

## Pain Point In The Teacher's VPPV Setting

In the local notes and SurRoL/VPPV reading, the learned part is best treated as
a high-level state-to-approach policy supported by visual state estimation and
later servoing/control. The important reliability question is therefore not
whether the jaw can open or close. The question is whether the system can detect
that the state estimate or approach decision has become unreliable before the
tool keeps moving toward the wrong state.

## Mechanism-Specific Routing

| Failure source | Evidence that should rise | Route |
| --- | --- | --- |
| Visual-state estimation bias | visual residual, perception uncertainty, local state mismatch | `reobserve_reestimate` |
| Depth-scale error | depth evidence before visual residual is trusted | `depth_reestimate_or_cautious_approach` |
| Policy approach drift | action-outcome mismatch and policy-proxy instability | `low_gain_correction_or_replan` |
| Nominal execution | no high-risk evidence | `continue` |

## Main Evidence

![Failure-aware VPPV supervisor pack](figures/failure_aware_vppv/failure_aware_vppv_supervisor_pack.png)

### Step-Level Router Ablation

| model | accuracy | macro_f1 | missed_high_risk_step_rate | false_alarm_on_nominal_step_rate | route_diversity |
| --- | --- | --- | --- | --- | --- |
| visual_only | 0.561 | 0.367 | 0.155 | 0.000 | 2 |
| depth_only | 0.561 | 0.381 | 0.578 | 0.000 | 2 |
| policy_only | 0.357 | 0.355 | 0.845 | 0.005 | 2 |
| composite_step_route | 0.999 | 0.998 | 0.000 | 0.005 | 4 |

### Cross-Task Frozen-Threshold Check

| split | rows | threshold_visual | threshold_depth | threshold_policy | threshold_action | macro_f1 | missed_high_risk_step_rate | false_alarm_on_continue_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| test_on_GauzeRetrieve | 5365 | 0.450 | 0.450 | 0.350 | 0.450 | 1.000 | 0.000 | 0.000 |
| test_on_NeedlePick | 5362 | 0.450 | 0.450 | 0.350 | 0.250 | 0.996 | 0.000 | 0.009 |

### Severity-Held-Out Check

| model | rows | seeds_total | macro_f1 | missed_intervention_rate | false_intervention_rate | route_diversity |
| --- | --- | --- | --- | --- | --- | --- |
| boundary_router | 6 | 30 | 1.000 | 0.000 | 0.000 | 3 |
| family_only | 6 | 30 | 1.000 | 0.000 | 0.000 | 3 |
| uniform_retry | 6 | 30 | 0.167 | 0.000 | 0.000 | 1 |

### Mixed-Perturbation Priority Check

| model | rows | scenarios | macro_f1 | missed_intervention_rate | wrong_priority_rate | route_diversity |
| --- | --- | --- | --- | --- | --- | --- |
| priority_router | 1440 | 8 | 1.000 | 0.000 | 0.000 | 2 |
| max_signal_router | 1440 | 8 | 0.033 | 0.000 | 0.949 | 2 |
| uniform_retry | 1440 | 8 | 0.000 | 0.000 | 1.000 | 1 |
| single_score_retry | 1440 | 8 | 0.000 | 0.250 | 1.000 | 2 |

### True Mixed-Fault SurRoL Rollouts

| task | failure_combo | episodes | seeds | perturbed_success | priority_routed_success | perturbed_final_distance | priority_routed_final_distance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GauzeRetrieve | depth_scale_error+near_target_drift | 5 | 5 | 0.000 | 1.000 | 0.258 | 0.013 |
| GauzeRetrieve | perception_bias+depth_scale_error | 5 | 5 | 0.000 | 1.000 | 0.258 | 0.013 |
| GauzeRetrieve | perception_bias+depth_scale_error+near_target_drift | 5 | 5 | 0.000 | 1.000 | 0.258 | 0.013 |
| GauzeRetrieve | perception_bias+near_target_drift | 5 | 5 | 0.000 | 1.000 | 0.259 | 0.013 |
| NeedlePick | depth_scale_error+near_target_drift | 5 | 5 | 0.000 | 1.000 | 0.190 | 0.021 |
| NeedlePick | perception_bias+depth_scale_error | 5 | 5 | 0.000 | 1.000 | 0.187 | 0.019 |
| NeedlePick | perception_bias+depth_scale_error+near_target_drift | 5 | 5 | 0.000 | 1.000 | 0.187 | 0.021 |
| NeedlePick | perception_bias+near_target_drift | 5 | 5 | 0.000 | 1.000 | 0.198 | 0.021 |

### Early Warning Summary

| mechanism | episodes | alert_rate | false_alert_rate | median_lead_time |
| --- | --- | --- | --- | --- |
| depth_scale_error | 20 | 1.000 | 0.000 | 179.000 |
| nominal | 25 | 0.000 | 0.000 |  |
| policy_approach_drift | 20 | 1.000 | 0.000 | 3.500 |
| visual_estimation_bias | 20 | 1.000 | 0.000 | 179.000 |

## Interpretation

The useful result is not just that a score becomes high after a fault. Single
evidence families are incomplete: visual-only, depth-only, and policy-only
routes miss different high-risk steps. The composite router uses mechanism
order: depth is checked before visual residuals, and policy drift is routed
through action-outcome/policy-proxy evidence. This is why the method is closer
to the ECG project's error-mechanism analysis than to a retry-after-failure
controller.

The cross-task check is a stronger internal test than within-task consistency:
thresholds are calibrated on one SurRoL task and frozen when evaluating the
other. Current results show macro-F1 of 1.000 from NeedlePick to GauzeRetrieve
and 0.996 from GauzeRetrieve to NeedlePick, with no missed high-risk steps
under the simulator-derived weak labels.

The severity-held-out check uses low/medium severity conditions to learn
intervention boundaries, then evaluates high severity without recalibrating.
This is a small 30-seed aggregate check, but it shows why uniform retry is the
wrong framing: high-severity visual/depth state errors require re-estimation or
review, while near-target drift can route to low-gain correction or replan.

The mixed-perturbation priority check is an offline compositional stress test,
not a new mixed-fault rollout. Its role is to test route ordering when evidence
families co-activate. It shows that a max-score or generic retry rule can pick
the wrong mechanism, while the priority router preserves `depth -> visual ->
policy` routing.

The true mixed-fault rollout then executes the mixed proxies in SurRoL/PyBullet.
In the current 5-seed smoke-scale run, perturbed mixed
cases are 0/40 success and
priority-routed cases are 40/40
success, which is stronger evidence than the offline composition audit but
still scripted-oracle simulation evidence.

## Scope Boundary

This is simulation evidence. The labels are derived from injected faults and
routing rules, not independent surgeon annotation. The current claim is
therefore: mechanism-aware reliability supervision is plausible and measurable
around VPPV-style surgical simulation, not that the system is clinically
validated or ready for hardware autonomy.

## Next Validation Step

The next strongest experiment is to scale the true mixed-fault run to more
seeds and add learned-policy or image-corruption conditions, then compare the
same priority router against a non-oracle VPPV policy path.

