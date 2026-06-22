param(
    [int]$Episodes = 100,
    [string]$RunPrefix = "cmp"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".conda\python.exe"
$presets = @(
    "prototype",
    "strict",
    "needle_reach",
    "needle_insert",
    "tight_corridor",
    "tissue_retraction_proxy",
    "gauze_manipulation_proxy"
)
$variants = @(
    "conditioned",
    "conditioned_shielded",
    "conditioned_tangent_shielded"
)
$methods = @("scratch", "curriculum")
$seeds = @(0, 1, 2)

foreach ($preset in $presets) {
    $summary = Join-Path $ProjectRoot "runs\stress_${preset}_summary.csv"
    $aggregate = Join-Path $ProjectRoot "runs\stress_${preset}_aggregate_summary.csv"
    if (Test-Path $aggregate) {
        Write-Host "skip_completed_preset=$preset"
        continue
    }

    $evalCsvs = @()
    foreach ($variant in $variants) {
        foreach ($method in $methods) {
            foreach ($seed in $seeds) {
                $runDir = Join-Path $ProjectRoot "runs\${RunPrefix}_${method}_${variant}_seed${seed}"
                $modelPath = Join-Path $runDir "model"
                if (-not (Test-Path "${modelPath}.zip")) {
                    Write-Host "skip_missing_model=$modelPath"
                    continue
                }
                $evalCsv = Join-Path $runDir "eval_${preset}.csv"
                & $Python (Join-Path $ProjectRoot "scripts\evaluate_policy.py") `
                    --model $modelPath `
                    --variant $variant `
                    --config-preset $preset `
                    --episodes $Episodes `
                    --seed 3000 `
                    --out $evalCsv `
                    --deterministic
                $evalCsvs += $evalCsv
            }
        }
    }

    if ($evalCsvs.Count -gt 0) {
        & $Python (Join-Path $ProjectRoot "scripts\summarize_evals.py") $evalCsvs --out $summary
        & $Python (Join-Path $ProjectRoot "scripts\aggregate_eval_summary.py") --summary $summary --out $aggregate
    }
}

& $Python (Join-Path $ProjectRoot "scripts\write_stress_suite_report.py") `
    --runs-dir (Join-Path $ProjectRoot "runs") `
    --out (Join-Path $ProjectRoot "reports\stress_transfer_suite_report.md")
