param(
    [int]$EasyTimesteps = 10000,
    [int]$PrototypeTimesteps = 40000,
    [int]$Episodes = 100,
    [string]$Variant = "conditioned"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".conda\python.exe"
$seeds = @(0, 1, 2)
$evalCsvs = @()

foreach ($seed in $seeds) {
    $scratchOutDir = Join-Path $ProjectRoot "runs\cmp_scratch_${Variant}_seed${seed}"
    & $Python (Join-Path $ProjectRoot "scripts\train_ppo.py") `
        --variant $Variant `
        --config-preset prototype `
        --total-timesteps ($EasyTimesteps + $PrototypeTimesteps) `
        --seed $seed `
        --out-dir $scratchOutDir `
        --verbose 0

    $scratchEval = Join-Path $scratchOutDir "eval.csv"
    & $Python (Join-Path $ProjectRoot "scripts\evaluate_policy.py") `
        --model (Join-Path $scratchOutDir "model") `
        --variant $Variant `
        --config-preset prototype `
        --episodes $Episodes `
        --seed 1000 `
        --out $scratchEval `
        --deterministic
    $evalCsvs += $scratchEval

    $curriculumOutDir = Join-Path $ProjectRoot "runs\cmp_curriculum_${Variant}_seed${seed}"
    & $Python (Join-Path $ProjectRoot "scripts\train_curriculum.py") `
        --variant $Variant `
        --seed $seed `
        --stage "easy:$EasyTimesteps" `
        --stage "prototype:$PrototypeTimesteps" `
        --out-dir $curriculumOutDir `
        --verbose 0

    $curriculumEval = Join-Path $curriculumOutDir "eval.csv"
    & $Python (Join-Path $ProjectRoot "scripts\evaluate_policy.py") `
        --model (Join-Path $curriculumOutDir "model") `
        --variant $Variant `
        --config-preset prototype `
        --episodes $Episodes `
        --seed 1000 `
        --out $curriculumEval `
        --deterministic
    $evalCsvs += $curriculumEval
}

& $Python (Join-Path $ProjectRoot "scripts\summarize_evals.py") $evalCsvs `
    --out (Join-Path $ProjectRoot "runs\cmp_${Variant}_summary.csv")

& $Python (Join-Path $ProjectRoot "scripts\aggregate_eval_summary.py") `
    --summary (Join-Path $ProjectRoot "runs\cmp_${Variant}_summary.csv") `
    --out (Join-Path $ProjectRoot "runs\cmp_${Variant}_aggregate_summary.csv")

