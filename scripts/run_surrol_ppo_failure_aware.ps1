param(
    [string]$SurrolRoot = "/mnt/e/RL_projects/SurRoL_clean_SR-VPPV",
    [string]$EnvPath = "/mnt/e/RL_projects/surrol_py38_env",
    [string]$MambaRoot = "/mnt/e/RL_projects/micromamba",
    [string]$Task = "NeedlePickRL-v0",
    [int]$Seed = 43000,
    [int]$TotalTimesteps = 2048,
    [int]$MaxEpisodeSteps = 100,
    [string]$FailureMode = "none",
    [double]$FailureProb = 0.25,
    [string]$ObservationMode = "state",
    [double]$PseudoVisionNoise = 0.003,
    [string]$VisionCorruption = "none",
    [double]$VisionCorruptionProb = 0.0,
    [double]$VisionCorruptionSeverity = 0.25,
    [int]$VisionStride = 1,
    [int]$ProprioDim = 7,
    [int]$ImageGridSize = 4,
    [string]$ImageFeatureMode = "stats_gray",
    [string]$DangerZone = "none",
    [double]$DangerRadius = 0.052,
    [double]$DangerPenalty = 2.0,
    [double]$ProgressRewardScale = 0.0,
    [double]$ProgressClip = 0.03,
    [double]$DistanceRewardScale = 0.0,
    [double]$NearTargetActionPenalty = 0.0,
    [double]$NearTargetThreshold = 0.12,
    [int]$TorchNumThreads = 1,
    [double]$PpoLearningRate = 0.0003,
    [double]$PpoClipRange = 0.2,
    [double]$PpoEntCoef = 0.0,
    [string]$InitModel = "",
    [string]$OutDir = "/mnt/e/RL_projects/constraint_surgical_rl/runs/surrol_ppo_failure_aware",
    [switch]$CheckOnly,
    [switch]$FreezeLogStd
)

$ErrorActionPreference = "Stop"

$workdir = "$SurrolRoot/Benchmark/state_based"
$micromamba = "$MambaRoot/bin/micromamba"
$script = "/mnt/e/RL_projects/constraint_surgical_rl/scripts/train_surrol_ppo_failure_aware.py"

$argsList = @(
    "--surrol-root", $SurrolRoot,
    "--task", $Task,
    "--seed", "$Seed",
    "--total-timesteps", "$TotalTimesteps",
    "--max-episode-steps", "$MaxEpisodeSteps",
    "--failure-mode", $FailureMode,
    "--failure-prob", "$FailureProb",
    "--observation-mode", $ObservationMode,
    "--pseudo-vision-noise", "$PseudoVisionNoise",
    "--vision-corruption", $VisionCorruption,
    "--vision-corruption-prob", "$VisionCorruptionProb",
    "--vision-corruption-severity", "$VisionCorruptionSeverity",
    "--vision-stride", "$VisionStride",
    "--proprio-dim", "$ProprioDim",
    "--image-grid-size", "$ImageGridSize",
    "--image-feature-mode", $ImageFeatureMode,
    "--danger-zone", $DangerZone,
    "--danger-radius", "$DangerRadius",
    "--danger-penalty", "$DangerPenalty",
    "--progress-reward-scale", "$ProgressRewardScale",
    "--progress-clip", "$ProgressClip",
    "--distance-reward-scale", "$DistanceRewardScale",
    "--near-target-action-penalty", "$NearTargetActionPenalty",
    "--near-target-threshold", "$NearTargetThreshold",
    "--torch-num-threads", "$TorchNumThreads",
    "--ppo-learning-rate", "$PpoLearningRate",
    "--ppo-clip-range", "$PpoClipRange",
    "--ppo-ent-coef", "$PpoEntCoef",
    "--out-dir", $OutDir
)

if ($InitModel -ne "") {
    $argsList += @("--init-model", $InitModel)
}

if ($CheckOnly) {
    $argsList += "--check-only"
}

if ($FreezeLogStd) {
    $argsList += "--freeze-log-std"
}

wsl --cd $workdir $micromamba run -p $EnvPath python $script @argsList
