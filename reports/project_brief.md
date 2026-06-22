# Constraint-Conditioned RL for Safe Surgical Tool Navigation

## One-Paragraph Takeaway

This prototype studies a simplified surgical tool navigation task where an RL policy receives task phase and safety-budget inputs while avoiding forbidden tissue-like regions. Plain constraint-conditioned PPO improves modestly, but the strongest result comes from adding a tangent backup controller that projects unsafe actions into a local avoidance direction. Across three seeds, tangent-shielded policies reach 1.000 success on the prototype setting with zero budget exhaustion and zero cumulative constraint cost. Strict transfer remains less stable, but tangent-shielded methods still dominate the unshielded baselines on safety metrics.

## Research Question

Can a policy conditioned on task phase and safety budget perform contact-rich surgical-tool navigation while respecting forbidden-region and constraint-budget limits?

## Method

- Base policy: PPO over a compact continuous-control surgical-tool abstraction.
- Conditioning: observation includes task phase and remaining safety budget.
- Safety layer: a tangent backup controller intercepts unsafe actions and redirects them around forbidden regions.
- Comparisons: scratch PPO, curriculum PPO, standard shield, tangent shield, strict-preset transfer, and random-policy sanity checks.

## Prototype Evaluation

| Variant | Success | Budget Exhausted | Cost | Final Distance | Shield Interventions |
|---|---:|---:|---:|---:|---:|
| curriculum_conditioned | 0.287 +/- 0.172 | 0.703 +/- 0.176 | 1.574 +/- 0.290 | 0.448 +/- 0.104 | 0.000 +/- 0.000 |
| curriculum_conditioned_shielded | 0.313 +/- 0.045 | 0.560 +/- 0.028 | 1.193 +/- 0.029 | 0.424 +/- 0.015 | 19.360 +/- 3.125 |
| curriculum_conditioned_tangent_shielded | 1.000 +/- 0.000 | 0.000 +/- 0.000 | 0.000 +/- 0.000 | 0.054 +/- 0.001 | 2.030 +/- 0.029 |
| scratch_conditioned | 0.227 +/- 0.017 | 0.720 +/- 0.045 | 1.567 +/- 0.093 | 0.454 +/- 0.018 | 0.000 +/- 0.000 |
| scratch_conditioned_shielded | 0.313 +/- 0.017 | 0.570 +/- 0.028 | 1.234 +/- 0.049 | 0.430 +/- 0.010 | 22.117 +/- 3.434 |
| scratch_conditioned_tangent_shielded | 1.000 +/- 0.000 | 0.000 +/- 0.000 | 0.000 +/- 0.000 | 0.053 +/- 0.001 | 2.117 +/- 0.103 |

## Strict Transfer Evaluation

| Variant | Success | Budget Exhausted | Cost | Final Distance | Shield Interventions |
|---|---:|---:|---:|---:|---:|
| curriculum_conditioned | 0.110 +/- 0.071 | 0.810 +/- 0.107 | 0.971 +/- 0.109 | 0.623 +/- 0.040 | 0.000 +/- 0.000 |
| curriculum_conditioned_shielded | 0.127 +/- 0.066 | 0.653 +/- 0.005 | 0.718 +/- 0.027 | 0.608 +/- 0.011 | 9.297 +/- 0.346 |
| curriculum_conditioned_tangent_shielded | 0.693 +/- 0.203 | 0.000 +/- 0.000 | 0.000 +/- 0.000 | 0.117 +/- 0.050 | 2.513 +/- 0.033 |
| scratch_conditioned | 0.063 +/- 0.045 | 0.843 +/- 0.081 | 1.004 +/- 0.081 | 0.622 +/- 0.036 | 0.000 +/- 0.000 |
| scratch_conditioned_shielded | 0.133 +/- 0.068 | 0.667 +/- 0.017 | 0.735 +/- 0.034 | 0.603 +/- 0.017 | 9.483 +/- 0.660 |
| scratch_conditioned_tangent_shielded | 0.860 +/- 0.164 | 0.000 +/- 0.000 | 0.000 +/- 0.000 | 0.084 +/- 0.045 | 2.577 +/- 0.065 |

## What Is Shown

- Tangent-shielded variants solve the prototype task with zero observed budget exhaustion over the current three-seed run.
- Standard shield reduces constraint cost but does not solve the reaching task reliably.
- Curriculum helps some unshielded runs, but it is not the dominant effect in the current results.
- A random-policy sanity check with the same tangent shield achieved 0.000 success on prototype episodes, so the backup controller alone is not solving the reaching task.

## What Is Suggested

- A lightweight supervisory controller can make constraint-conditioned RL much more reliable in this abstract surgical setting.
- The strongest application framing is safe surgical tool navigation rather than generic PPO benchmarking.
- The tangent-shield mechanism is a stronger primary contribution than curriculum learning for the current evidence.

## Limitations

- Only three training seeds are reported.
- The environment is an abstract 3D proxy, not yet SurRoL or a high-fidelity surgical simulator.
- Existing pre-upgrade result tables were produced with the earlier 2D environment and should not be mixed with retrained 3D results.
- The tangent shield is strong; future experiments should measure how much action authority it uses and compare against non-RL heuristic controllers.
- Strict transfer has high seed variance, especially for curriculum tangent-shielded models.

## Recommended Next Experiment

Move from this 3D proxy to a SurRoL-inspired needle-reaching or constrained-tool-navigation environment, while keeping the same policy interface and tangent backup controller. Also report intervention rate, action deviation from the policy, and performance under stricter forbidden-volume geometry.

## Paper-Style Claim

Preliminary results in an abstract surgical navigation task suggest that combining constraint-conditioned PPO with a tangent backup controller can substantially reduce constraint violations while preserving task success. These results are promising but remain prototype-level until validated in a higher-fidelity surgical simulator and with additional seeds.
