param(
    [string]$SurrolRoot = "/mnt/e/RL_projects/SurRoL_clean_SR-VPPV",
    [string]$EnvPath = "/mnt/e/RL_projects/surrol_py38_env",
    [string]$MambaRoot = "/mnt/e/RL_projects/micromamba"
)

$ErrorActionPreference = "Stop"

$workdir = "$SurrolRoot/Benchmark/state_based"
$micromamba = "$MambaRoot/bin/micromamba"

$smokeScript = @"
import traceback

cases = [
    ("ECMReach", "surrol.tasks.ecm_reach", "ECMReach"),
    ("NeedleReach", "surrol.tasks.needle_reach_org", "NeedleReach"),
    ("NeedlePick", "surrol.tasks.needle_pick_org", "NeedlePick"),
    ("GauzeRetrieve", "surrol.tasks.gauze_retrieve_org", "GauzeRetrieve"),
    ("BiPegTransfer", "surrol.tasks.peg_transfer_bimanual_org", "BiPegTransfer"),
    ("NeedleRegrasp", "surrol.tasks.needle_regrasp_bimanual_org", "NeedleRegrasp"),
]

failures = []

for name, module_name, class_name in cases:
    print(f"\nCASE {name}", flush=True)
    try:
        module = __import__(module_name, fromlist=[class_name])
        env_cls = getattr(module, class_name)
        env = env_cls(render_mode=None)
        obs = env.reset()
        action = env.get_oracle_action(obs) if hasattr(env, "get_oracle_action") else env.action_space.sample()
        obs, reward, done, info = env.step(action)
        print(
            "OK",
            "obs", obs["observation"].shape,
            "action", action.shape,
            "reward", float(reward),
            "success", info.get("is_success"),
            flush=True,
        )
        if hasattr(env, "close"):
            env.close()
    except Exception as exc:
        failures.append(name)
        print("FAIL", type(exc).__name__, exc, flush=True)
        traceback.print_exc(limit=2)

if failures:
    raise SystemExit("SurRoL smoke failures: " + ", ".join(failures))

print("\nSurRoL WSL smoke suite passed.")
"@

$smokeScript | wsl --cd $workdir $micromamba run -p $EnvPath python -X faulthandler -
