# Experiment Plan

## Research Question

Can a policy conditioned on task phase and safety budget improve constrained
success in abstract contact-rich surgical manipulation?

## Environments

Initial environment:

- `ConstrainedToolNavigationEnv`
- 3D tool-tip navigation
- target-reaching objective
- forbidden tissue-like volume
- force proxy from penetration depth
- workspace and motion penalties
- per-episode safety budget

Preferred later simulator:

- SurRoL, if deployment is stable.

Fallback simulator:

- ManiSkill or MuJoCo with a surgical-tool abstraction.

## Baselines

1. PPO with full constraint-conditioned observation.
2. PPO without task phase and remaining safety budget (`no_phase_budget`).
3. PPO with fixed conservative penalty weights.
4. PPO with a simple backup-controller shield (`conditioned_shielded`).

## Metrics

- success rate;
- budget violation rate;
- mean cumulative constraint cost;
- mean force proxy;
- episode length;
- reward curve;
- robustness over random seeds.

## First Formal Run

Use at least 3 seeds for the prototype phase:

```powershell
python scripts\train_ppo.py --seed 0 --total-timesteps 100000 --out-dir runs\ppo_seed0
python scripts\train_ppo.py --seed 1 --total-timesteps 100000 --out-dir runs\ppo_seed1
python scripts\train_ppo.py --seed 2 --total-timesteps 100000 --out-dir runs\ppo_seed2
```

These are still prototype-scale runs, not final paper-level evidence.

Run the current prototype comparison:

```powershell
.\scripts\run_prototype_experiment.ps1 -TotalTimesteps 10000 -Episodes 50 -ConfigPreset prototype
```

Curriculum comparison:

```powershell
.\scripts\run_curriculum_comparison.ps1 -EasyTimesteps 10000 -PrototypeTimesteps 40000 -Episodes 100 -Variant conditioned
```

Shielded curriculum comparison:

```powershell
.\scripts\run_curriculum_comparison.ps1 -EasyTimesteps 10000 -PrototypeTimesteps 40000 -Episodes 100 -Variant conditioned_shielded
```

Current 50k-step prototype summary:

Note: the table below documents the earlier 2D prototype runs. After the 3D
environment upgrade, policies should be retrained before making new claims.

| Variant | Success | Budget Exhausted | Cost | Final Distance |
|---|---:|---:|---:|---:|
| scratch_conditioned | 0.227 | 0.720 | 1.567 | 0.454 |
| curriculum_conditioned | 0.287 | 0.703 | 1.574 | 0.448 |
| scratch_conditioned_shielded | 0.313 | 0.570 | 1.234 | 0.430 |
| curriculum_conditioned_shielded | 0.313 | 0.560 | 1.193 | 0.424 |
| scratch_conditioned_tangent_shielded | 1.000 | 0.000 | 0.000 | 0.053 |
| curriculum_conditioned_tangent_shielded | 1.000 | 0.000 | 0.000 | 0.054 |

The strongest current algorithmic direction is:

```text
constraint-conditioned PPO + tangent backup controller
```

Curriculum remains a useful comparison, but the clearest improvement comes from
the backup controller that projects unsafe actions into a tangential avoidance
direction around forbidden tissue-like regions.

Strict-preset transfer check:

```powershell
.\scripts\evaluate_trained_comparison.ps1 -EvalPreset strict -Episodes 100
```

Rollout visualization:

```powershell
python scripts\plot_policy_rollouts.py --model runs\cmp_curriculum_conditioned_shielded_seed2\model --variant conditioned_shielded --config-preset prototype --episodes 6 --deterministic
```

## Evaluation

```powershell
python scripts\evaluate_policy.py --model runs\ppo_seed0\model --variant conditioned --episodes 100 --out runs\ppo_seed0\eval.csv --deterministic
```

Summarize multiple evaluation files:

```powershell
python scripts\summarize_evals.py runs\ppo_seed0\eval.csv runs\ppo_seed1\eval.csv --out runs\summary.csv
```

## Smoke Comparison

```powershell
.\scripts\run_smoke_comparison.ps1
```
