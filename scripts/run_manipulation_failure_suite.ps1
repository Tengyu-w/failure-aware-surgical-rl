param(
    [string]$Variant = "conditioned_tangent_shielded",
    [int]$Episodes = 100,
    [int]$FailureStep = 5,
    [double]$BiasMagnitude = 0.45,
    [double]$SlipScale = 0.20,
    [int]$ContactLossDelay = 6,
    [int]$RecoverySteps = 18,
    [string]$OutPrefix = "manip_failure",
    [string]$ReportOut = "runs\manipulation_failure_report.md"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".conda\python.exe"

$failureModes = @("none", "object_state_bias", "object_dropout", "execution_slip", "contact_loss")
$controllers = @("base_controller", "monitor_recovery")
$controllerFileNames = @{
    "base_controller" = "base"
    "monitor_recovery" = "monitor"
}
$failureFileNames = @{
    "object_state_bias" = "object_bias"
}

foreach ($failureMode in $failureModes) {
    foreach ($controller in $controllers) {
        $failureFileName = $failureFileNames[$failureMode]
        if ($null -eq $failureFileName) {
            $failureFileName = $failureMode
        }
        $controllerFileName = $controllerFileNames[$controller]
        $outCsv = Join-Path $ProjectRoot "runs\${OutPrefix}_${failureFileName}_${controllerFileName}.csv"
        & $Python (Join-Path $ProjectRoot "scripts\evaluate_manipulation_failure_recovery.py") `
            --variant $Variant `
            --failure-mode $failureMode `
            --controller $controller `
            --episodes $Episodes `
            --failure-step $FailureStep `
            --bias-magnitude $BiasMagnitude `
            --slip-scale $SlipScale `
            --contact-loss-delay $ContactLossDelay `
            --recovery-steps $RecoverySteps `
            --out $outCsv
    }
}

& $Python (Join-Path $ProjectRoot "scripts\write_manipulation_failure_report.py") `
    --prefix $OutPrefix `
    --runs-dir (Join-Path $ProjectRoot "runs") `
    --out (Join-Path $ProjectRoot $ReportOut)
