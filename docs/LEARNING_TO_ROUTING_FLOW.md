# Learning-To-Routing Flow

This document explains the full experimental logic behind the project:
baseline RL training, failure labeling, embedding/KNN risk analysis,
training-loop feedback, visual reliability modules, and the final move toward
runtime multi-route supervision.

The motivation is close to surgical embodied-intelligence systems such as
vision-parsing + RL + visual-servo pipelines and retrieval-augmented
manipulation systems. Better spatial planning or better policy learning does
not guarantee that execution remains reliable near the target. The missing
piece is an execution-time reliability layer that can detect stagnation,
visual uncertainty, action-outcome mismatch, and unsafe recovery conditions.

## 1. What The RL Policy Learns From

The RL policy is not trained from human-written labels at every timestep.
Training is mostly interaction-based:

```text
state or observation
  -> policy action
  -> simulator step
  -> reward, next state, done flag, diagnostic info
  -> PPO update
```

In the custom constrained proxy, the reward includes dense distance-to-goal
terms, force/contact proxy penalties, motion cost, forbidden-region and
workspace violation penalties, success bonus, and safety-budget termination.

In the SurRoL branch, the PPO wrapper can use state, pseudo-vision, rendered
vision features, or proprioceptive-plus-vision features. The reward can include
success bonus, progress reward, distance shaping, near-target action damping,
and danger-zone penalties.

So the first learning target is not a manually labeled class. It is a policy
that tries to maximize task reward under safety and progress constraints.

## 2. Where The Labels Come From

After rollouts are collected, the project builds reliability labels from logs.
These labels are not independent expert annotations; they are weak labels
distilled from simulator diagnostics and failure-injection design.

### Timestep-Level Risk Labels

`outputs/risk_dataset/risk_dataset.csv` contains timestep-level weak risk
labels. A timestep can be marked high risk when it shows one or more of:

- near forbidden-zone or workspace boundary;
- high force/contact proxy;
- low remaining safety budget;
- stalled progress while still far from the target;
- explicit risk/monitor/unsafe event;
- episode-level failure or safety-budget exhaustion.

These rows become the substrate for embedding/PCA/KNN risk analysis.

### Episode-Level Route Labels

SurRoL episode logs are also converted into route labels:

| Failure family | Example failures | Route meaning |
| --- | --- | --- |
| nominal execution | `none` | `auto_execute` |
| reversible execution drift | `action_noise`, `action_dropout`, `execution_slip` | `auto_recovery` |
| visual-state error | `perception_bias`, `depth_scale_error` | `human_review` or re-estimation |
| grasp/contact uncertainty | `jaw_stuck_open` | review or observable retry |
| unsafe recovery proxy | danger-zone abort cases | `abort_candidate` |

These labels are used to train and audit a learned route classifier. They are
useful for research supervision, but they should not be described as clinical
or surgeon-labeled ground truth.

### Visual Reliability Labels

The visual branch adds two related supervision signals:

- clean/corrupt visual-feature pairs for a denoising adapter;
- policy-vs-oracle action gap labels for a visual action-risk head.

The action-risk head marks a step as high risk when the policy action is far
from an oracle/reference action. This is an action-outcome reliability proxy,
not a clinical failure label.

## 3. Embedding/KNN Error Analysis

The ECG-inspired idea is to inspect whether learned or logged behavior has
geometry in feature space:

```text
rollout features
  -> standardization
  -> PCA embedding
  -> nearest risk and non-risk neighbors
  -> risk score / atypicality / OOD-style distance
```

In this project, the embedding/KNN score asks:

- Does this state look close to known risky states?
- Is it closer to failed or successful local neighborhoods?
- Is it far from the training memory, suggesting OOD behavior?

This is useful for explanation and triage, but the project also tests whether
it can improve training.

## 4. The Attempt To Improve The Model

The embedding risk score was fed back into PPO in two ways:

| Training feedback | Implementation | Intended effect |
| --- | --- | --- |
| reward shaping | penalize high embedding-risk states | teach the policy to avoid known risky regions |
| hard-negative curriculum | reset into harder high-risk starts | force training data to cover failure-prone states |
| curriculum fine-tuning | train baseline first, then fine-tune on hard negatives | avoid making early training too difficult |

The multi-seed result is intentionally conservative:

- curriculum fine-tuning improves mean return;
- strict final distance improves;
- success rate and safety-budget exhaustion do not reliably improve.

This is a useful negative result. It shows that embedding risk can influence
the learned policy, but current reward/curriculum feedback is not enough to
make the policy robust.

## 5. Why The Project Moves To Runtime Routing

Because training-loop feedback did not produce a robust policy improvement,
the final system does not rely only on making the RL policy better. It adds a
runtime supervisor.

The supervisor asks:

```text
Is this a normal execution state?
Is this a recoverable execution drift?
Is this visual/contact uncertainty that needs review or re-estimation?
Is this an unsafe recovery candidate?
```

This is the main conceptual upgrade:

```text
train policy
  -> analyze errors and embeddings
  -> try risk-aware retraining
  -> observe that retraining is not enough
  -> deploy reliability routing around the policy
```

## 6. Final Research Position

The final claim is not that the new PPO policy is solved. The stronger claim is
that the project builds a reliability-supervised surgical RL pipeline:

1. train a baseline policy;
2. collect rollout failures;
3. weakly label risk, failure family, and route;
4. analyze embedding/KNN structure;
5. feed risk back into training and report its limits;
6. add visual reliability modules;
7. use risk-gated and mechanism-routed supervisors for execution-time
   intervention.

This makes the project useful for surgical embodied AI because it addresses a
practical gap: even if visual parsing and RL policy learning are strong, the
system still needs to know when execution has become unreliable and what kind
of intervention is appropriate.
