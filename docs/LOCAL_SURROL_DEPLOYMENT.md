# Local SurRoL Deployment Runbook

This note records the local setup used on this machine to run the project
inside the open-source SurRoL/PyBullet simulator.

## Confirmed Local Paths

| Component | Path |
| --- | --- |
| Project repository | `E:\RL_projects\constraint_surgical_rl` |
| SurRoL source tree | `E:\RL_projects\SurRoL_clean_SR-VPPV` |
| SurRoL WSL path | `/mnt/e/RL_projects/SurRoL_clean_SR-VPPV` |
| SurRoL Python environment | `/mnt/e/RL_projects/surrol_py38_env` |
| Micromamba | `/mnt/e/RL_projects/micromamba/bin/micromamba` |
| Project Python | `E:\RL_projects\constraint_surgical_rl\.conda\python.exe` |

The Windows project environment is Python 3.10 and is used for repository
tests, reports, and table generation. The SurRoL simulator environment is
Python 3.8 under WSL and is used for PyBullet/Gym/Stable-Baselines3 runs.

## Verified Smoke Checks

From the project root:

```powershell
& .\.conda\python.exe scripts\audit_surrol_upgrade_status.py
& .\.conda\python.exe -m pytest -q
.\scripts\check_local_surrol_deployment.ps1
```

Expected status:

- The audit should find 10-seed SurRoL recovery rows for NeedlePick and
  GauzeRetrieve.
- The repository unit tests should pass.
- The local deployment check should import PyBullet, create a SurRoL
  `NeedleReach` environment in DIRECT/EGL mode, reset it, and close it.

SurRoL task import is slow on first run because it initializes Taichi, PyBullet,
Gym, and EGL/Mesa. A 60-120 second first import is normal on this machine.

## Running SurRoL Recovery From This Machine

Use WSL-style absolute paths when calling the SurRoL PowerShell runners, because
this repository does not contain an `external/` checkout.

Example one-seed monitor recovery smoke:

```powershell
.\scripts\run_surrol_monitor_recovery.ps1 `
  -SurrolRoot /mnt/e/RL_projects/SurRoL_clean_SR-VPPV `
  -EnvPath /mnt/e/RL_projects/surrol_py38_env `
  -MambaRoot /mnt/e/RL_projects/micromamba `
  -Task NeedleReach `
  -Failures none,action_freeze `
  -Seeds 1 `
  -Episodes 1 `
  -MaxSteps 80 `
  -EpisodeOut /mnt/e/RL_projects/constraint_surgical_rl/runs/local_needlereach_monitor_smoke.csv `
  -StepOut /mnt/e/RL_projects/constraint_surgical_rl/runs/local_needlereach_monitor_smoke_steps.csv `
  -Report /mnt/e/RL_projects/constraint_surgical_rl/reports/local_needlereach_monitor_smoke.md
```

Example PPO wrapper smoke without training:

```powershell
.\scripts\run_surrol_ppo_failure_aware.ps1 `
  -SurrolRoot /mnt/e/RL_projects/SurRoL_clean_SR-VPPV `
  -EnvPath /mnt/e/RL_projects/surrol_py38_env `
  -MambaRoot /mnt/e/RL_projects/micromamba `
  -Task NeedlePickRL-v0 `
  -ObservationMode pseudo_vision `
  -FailureMode near_target_drift `
  -OutDir /mnt/e/RL_projects/constraint_surgical_rl/runs/local_needlepick_ppo_wrapper_smoke `
  -CheckOnly
```

## Research Boundary

This is a simulator deployment, not a hardware or clinical deployment. The
current evidence supports a surgical-simulation reliability-routing prototype:
CircleRL is the minimal mechanism check, and SurRoL is the task-level migration
layer for NeedleReach, NeedlePick, GauzeRetrieve, PickAndPlace, and unsafe-zone
recovery routing.
