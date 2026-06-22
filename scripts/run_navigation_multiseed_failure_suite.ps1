param(
    [string]$RunPrefix = "pilot_3d_50k_prototype",
    [string]$Variant = "conditioned_tangent_shielded",
    [string]$ConfigPreset = "prototype",
    [int[]]$ModelSeeds = @(0, 1, 2),
    [int]$Episodes = 20,
    [int]$DriftStep = 5,
    [string]$OutPrefix = "nav_multiseed_failure"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".conda\python.exe"

$failureModes = @("none", "state_target_bias", "state_dropout", "execution_slip")
$controllers = @("policy_only", "monitor_recovery")

foreach ($modelSeed in $ModelSeeds) {
    $modelPath = Join-Path $ProjectRoot "runs\${RunPrefix}_${Variant}_seed${modelSeed}\model"
    foreach ($failureMode in $failureModes) {
        foreach ($controller in $controllers) {
            $outCsv = Join-Path $ProjectRoot "runs\${OutPrefix}_modelseed${modelSeed}_${failureMode}_${controller}.csv"
            & $Python (Join-Path $ProjectRoot "scripts\evaluate_failure_recovery.py") `
                --model $modelPath `
                --variant $Variant `
                --config-preset $ConfigPreset `
                --controller $controller `
                --failure-mode $failureMode `
                --episodes $Episodes `
                --seed (7000 + 1000 * $modelSeed) `
                --drift-step $DriftStep `
                --out $outCsv `
                --deterministic
        }
    }
}

& $Python (Join-Path $ProjectRoot "scripts\write_navigation_multiseed_failure_report.py") `
    --prefix $OutPrefix `
    --runs-dir (Join-Path $ProjectRoot "runs") `
    --out (Join-Path $ProjectRoot "reports\navigation_multiseed_failure_report.md")
