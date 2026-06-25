# Reproduction Commands

All commands assume they are run from the repository root.

## Tests

```powershell
python -m pytest -q
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
python scripts\build_surrol_master_results.py
python scripts\build_surrol_fault_taxonomy.py
python scripts\train_surrol_route_classifier.py
python scripts\analyze_observable_proxy_risk.py
python scripts\build_surrol_observable_supervisor_step4.py
python scripts\write_risk_gated_report.py
```

## Multi-Seed Reliability

```powershell
.\scripts\run_navigation_multiseed_failure_suite.ps1 -Episodes 20 -DriftStep 5
```
