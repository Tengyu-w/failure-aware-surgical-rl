param(
    [int]$TotalTimesteps = 1024,
    [int]$Episodes = 10,
    [string]$ConfigPreset = "prototype"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".conda\python.exe"

$variants = @(
    "conditioned",
    "no_phase_budget",
    "conditioned_shielded",
    "conditioned_tangent_shielded"
)
$evalCsvs = @()

foreach ($variant in $variants) {
    $outDir = Join-Path $ProjectRoot "runs\smoke_3d_${variant}"
    & $Python (Join-Path $ProjectRoot "scripts\train_ppo.py") `
        --variant $variant `
        --config-preset $ConfigPreset `
        --total-timesteps $TotalTimesteps `
        --seed 0 `
        --out-dir $outDir `
        --verbose 0

    $evalCsv = Join-Path $outDir "eval.csv"
    & $Python (Join-Path $ProjectRoot "scripts\evaluate_policy.py") `
        --model (Join-Path $outDir "model") `
        --variant $variant `
        --config-preset $ConfigPreset `
        --episodes $Episodes `
        --out $evalCsv `
        --deterministic

    $evalCsvs += $evalCsv
}

& $Python (Join-Path $ProjectRoot "scripts\summarize_evals.py") $evalCsvs `
    --out (Join-Path $ProjectRoot "runs\smoke_3d_summary.csv")
