# PhD Proposal Seed

## Title

Failure-Aware Reliability Supervision for Surgical Robot Autonomy under Visual Uncertainty

## Motivation

Autonomous surgical robots should not only learn how to reach a target or execute a manipulation primitive. They must also know when an action is unreliable, when recovery is safe, and when continued autonomy should be deferred to a human operator. In surgical settings, blind recovery can be more dangerous than failure itself because an incorrect corrective motion may cause irreversible harm.

This project studies an external reliability supervisor for surgical robot autonomy. The supervisor does not replace the underlying controller. Instead, it monitors policy rollouts and routes execution into four outcomes: auto-execution, memory-based recovery, human review, or abort candidates.

## Research Question

How can a surgical robot know when not to recover?

More specifically:

1. Can visual-policy rollouts be selectively routed so that only low-risk or recoverable states remain autonomous?
2. Can temporal evidence, such as repeated recovery without progress, identify unsafe auto-recovery attempts?
3. Can task-specific visual uncertainty and recovery memory be learned without relying on privileged simulator state?
4. Which failures should be recovered automatically, and which should be escalated to review?

## Current Prototype

The current prototype is implemented in SurRoL. The main learned visual setting uses `render_proprio_vision`, a 208-dimensional observation composed of 7 proprioceptive features and 201 RGB-rendered image features. Privileged achieved-goal and desired-goal coordinates are not directly provided to the policy input.

The current supervisor contains:

- A visual action-risk head trained from policy-oracle action gap.
- A recovery memory for high-risk visual states.
- An OOD gate based on memory distance.
- A high-risk review threshold.
- A conservative recovery budget.
- A temporal stagnation detector.

## Key Preliminary Evidence

| Experiment | Result | Interpretation |
|---|---:|---|
| Risk-aware routing, 50 seeds | pure policy 3/50 success; guarded routing 9/50 success | selective routing improves accepted autonomous outcomes |
| Learned stagnation, 50 seeds | auto failures 8 -> 4 while preserving 15 auto successes | temporal evidence helps reject failing recovery trajectories |
| Conservative budget, 20 seeds | auto failures 2 -> 0 while preserving 6 auto successes | simple recovery budget is an effective safety guard |
| Visual adapter, strict split | corruption MSE reduced by 99.91% on held-out test | visual denoising works offline |
| Adapter-space recovery memory | closed-loop failure or over-review | offline visual correction does not guarantee reliable recovery |
| Cross-task probe | NeedlePick/GauzeRetrieve learned transfer gives 0/5 success, 5/5 review | current learned visual supervisor is task-specific |

## Positive and Negative Findings

### What is supported

The experiments support the feasibility of a reliability supervisor that improves selective autonomy. The strongest evidence is not raw success-rate maximization, but the reduction of unsafe automatic recovery failures under explicit review routing.

### What failed

Several negative results are important:

- PPO finetuning did not yield a strong surgical policy.
- Offline adapter-space recovery memory looked acceptable offline but failed in closed-loop evaluation.
- Online adapter KNN memory became overly conservative and did not replace the old recovery memory.
- NeedleReach learned visual risk/memory did not directly transfer to NeedlePick or GauzeRetrieve.

These failures sharpen the research direction: reliability supervision must be evaluated in closed loop, task-specific data matters, and uncertainty modules should be judged by selective risk rather than by offline loss alone.

## Proposed PhD Direction

The PhD project would generalize the current prototype into a task-aware reliability supervisor for surgical robot autonomy.

### Aim 1: Task-Specific Visual Risk Modeling

Collect task-specific visual rollouts for NeedlePick, GauzeRetrieve, and more complex manipulation tasks. Train risk heads using action gap, progress failure, visual OOD, unsafe proximity, and phase-aware stagnation labels.

### Aim 2: Phase-Aware Recovery Policies

Replace global KNN recovery memory with phase-aware learned recovery heads. Recovery should depend on task phase, recent progress, and risk category.

### Aim 3: Visual Semantic Memory Integration

Integrate stronger perception features, such as keypoints, compact CNN embeddings, or RAM/VLM-derived object-face memory. RAM/VLM modules would provide upstream semantic state; the reliability supervisor would decide whether that state is trustworthy enough for autonomy.

### Aim 4: Selective Autonomy Evaluation

Evaluate systems with coverage-risk curves:

- automatic coverage
- selected success
- automatic failure rate
- review rate
- abort-candidate rate
- OOD rejection behavior

This avoids overclaiming from raw task success alone.

## Expected Contribution

The expected contribution is a framework for surgical robot reliability supervision that separates:

- execution failures that can be recovered,
- visual or semantic uncertainty that requires review,
- repeated recovery attempts that should be stopped,
- and task states that are unsafe for autonomy.

The contribution is not a claim of clinical deployment. It is a simulation-based research prototype and a methodological step toward safer surgical autonomy.

## Current Limitations

- Results are simulation-only.
- The visual encoder is currently hand-crafted RGB pooling plus a linear adapter.
- Learned visual routing is strongest on NeedleReach and not yet transferred to complex tasks.
- Risk labels are proxy labels, not clinical tissue-damage labels.
- PPO policies are not strong enough to be the main contribution.

## Thesis Statement

Surgical autonomy should be evaluated not only by whether a robot can complete a task, but by whether it can recognize when autonomy is unreliable. A failure-aware reliability supervisor can improve selective autonomy by routing uncertain or repeatedly failing rollouts away from blind recovery and toward review or abort decisions.

