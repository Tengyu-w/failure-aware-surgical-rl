$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".conda\python.exe"

$variants = @("conditioned", "no_phase_budget", "conditioned_shielded")

foreach ($variant in $variants) {
    $outDir = Join-Path $ProjectRoot "runs\smoke_$variant"
    & $Python (Join-Path $ProjectRoot "scripts\train_ppo.py") `
        --variant $variant `
        --config-preset prototype `
        --total-timesteps 2048 `
        --seed 0 `
        --out-dir $outDir

    & $Python (Join-Path $ProjectRoot "scripts\evaluate_policy.py") `
        --model (Join-Path $outDir "model") `
        --variant $variant `
        --config-preset prototype `
        --episodes 20 `
        --out (Join-Path $outDir "eval.csv") `
        --deterministic
}
