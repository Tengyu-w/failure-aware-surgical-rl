param(
    [string]$EvalPreset = "strict",
    [int]$Episodes = 100,
    [string]$RunPrefix = "cmp",
    [string[]]$Variants = @("conditioned", "conditioned_shielded")
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".conda\python.exe"
$seeds = @(0, 1, 2)
$evalCsvs = @()

foreach ($variant in $Variants) {
    foreach ($method in @("scratch", "curriculum")) {
        foreach ($seed in $seeds) {
            $runDir = Join-Path $ProjectRoot "runs\${RunPrefix}_${method}_${variant}_seed${seed}"
            $modelPath = Join-Path $runDir "model"
            $evalCsv = Join-Path $runDir "eval_${EvalPreset}.csv"
            & $Python (Join-Path $ProjectRoot "scripts\evaluate_policy.py") `
                --model $modelPath `
                --variant $variant `
                --config-preset $EvalPreset `
                --episodes $Episodes `
                --seed 2000 `
                --out $evalCsv `
                --deterministic
            $evalCsvs += $evalCsv
        }
    }
}

$summary = Join-Path $ProjectRoot "runs\${RunPrefix}_${EvalPreset}_summary.csv"
$aggregate = Join-Path $ProjectRoot "runs\${RunPrefix}_${EvalPreset}_aggregate_summary.csv"
$report = Join-Path $ProjectRoot "runs\${RunPrefix}_${EvalPreset}_report.md"

& $Python (Join-Path $ProjectRoot "scripts\summarize_evals.py") $evalCsvs --out $summary
& $Python (Join-Path $ProjectRoot "scripts\aggregate_eval_summary.py") --summary $summary --out $aggregate
& $Python (Join-Path $ProjectRoot "scripts\write_experiment_report.py") --aggregate $aggregate --summary $summary --out $report

Write-Host "strict_summary=$summary"
Write-Host "strict_aggregate=$aggregate"
Write-Host "strict_report=$report"
