param(
    [int]$TotalTimesteps = 10000,
    [int]$Episodes = 50,
    [string]$ConfigPreset = "prototype"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".conda\python.exe"
$variants = @("conditioned", "no_phase_budget", "conditioned_shielded")
$seeds = @(0, 1, 2)
$evalCsvs = @()

foreach ($variant in $variants) {
    foreach ($seed in $seeds) {
        $outDir = Join-Path $ProjectRoot "runs\proto_${ConfigPreset}_${variant}_seed${seed}"
        & $Python (Join-Path $ProjectRoot "scripts\train_ppo.py") `
            --variant $variant `
            --config-preset $ConfigPreset `
            --total-timesteps $TotalTimesteps `
            --seed $seed `
            --out-dir $outDir

        $evalCsv = Join-Path $outDir "eval.csv"
        & $Python (Join-Path $ProjectRoot "scripts\evaluate_policy.py") `
            --model (Join-Path $outDir "model") `
            --variant $variant `
            --config-preset $ConfigPreset `
            --episodes $Episodes `
            --seed 1000 `
            --out $evalCsv `
            --deterministic

        $evalCsvs += $evalCsv
    }
}

& $Python (Join-Path $ProjectRoot "scripts\summarize_evals.py") $evalCsvs `
    --out (Join-Path $ProjectRoot "runs\proto_${ConfigPreset}_summary.csv")

& $Python (Join-Path $ProjectRoot "scripts\aggregate_eval_summary.py") `
    --summary (Join-Path $ProjectRoot "runs\proto_${ConfigPreset}_summary.csv") `
    --out (Join-Path $ProjectRoot "runs\proto_${ConfigPreset}_aggregate_summary.csv")

& $Python (Join-Path $ProjectRoot "scripts\plot_eval_summary.py") `
    --summary (Join-Path $ProjectRoot "runs\proto_${ConfigPreset}_summary.csv") `
    --out-dir (Join-Path $ProjectRoot "runs\proto_${ConfigPreset}_plots")
