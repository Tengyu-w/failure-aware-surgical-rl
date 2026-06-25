# Embedding-Risk Guided PPO Pilot

## Question

Can embedding/KNN instability analysis improve the PPO policy when the risk
signal is fed back into training, instead of being used only for post-hoc
explanation?

## Method

This experiment uses the custom constrained navigation proxy, not SurRoL. The
risk scorer is built from `outputs/risk_dataset/risk_dataset.csv`, filtered to
`source_kind=synthetic_navigation`. It standardizes seven timestep features,
projects them into a PCA embedding, and compares each state to nearest risk and
non-risk neighbors.

Two training-loop uses were implemented:

| Training use | Variant | Meaning |
|---|---|---|
| reward shaping | `conditioned_embedding_risk_penalty` | subtract a penalty when the embedding/KNN risk score is above threshold |
| hard-negative curriculum | `conditioned_embedding_risk_curriculum` | use the risk scorer during reset to select harder near-forbidden/path-blocking starts, then train with the risk penalty |

The curriculum version is tested as a two-stage fine-tune: first train a
baseline PPO policy, then continue training with embedding-risk hard negatives.

## Multi-Seed Follow-Up

Run settings:

- Seeds: 0, 1, 2.
- 8,192 PPO timesteps per training stage.
- 50 deterministic evaluation episodes per seed and preset.
- Training preset: `prototype`.
- Evaluation presets: `prototype` and `strict`.
- Risk threshold: 0.55.
- Penalty scale: 0.25.
- Curriculum reset probability: 0.35.

![Embedding-risk multi-seed pilot](figures/embedding_risk_training_pilot/multiseed_curriculum_metrics.png)

| Method | Preset | Success | Budget Exhaustion | Mean Return | Final Distance |
|---|---|---:|---:|---:|---:|
| baseline PPO | prototype | 0.047 +/- 0.050 | 0.953 +/- 0.050 | -40.983 +/- 8.907 | 0.687 +/- 0.054 |
| embedding-risk reward PPO | prototype | 0.007 +/- 0.012 | 0.993 +/- 0.012 | -45.037 +/- 6.773 | 0.721 +/- 0.029 |
| embedding-risk curriculum fine-tune PPO | prototype | 0.040 +/- 0.020 | 0.960 +/- 0.020 | -28.632 +/- 2.058 | 0.704 +/- 0.066 |
| baseline PPO | strict | 0.000 +/- 0.000 | 1.000 +/- 0.000 | -57.651 +/- 16.348 | 0.845 +/- 0.327 |
| embedding-risk reward PPO | strict | 0.027 +/- 0.046 | 0.973 +/- 0.046 | -73.178 +/- 15.782 | 0.984 +/- 0.401 |
| embedding-risk curriculum fine-tune PPO | strict | 0.000 +/- 0.000 | 1.000 +/- 0.000 | -32.202 +/- 3.040 | 0.697 +/- 0.024 |

Full multi-seed tables:

- `outputs/embedding_risk_multiseed_curriculum_seed_summary.csv`
- `outputs/embedding_risk_multiseed_curriculum_aggregate_summary.csv`

## Interpretation

The multi-seed follow-up does not confirm a stable success-rate or
budget-exhaustion improvement. That is the most important conclusion.

What is shown:

- Embedding risk is now genuinely connected to training, both as reward shaping
  and as hard-negative reset sampling.
- Curriculum fine-tuning improves mean return on both presets. Prototype return
  improves from -40.983 to -28.632, and strict return improves from -57.651 to
  -32.202.
- Curriculum fine-tuning improves strict final distance from 0.845 to 0.697 and
  greatly reduces final-distance variance in this three-seed pilot.
- Reward-only shaping produces a small strict success/budget improvement in the
  aggregate, but it also worsens return and final distance, so it is not a
  clean policy improvement.

What is not yet shown:

- Prototype success does not improve in the multi-seed aggregate: baseline is
  0.047, curriculum fine-tune is 0.040.
- Prototype budget exhaustion does not improve in the multi-seed aggregate:
  baseline is 0.953, curriculum fine-tune is 0.960.
- Strict budget exhaustion remains 1.000 for baseline and curriculum fine-tune.
- The evidence is still a short-horizon PPO pilot, not a formal robust training
  claim.

The honest claim is therefore narrower than the single-seed result suggested:
embedding/KNN risk can be used as a training signal and changes the learned
policy, but the current implementation mainly improves return and some distance
metrics. It does not yet reliably improve success or safety-budget outcomes.

## Earlier Single-Seed Fine-Tune Pilot

Before the multi-seed follow-up, a one-seed 40-episode pilot showed a more
positive prototype result for curriculum fine-tuning:

| Method | Preset | Success | Budget Exhaustion | Mean Return | Final Distance |
|---|---|---:|---:|---:|---:|
| baseline PPO | prototype | 0.025 | 0.975 | -41.783 | 0.650 |
| embedding-risk curriculum fine-tune PPO | prototype | 0.050 | 0.950 | -27.116 | 0.630 |
| baseline PPO | strict | 0.000 | 1.000 | -57.689 | 0.640 |
| embedding-risk curriculum fine-tune PPO | strict | 0.000 | 1.000 | -28.305 | 0.696 |

This result was useful for discovering that two-stage curriculum fine-tuning is
more promising than training from hard negatives from scratch. The multi-seed
run above is stronger evidence and should be preferred for claims.

Full single-seed summary:
`outputs/embedding_risk_curriculum_finetune_pilot_summary.csv`.

## Earlier Reward-Shaping Pilot

Before the curriculum upgrade, three reward-only settings were tested with
8,192 PPO steps and 40 evaluation episodes:

| Pilot | Training signal |
|---|---|
| `continuous_t075` | continuous embedding-risk penalty, scale 0.75 |
| `continuous_t025` | continuous embedding-risk penalty, scale 0.25 |
| `thresholded_t075_thr055` | only penalize risk above 0.55, scale 0.75 |

The best reward-only settings produced isolated improvements: one improved
prototype success from 0.025 to 0.075 and budget exhaustion from 0.975 to
0.925, while another improved strict budget exhaustion from 1.000 to 0.925.
However, no reward-only setting won consistently across prototype and strict.

Full earlier comparison:
`outputs/embedding_risk_training_pilot_comparison.csv`.

## Next Experiment

The next experiment should keep the embedding-risk curriculum but add a stronger
goal-retention mechanism, because the current risk signal can improve avoidance
or return while failing to improve success. Good candidates are:

1. gradually increasing curriculum probability instead of using a fixed 0.35;
2. mixing hard negatives with extra goal-reaching demonstrations or hindsight
   relabeling;
3. applying the risk curriculum only after the policy reaches a minimum
   success-rate checkpoint;
4. combining curriculum fine-tuning with the risk-gated tangent supervisor
   during evaluation.

## Conclusion

Embedding/KNN analysis is no longer only a classifier or explanation tool in
this repository. It is now connected to the PPO training loop as:

1. a risk-aware reward penalty;
2. a hard-negative curriculum reset mechanism;
3. a two-stage fine-tuning route.

The strongest current claim is: embedding risk changes training behavior and
improves some return/distance metrics, but the present implementation has not
yet produced robust multi-seed improvements in success rate or safety-budget
exhaustion.
