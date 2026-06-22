# Claims And Limitations Table

## Evidence Levels

| Level | Meaning |
|---|---|
| Confirmed | Supported by completed experiment logs and multi-seed results |
| Suggested | Plausible from current evidence but needs more seeds/tasks |
| Not proven | Should not be claimed |
| Withdrawn | Tested and should not be used as a positive result |

## Claims

| Claim | Level | Evidence | Limitation |
|---|---|---|---|
| A reliability supervisor can improve selective autonomy on SurRoL NeedleReach. | Confirmed | Guarded routing improves selected success over pure policy in 50-seed evaluation. | Mainly NeedleReach learned visual setting. |
| Conservative recovery budget reduces automatic failures. | Confirmed | Budget 10 reduces auto failures 2 -> 0 while preserving 6 auto successes in 20-seed mixed corruption test. | Needs more seeds and task transfer validation. |
| Temporal stagnation can catch some failing recovery trajectories. | Confirmed but preliminary | 50-seed result reduces auto failures 8 -> 4 while preserving 15 auto successes. | Few failure examples in training/evaluation. |
| Visual observations causally affect the learned policy. | Confirmed | Blackout removes success in visual policy tests. | Visual representation is hand-crafted RGB pooling. |
| Visual adapter reduces corruption in feature space. | Confirmed offline | Strict held-out test shows 99.91% corruption MSE reduction. | Offline denoising does not guarantee closed-loop recovery improvement. |
| Old augmented recovery memory remains better than new KNN adapter memories. | Confirmed in current setting | Round 43 online KNN memory over-reviews; Round 40 adapter memory causes failures. | Old memory is still task-local and simple. |
| The reliability framework transfers across tasks at the rule/phase-aware level. | Suggested / partially confirmed | NeedlePick and GauzeRetrieve monitor results recover standard corruptions and jaw-stuck failures. | These are rule/oracle-based, not learned visual routing. |
| Learned visual routing transfers from NeedleReach to NeedlePick/GauzeRetrieve. | Not proven | Direct probe gives 0/5 success and 5/5 review on both tasks. | Needs task-specific policy, risk head, and memory. |
| Current PPO/RL policy is strong. | Not proven | PPO and BC/PPO attempts remain weak or unstable. | Do not use as main claim. |
| Current system is clinically deployable or detects real tissue damage. | Not proven | All results are simulation and proxy-risk based. | No real force, deformation, clinical validation, or hardware deployment. |
| Round 40 adapter-space recovery memory is a valid improvement. | Withdrawn | Closed-loop automatic failures increase sharply. | Do not include as positive result. |
| Round 43 online adapter KNN memory replaces old memory. | Withdrawn as replacement | It avoids failures but over-reviews and does not improve recovery. | Useful as negative evidence only. |

## Recommended Wording

Use:

> The current evidence supports a simulation-based external reliability supervisor for selective surgical autonomy. The strongest result is improved routing: reducing unsafe automatic recovery while preserving accepted autonomous successes.

Avoid:

> The system solves SurRoL surgical autonomy.

Avoid:

> The visual adapter solves visual uncertainty.

Avoid:

> The learned visual supervisor transfers across tasks.

## Next Validation Needed

1. Task-specific learned visual data for NeedlePick and GauzeRetrieve.
2. Learned phase-aware recovery head instead of global KNN memory.
3. Stronger visual representation: keypoints, CNN embeddings, or RAM/VLM-derived memory.
4. Coverage-risk curves across tasks and corruption severities.
5. More realistic irreversible-risk proxies, including contact or force-related signals.

