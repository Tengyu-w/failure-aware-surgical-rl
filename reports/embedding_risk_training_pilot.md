# Embedding-Risk Guided PPO Pilot

## Question

Can embedding/KNN instability analysis improve the base PPO policy when it is
fed back into training as a reward-shaping signal?

## Method

The pilot uses the custom navigation proxy, not SurRoL. A small NumPy risk
scorer is built from `outputs/risk_dataset/risk_dataset.csv`, filtered to
`source_kind=synthetic_navigation`. The scorer standardizes seven timestep
features, projects them into a PCA embedding, then compares each state to
nearest risk and non-risk neighbors. The resulting score is used as a PPO
reward penalty through the `conditioned_embedding_risk_penalty` variant.

Three 8,192-step pilots were run with one seed and 40 deterministic evaluation
episodes per preset:

| Pilot | Training signal |
|---|---|
| `continuous_t075` | continuous embedding-risk penalty, scale 0.75 |
| `continuous_t025` | continuous embedding-risk penalty, scale 0.25 |
| `thresholded_t075_thr055` | only penalize risk above 0.55, scale 0.75 |

## Key Result

| Pilot | Preset | Method | Success | Budget Exhaustion | Mean Cost | Final Distance | Mean Risk | Active Risk |
|---|---|---|---:|---:|---:|---:|---:|---:|
| continuous_t075 | prototype | baseline PPO | 0.025 | 0.975 | 2.011 | 0.650 | 0.303 |  |
| continuous_t075 | prototype | embedding-risk PPO | 0.075 | 0.925 | 1.923 | 0.688 | 0.329 |  |
| continuous_t075 | strict | baseline PPO | 0.000 | 1.000 | 1.000 | 0.640 | 0.369 |  |
| continuous_t075 | strict | embedding-risk PPO | 0.000 | 1.000 | 1.000 | 0.937 | 0.380 |  |
| continuous_t025 | prototype | baseline PPO | 0.025 | 0.975 | 2.011 | 0.650 | 0.303 |  |
| continuous_t025 | prototype | embedding-risk PPO | 0.000 | 1.000 | 2.004 | 0.723 | 0.332 |  |
| continuous_t025 | strict | baseline PPO | 0.000 | 1.000 | 1.000 | 0.640 | 0.369 |  |
| continuous_t025 | strict | embedding-risk PPO | 0.025 | 0.925 | 0.928 | 0.513 | 0.404 |  |
| thresholded_t075_thr055 | prototype | baseline PPO | 0.025 | 0.975 | 2.011 | 0.650 | 0.303 | 0.048 |
| thresholded_t075_thr055 | prototype | embedding-risk PPO | 0.000 | 1.000 | 2.056 | 0.648 | 0.298 | 0.016 |
| thresholded_t075_thr055 | strict | baseline PPO | 0.000 | 1.000 | 1.000 | 0.640 | 0.369 | 0.020 |
| thresholded_t075_thr055 | strict | embedding-risk PPO | 0.000 | 1.000 | 1.049 | 0.651 | 0.369 | 0.000 |

Full summary: `outputs/embedding_risk_training_pilot_comparison.csv`.

## Interpretation

This pilot shows that embedding/KNN instability analysis can be connected to
the PPO training loop and can change learned behavior. However, it does not yet
show a stable overall policy improvement.

What is shown:

- `continuous_t075` improves prototype success from 0.025 to 0.075 and reduces
  budget exhaustion from 0.975 to 0.925.
- `continuous_t025` improves strict budget exhaustion from 1.000 to 0.925 and
  improves strict final distance from 0.640 to 0.513.
- `thresholded_t075_thr055` reduces high-risk embedding activation on both
  prototype and strict, but does not improve success or budget exhaustion.

What is not yet shown:

- No setting wins consistently across prototype and strict.
- Mean embedding risk does not reliably decrease for the continuous penalties.
- The result is one-seed, short-horizon PPO evidence, so it is a pilot rather
  than a formal training improvement claim.

## Next Experiment

The next stronger version should use embedding risk for targeted sampling
rather than only reward shaping: collect or reset into high-risk states, add
oracle/recovery actions there, and fine-tune the policy on those hard-negative
states. That would test whether the instability analysis can improve the model
through data selection, not only through a scalar penalty.
