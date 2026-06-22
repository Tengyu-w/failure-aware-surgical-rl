# SurRoL PPO / Pseudo-Vision Readiness

## 一句话结论

本轮已经把 SurRoL RL 环境接入一个 failure-aware PPO wrapper：它支持 state/pseudo_vision 两种观测、render_pseudo_vision 图像压缩观测、action_noise/action_dropout/near_target_drift 训练扰动、forbidden-zone 风险惩罚和 success bonus。目前 NeedlePickRL 和 PickAndPlaceRL 都通过了环境级 smoke；NeedlePickRL 还完成了一个最小 PPO 训练 smoke、保存 checkpoint，并跑通了 checkpoint 评估入口。

## Smoke Evidence

| Task | Observation mode | Obs shape | Action shape | Failure mode | Danger signal | Status |
|---|---|---:|---:|---|---|---|
| NeedlePickRL-v0 | pseudo_vision | 32 | 5 | near_target_drift | unsafe_violation in info | smoke_pass |
| PickAndPlaceRL-v0 | pseudo_vision | 57 | 5 | near_target_drift | unsafe_violation in info | smoke_pass |
| NeedlePickRL-v0 | render_pseudo_vision | 50 | 5 | near_target_drift | rendered RGB compressed features | smoke_pass |
| GauzeRetrieveRL-v0 | pseudo_vision | 32 | 5 | near_target_drift | unsafe_violation in info | smoke_pass |

## PPO Dependency Probe

- Earlier probe showed `stable_baselines3/torch` were missing.
- The SurRoL py38 environment was then updated with CPU torch and Stable-Baselines3.
- Previous blocked reason: stable_baselines3/torch is not installed in the active SurRoL environment
- Previous error: `No module named 'stable_baselines3'`

## PPO Train Smoke

| Task | Observation mode | Failure mode | Requested timesteps | Model saved |
|---|---|---|---:|---|
| NeedlePickRL-v0 | pseudo_vision | near_target_drift | 16 | True |
| NeedlePickRL-v0 | pseudo_vision | near_target_drift | 2048 | True |

## PPO Evaluation Smoke

The smoke checkpoint was evaluated for 3 episodes under near-target drift. It did not solve the task, which is expected for a 256-step smoke policy, and all episodes were routed to human_review rather than auto_execute.

- Evaluation CSV exists: True

## PPO 2048-Step Evaluation

| Model | Episodes | Success | Mean final distance | Unsafe events | Risk routes |
|---|---:|---:|---:|---:|---|
| NeedlePickRL pseudo_vision 2048 | 5 | 0.000 | 0.187 | 0 | {'human_review': 5} |

The 2048-step PPO run is a real training run, but it is still far too short for NeedlePickRL: evaluation remains 0/5 success and is routed to human_review. This is useful negative evidence rather than a failed script.

## Demonstration / BC Initialization

| Method | Demo steps | BC epochs | Final action MSE | Eval condition | Episodes | Success | Mean final distance | Unsafe events | Risk routes |
|---|---:|---:|---:|---|---:|---:|---:|---:|---|
| BC-MSE | 205 | 80 | 0.0203 | clean | 5 | 0.000 | 0.184 | 0 | {'human_review': 5} |
| BC-MSE | 205 | 80 | 0.0203 | near_target_drift | 5 | 0.000 | 0.184 | 0 | {'human_review': 5} |
| BC-MSE + PPO 2048 | 205 | 80 | 0.0203 | near_target_drift | 5 | 0.000 | 0.184 | 5 | {'abort_candidate': 5} |

BC reduced action imitation error, but the resulting policy still does not complete NeedlePickRL. After PPO fine-tuning from BC, the policy reaches the forbidden-zone proxy earlier under near-target drift and is routed to abort_candidate. This supports the risk-aware argument: a learned policy must be evaluated by safety routing, not judged only by whether it moves.

## Complex Task Breadth: PickAndPlaceRL

| Task | Demo steps | BC epochs | Final action MSE | Eval condition | Episodes | Success | Mean final distance | Unsafe events | Risk routes |
|---|---:|---:|---:|---|---:|---:|---:|---:|---|
| PickAndPlaceRL-v0 | 176 | 40 | 0.0695 | clean | 3 | 0.000 | 0.235 | 0 | {'human_review': 3} |
| PickAndPlaceRL-v0 | 176 | 40 | 0.0695 | near_target_drift | 3 | 0.000 | 0.232 | 0 | {'human_review': 3} |

PickAndPlaceRL now enters the same demo -> BC policy -> risk evaluation chain as NeedlePickRL. The policy is not successful yet, so this should be reported as breadth/readiness evidence, not as a solved complex-task result.

## Cross-Task Breadth: GauzeRetrieveRL

| Task | Demo steps | BC epochs | Final action MSE | Eval condition | Episodes | Success | Mean final distance | Unsafe events | Risk routes |
|---|---:|---:|---:|---|---:|---:|---:|---:|---|
| GauzeRetrieveRL-v0 | 101 | 60 | 0.0825 | clean | 5 | 0.000 | 0.290 | 0 | {'human_review': 5} |
| GauzeRetrieveRL-v0 | 101 | 60 | 0.0825 | near_target_drift | 5 | 0.000 | 0.290 | 2 | {'human_review': 3, 'abort_candidate': 2} |

GauzeRetrieveRL is now integrated into the same training and risk-routing pipeline. Under near-target drift, some episodes are promoted from human_review to abort_candidate because they enter the forbidden-zone proxy.

## What This Adds To The Project

- PPO/RL: there is now a concrete PPO entry point instead of only oracle + monitor evaluation.
- Pseudo-vision: the wrapper can append noisy keypoint/depth-like features derived from visual-state proxies before policy learning.
- Render pseudo-vision: the wrapper can call SurRoL RGB rendering and compress images into policy features, so vision-like errors can enter before action selection.
- Multi-task breadth: the same wrapper passed smoke and BC/evaluation readiness on NeedlePickRL, GauzeRetrieveRL, and PickAndPlaceRL.
- Risk-aware learning: the reward can penalize forbidden-zone violations, so risk-aware routing is no longer only a post-hoc evaluator.
- Policy evaluation: trained PPO checkpoints can now be loaded and routed through a simple risk-level evaluator.
- Demonstration initialization: oracle demonstrations can now initialize a PPO policy through behavior cloning before RL fine-tuning.

## What Is Still Not Complete

- The current PPO checkpoints are smoke/small-training checkpoints, not meaningful trained surgical policies yet.
- BC initialization changes behavior but does not yet solve NeedlePickRL; under drift it can increase unsafe-zone exposure.
- PickAndPlaceRL is now integrated into the training/evaluation chain, but the current 2-demo BC policy is not successful.
- GauzeRetrieveRL is integrated, but the current 3-demo BC policy is also not successful and shows drift-triggered abort candidates.
- The render_pseudo_vision signal compresses RGB images with hand-crafted statistics, not a learned segmentation or VLM encoder.
- PickAndPlaceRL has only passed one-step smoke; it is not yet a stable multi-seed training/evaluation benchmark.
- The current reward shaping uses a geometric forbidden-zone proxy, not physical tissue-force or deformation feedback.

## Next Concrete Step

Next, either extend NeedlePickRL PPO training substantially beyond 2k timesteps, or initialize from demonstrations / curriculum before attempting PickAndPlaceRL training. The current evidence suggests sparse reward PPO from scratch is not enough at this scale.

## Files

- `scripts/train_surrol_ppo_failure_aware.py`
- `scripts/run_surrol_ppo_failure_aware.ps1`
- `runs/surrol_ppo_smoke_needlepick_pseudovision/smoke_check.json`
- `runs/surrol_ppo_smoke_pickandplace_pseudovision/smoke_check.json`
- `runs/surrol_ppo_smoke_needlepick_render_pseudovision/smoke_check.json`
- `runs/surrol_ppo_dependency_probe_needlepick/dependency_blocked.json`
- `runs/surrol_ppo_train_smoke_needlepick_16step/model.zip`
- `runs/surrol_ppo_train_smoke_needlepick_16step/train_summary.json`
- `runs/surrol_ppo_eval_needlepick_smoke_3ep.csv`
- `runs/surrol_ppo_train_needlepick_pseudovision_2048_seed43000/model.zip`
- `runs/surrol_ppo_eval_needlepick_pseudovision_2048_5ep.csv`
- `runs/surrol_ppo_bc_needlepick_pseudovision_5demo_mse80/model_bc.zip`
- `runs/surrol_ppo_eval_needlepick_bc_mse80_clean_5ep.csv`
- `runs/surrol_ppo_eval_needlepick_bc_mse80_drift_5ep.csv`
- `runs/surrol_ppo_train_needlepick_bcinit_mse80_2048/model.zip`
- `runs/surrol_ppo_eval_needlepick_bcinit_mse80_2048_drift_5ep.csv`
- `runs/surrol_ppo_bc_pickandplace_pseudovision_2demo_mse40/model_bc.zip`
- `runs/surrol_ppo_eval_pickandplace_bc_2demo_clean_3ep.csv`
- `runs/surrol_ppo_eval_pickandplace_bc_2demo_drift_3ep.csv`
- `runs/surrol_ppo_bc_gauzeretrieve_pseudovision_3demo_mse60/model_bc.zip`
- `runs/surrol_ppo_eval_gauzeretrieve_bc_3demo_clean_5ep.csv`
- `runs/surrol_ppo_eval_gauzeretrieve_bc_3demo_drift_5ep.csv`