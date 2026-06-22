# Reproduction Commands

All commands assume the project root is:

```powershell
E:\RL_projects\constraint_surgical_rl
```

Use the local environment:

```powershell
E:\RL_projects\constraint_surgical_rl\.conda\python.exe
```

## Tests

```powershell
& .\.conda\python.exe -m pytest -q
```

## Heuristic Checks

```powershell
& .\.conda\python.exe scripts\evaluate_heuristic.py --variant conditioned --config-preset prototype --episodes 100 --out runs\heuristic_prototype_eval.csv
& .\.conda\python.exe scripts\evaluate_heuristic.py --variant conditioned --config-preset strict --episodes 100 --out runs\heuristic_strict_eval.csv
```

## 3D Smoke Comparison

```powershell
.\scripts\run_3d_smoke_comparison.ps1 -TotalTimesteps 1024 -Episodes 10
```

## 3D Prototype Comparison

```powershell
.\scripts\run_3d_prototype_experiment.ps1 -TotalTimesteps 20000 -Episodes 50 -ConfigPreset prototype -RunPrefix proto_3d
```

## Multi-Phase Manipulation Proxy

```powershell
& .\.conda\python.exe scripts\evaluate_manipulation_heuristic.py --variant conditioned_tangent_shielded --episodes 100 --out runs\manipulation_heuristic_tangent_eval.csv
& .\.conda\python.exe scripts\train_ppo.py --task manipulation --variant conditioned_tangent_shielded --total-timesteps 1024 --out-dir runs\smoke_manipulation_tangent --verbose 0
& .\.conda\python.exe scripts\evaluate_policy.py --task manipulation --model runs\smoke_manipulation_tangent\model --variant conditioned_tangent_shielded --episodes 5 --out runs\smoke_manipulation_tangent\eval.csv --deterministic
.\scripts\run_manipulation_failure_suite.ps1 -Episodes 100
```

## Prototype Comparison

```powershell
.\scripts\run_prototype_experiment.ps1 -TotalTimesteps 10000 -Episodes 50 -ConfigPreset prototype
```

## Curriculum Comparison

```powershell
.\scripts\run_curriculum_comparison.ps1 -EasyTimesteps 10000 -PrototypeTimesteps 40000 -Episodes 100 -Variant conditioned
.\scripts\run_curriculum_comparison.ps1 -EasyTimesteps 10000 -PrototypeTimesteps 40000 -Episodes 100 -Variant conditioned_shielded
.\scripts\run_curriculum_comparison.ps1 -EasyTimesteps 10000 -PrototypeTimesteps 40000 -Episodes 100 -Variant conditioned_tangent_shielded
```

## Strict Transfer

```powershell
.\scripts\evaluate_trained_comparison.ps1 -EvalPreset strict -Episodes 100
.\scripts\evaluate_trained_comparison.ps1 -EvalPreset strict -Episodes 100 -Variants conditioned_tangent_shielded
```

## Expanded Stress Transfer Suite

```powershell
.\scripts\run_stress_transfer_suite.ps1 -Episodes 100
.\scripts\run_3d_breadth_suite.ps1 -Episodes 20
```

## Random-Policy Sanity Checks

```powershell
& .\.conda\python.exe scripts\evaluate_random_policy.py --variant conditioned --config-preset prototype --episodes 100 --out runs\random_conditioned_prototype.csv
& .\.conda\python.exe scripts\evaluate_random_policy.py --variant conditioned_shielded --config-preset prototype --episodes 100 --out runs\random_conditioned_shielded_prototype.csv
& .\.conda\python.exe scripts\evaluate_random_policy.py --variant conditioned_tangent_shielded --config-preset prototype --episodes 100 --out runs\random_conditioned_tangent_shielded_prototype.csv
```

## Reports

```powershell
& .\.conda\python.exe scripts\write_project_brief.py --prototype runs\prototype_all_aggregate_summary.csv --strict runs\cmp_strict_all_aggregate_summary.csv --out reports\project_brief.md
& .\.conda\python.exe scripts\write_cross_task_recovery_report.py --out reports\cross_task_recovery_report.md
& .\.conda\python.exe scripts\write_human_review_trigger_report.py --out reports\human_review_trigger_report.md
& .\.conda\python.exe scripts\write_risk_model_report.py --out reports\risk_model_report.md --dataset-out reports\risk_model_dataset.csv
```

## Multi-Seed Reliability

```powershell
.\scripts\run_navigation_multiseed_failure_suite.ps1 -Episodes 20 -DriftStep 5
```
