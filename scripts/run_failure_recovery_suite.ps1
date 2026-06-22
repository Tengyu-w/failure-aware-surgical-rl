param(
    [string]$Model = "runs\pilot_3d_50k_prototype_conditioned_tangent_shielded_seed0\model",
    [string]$Variant = "conditioned_tangent_shielded",
    [string]$ConfigPreset = "prototype",
    [int]$Episodes = 100,
    [int]$DriftStep = 5,
    [string]$OutPrefix = "failure_suite"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".conda\python.exe"
$ModelPath = Join-Path $ProjectRoot $Model

$failureModes = @("none", "state_target_bias", "state_dropout", "execution_slip")
$controllers = @("policy_only", "monitor_recovery", "heuristic_only")

foreach ($failureMode in $failureModes) {
    foreach ($controller in $controllers) {
        $outCsv = Join-Path $ProjectRoot "runs\${OutPrefix}_${failureMode}_${controller}.csv"
        & $Python (Join-Path $ProjectRoot "scripts\evaluate_failure_recovery.py") `
            --model $ModelPath `
            --variant $Variant `
            --config-preset $ConfigPreset `
            --controller $controller `
            --failure-mode $failureMode `
            --episodes $Episodes `
            --drift-step $DriftStep `
            --out $outCsv `
            --deterministic
    }
}

foreach ($failureMode in $failureModes) {
    & $Python (Join-Path $ProjectRoot "scripts\write_failure_recovery_report.py") `
        --failure-mode $failureMode `
        --policy-only (Join-Path $ProjectRoot "runs\${OutPrefix}_${failureMode}_policy_only.csv") `
        --monitor-recovery (Join-Path $ProjectRoot "runs\${OutPrefix}_${failureMode}_monitor_recovery.csv") `
        --heuristic-only (Join-Path $ProjectRoot "runs\${OutPrefix}_${failureMode}_heuristic_only.csv") `
        --out (Join-Path $ProjectRoot "runs\${OutPrefix}_${failureMode}_report.md")
}
