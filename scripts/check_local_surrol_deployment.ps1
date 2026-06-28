param(
    [string]$RepoRoot = "E:/RL_projects/constraint_surgical_rl",
    [string]$SurrolRoot = "/mnt/e/RL_projects/SurRoL_clean_SR-VPPV",
    [string]$EnvPath = "/mnt/e/RL_projects/surrol_py38_env"
)

$ErrorActionPreference = "Stop"

function Require-Path {
    param(
        [string]$Label,
        [string]$Path
    )
    if (-not (Test-Path $Path)) {
        throw "$Label not found: $Path"
    }
    Write-Host "ok: $Label -> $Path"
}

Require-Path "project repo" $RepoRoot
Require-Path "project python" (Join-Path $RepoRoot ".conda/python.exe")
Require-Path "SurRoL source" "E:/RL_projects/SurRoL_clean_SR-VPPV"

Push-Location $RepoRoot
try {
    & .\.conda\python.exe scripts\audit_surrol_upgrade_status.py | Select-Object -First 12
}
finally {
    Pop-Location
}

$stateBased = "$SurrolRoot/Benchmark/state_based"
$python = "$EnvPath/bin/python"

wsl -e bash -lc "test -d '$stateBased' && test -x '$python'"

wsl -e bash -lc "cd '$stateBased' && export PYTHONPATH='$stateBased' && '$python' -u - <<'PY'
import pybullet as p
print('pybullet ok')
from surrol.tasks.needle_reach_org import NeedleReach
print('NeedleReach import ok')
env = NeedleReach(render_mode=None)
print('NeedleReach env created')
obs = env.reset()
print('NeedleReach reset ok:', sorted(obs.keys()))
if hasattr(env, 'close'):
    env.close()
print('SurRoL local deployment smoke passed')
PY"
