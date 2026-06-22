# Expanded Stress Transfer Suite

This report evaluates trained prototype policies across additional surgical-proxy and stress presets.

## Preset-Level Tables

### gauze_manipulation_proxy

| Variant | Success | Budget Exhausted | Cost | Final Distance | Shield Interventions |
|---|---:|---:|---:|---:|---:|
| curriculum_conditioned | 0.347 | 0.600 | 1.319 | 0.442 | 0.000 |
| curriculum_conditioned_shielded | 0.420 | 0.413 | 0.820 | 0.396 | 14.777 |
| curriculum_conditioned_tangent_shielded | 1.000 | 0.000 | 0.000 | 0.065 | 1.983 |
| scratch_conditioned | 0.293 | 0.630 | 1.357 | 0.446 | 0.000 |
| scratch_conditioned_shielded | 0.490 | 0.427 | 0.857 | 0.379 | 14.530 |
| scratch_conditioned_tangent_shielded | 1.000 | 0.000 | 0.000 | 0.064 | 2.003 |

### needle_insert

| Variant | Success | Budget Exhausted | Cost | Final Distance | Shield Interventions |
|---|---:|---:|---:|---:|---:|
| curriculum_conditioned | 0.150 | 0.740 | 0.906 | 0.563 | 0.000 |
| curriculum_conditioned_shielded | 0.227 | 0.600 | 0.685 | 0.522 | 6.430 |
| curriculum_conditioned_tangent_shielded | 0.880 | 0.000 | 0.000 | 0.058 | 2.530 |
| scratch_conditioned | 0.057 | 0.800 | 0.974 | 0.566 | 0.000 |
| scratch_conditioned_shielded | 0.190 | 0.607 | 0.683 | 0.525 | 6.697 |
| scratch_conditioned_tangent_shielded | 0.953 | 0.000 | 0.000 | 0.043 | 2.537 |

### needle_reach

| Variant | Success | Budget Exhausted | Cost | Final Distance | Shield Interventions |
|---|---:|---:|---:|---:|---:|
| curriculum_conditioned | 0.220 | 0.687 | 0.943 | 0.500 | 0.000 |
| curriculum_conditioned_shielded | 0.313 | 0.510 | 0.646 | 0.437 | 7.780 |
| curriculum_conditioned_tangent_shielded | 0.937 | 0.000 | 0.000 | 0.052 | 1.830 |
| scratch_conditioned | 0.123 | 0.700 | 0.960 | 0.496 | 0.000 |
| scratch_conditioned_shielded | 0.280 | 0.517 | 0.647 | 0.441 | 7.427 |
| scratch_conditioned_tangent_shielded | 0.967 | 0.000 | 0.000 | 0.046 | 1.840 |

### needle_regrasp_proxy

| Variant | Success | Budget Exhausted | Cost | Final Distance | Shield Interventions |
|---|---:|---:|---:|---:|---:|
| conditioned | 0.000 | 1.000 | 1.476 | 0.656 | 0.000 |
| conditioned_shielded | 0.383 | 0.300 | 0.351 | 0.301 | 0.933 |
| conditioned_tangent_shielded | 0.800 | 0.000 | 0.000 | 0.067 | 1.300 |
| no_phase_budget | 0.017 | 0.950 | 1.401 | 0.946 | 0.000 |

### peg_transfer_proxy

| Variant | Success | Budget Exhausted | Cost | Final Distance | Shield Interventions |
|---|---:|---:|---:|---:|---:|
| conditioned | 0.000 | 1.000 | 1.596 | 0.701 | 0.000 |
| conditioned_shielded | 0.450 | 0.367 | 0.448 | 0.351 | 1.550 |
| conditioned_tangent_shielded | 0.933 | 0.000 | 0.000 | 0.053 | 1.700 |
| no_phase_budget | 0.000 | 0.983 | 1.564 | 0.994 | 0.000 |

### prototype

| Variant | Success | Budget Exhausted | Cost | Final Distance | Shield Interventions |
|---|---:|---:|---:|---:|---:|
| curriculum_conditioned | 0.340 | 0.660 | 1.467 | 0.443 | 0.000 |
| curriculum_conditioned_shielded | 0.397 | 0.490 | 1.040 | 0.386 | 12.753 |
| curriculum_conditioned_tangent_shielded | 1.000 | 0.000 | 0.000 | 0.053 | 1.873 |
| scratch_conditioned | 0.297 | 0.673 | 1.474 | 0.445 | 0.000 |
| scratch_conditioned_shielded | 0.440 | 0.493 | 1.054 | 0.377 | 12.317 |
| scratch_conditioned_tangent_shielded | 1.000 | 0.000 | 0.000 | 0.052 | 1.897 |

### strict

| Variant | Success | Budget Exhausted | Cost | Final Distance | Shield Interventions |
|---|---:|---:|---:|---:|---:|
| curriculum_conditioned | 0.110 | 0.780 | 0.931 | 0.609 | 0.000 |
| curriculum_conditioned_shielded | 0.177 | 0.607 | 0.677 | 0.580 | 5.460 |
| curriculum_conditioned_tangent_shielded | 0.660 | 0.000 | 0.000 | 0.125 | 2.250 |
| scratch_conditioned | 0.073 | 0.823 | 0.976 | 0.600 | 0.000 |
| scratch_conditioned_shielded | 0.197 | 0.617 | 0.667 | 0.575 | 5.270 |
| scratch_conditioned_tangent_shielded | 0.877 | 0.000 | 0.000 | 0.080 | 2.260 |

### tight_corridor

| Variant | Success | Budget Exhausted | Cost | Final Distance | Shield Interventions |
|---|---:|---:|---:|---:|---:|
| curriculum_conditioned | 0.090 | 0.877 | 1.061 | 0.699 | 0.000 |
| curriculum_conditioned_shielded | 0.133 | 0.787 | 0.904 | 0.689 | 8.260 |
| curriculum_conditioned_tangent_shielded | 0.967 | 0.000 | 0.000 | 0.053 | 3.550 |
| scratch_conditioned | 0.053 | 0.910 | 1.097 | 0.704 | 0.000 |
| scratch_conditioned_shielded | 0.113 | 0.803 | 0.917 | 0.690 | 7.853 |
| scratch_conditioned_tangent_shielded | 0.987 | 0.000 | 0.000 | 0.049 | 3.577 |

### tissue_retraction_proxy

| Variant | Success | Budget Exhausted | Cost | Final Distance | Shield Interventions |
|---|---:|---:|---:|---:|---:|
| curriculum_conditioned | 0.197 | 0.800 | 1.245 | 0.508 | 0.000 |
| curriculum_conditioned_shielded | 0.230 | 0.677 | 1.059 | 0.484 | 18.280 |
| curriculum_conditioned_tangent_shielded | 0.987 | 0.000 | 0.000 | 0.055 | 4.567 |
| scratch_conditioned | 0.167 | 0.793 | 1.239 | 0.506 | 0.000 |
| scratch_conditioned_shielded | 0.203 | 0.683 | 1.059 | 0.493 | 20.090 |
| scratch_conditioned_tangent_shielded | 0.983 | 0.000 | 0.000 | 0.055 | 4.790 |

## Cross-Preset Averages

| Variant | Mean Success | Mean Budget Exhausted | Mean Cost | Mean Final Distance |
|---|---:|---:|---:|---:|
| conditioned | 0.000 | 1.000 | 1.536 | 0.678 |
| conditioned_shielded | 0.417 | 0.333 | 0.400 | 0.326 |
| conditioned_tangent_shielded | 0.867 | 0.000 | 0.000 | 0.060 |
| curriculum_conditioned | 0.208 | 0.735 | 1.125 | 0.538 |
| curriculum_conditioned_shielded | 0.271 | 0.583 | 0.833 | 0.499 |
| curriculum_conditioned_tangent_shielded | 0.919 | 0.000 | 0.000 | 0.066 |
| no_phase_budget | 0.008 | 0.967 | 1.482 | 0.970 |
| scratch_conditioned | 0.152 | 0.761 | 1.154 | 0.538 |
| scratch_conditioned_shielded | 0.273 | 0.592 | 0.841 | 0.497 |
| scratch_conditioned_tangent_shielded | 0.967 | 0.000 | 0.000 | 0.056 |

## Reading

- This stress suite is a transfer-style evaluation: models are trained on prototype-style settings, then evaluated on additional presets.
- Surgical-proxy presets increase document and experiment volume, but they should be described as abstract proxies until implemented in SurRoL/MuJoCo.
- The main question is whether tangent backup control remains robust when target precision, action scale, budget, and forbidden radius change.
