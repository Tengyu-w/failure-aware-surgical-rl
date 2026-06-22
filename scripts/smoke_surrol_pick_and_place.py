from __future__ import annotations

import argparse
import csv
import sys
import types
from pathlib import Path

import numpy as np


def install_dummy_haptic() -> None:
    module = types.ModuleType("haptic_src._test")
    for name in [
        "initTouch_right",
        "initTouch_left",
        "startScheduler",
        "stopScheduler",
        "closeTouch_left",
        "closeTouch_right",
        "getDeviceAction_right",
        "getDeviceAction_left",
    ]:
        setattr(module, name, lambda *args, **kwargs: None)
    sys.modules["haptic_src._test"] = module


def goal_distance(obs: dict) -> float:
    return float(np.linalg.norm(np.asarray(obs["achieved_goal"]) - np.asarray(obs["desired_goal"])))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--max-steps", type=int, default=220)
    parser.add_argument("--seeds", type=int, default=3)
    args = parser.parse_args()

    install_dummy_haptic()
    from surrol.tasks.pick_and_place_org import PickAndPlace

    rows = []
    env = PickAndPlace(render_mode=None)
    try:
        for seed_idx in range(args.seeds):
            seed = 45000 + seed_idx
            np.random.seed(seed)
            env.seed(seed)
            obs = env.reset()
            initial_distance = goal_distance(obs)
            success = 0.0
            final_distance = initial_distance
            for step in range(args.max_steps):
                action = env.get_oracle_action(obs)
                obs, reward, done, info = env.step(action)
                final_distance = goal_distance(obs)
                success = float(info.get("is_success", 0.0))
                if success >= 1.0:
                    break
            rows.append(
                {
                    "task": "PickAndPlace",
                    "seed": seed,
                    "success": success,
                    "steps": step + 1,
                    "initial_distance": initial_distance,
                    "final_distance": final_distance,
                }
            )
            print(f"seed={seed} success={success} final_distance={final_distance:.4f} steps={step+1}", flush=True)
    finally:
        if hasattr(env, "close"):
            env.close()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
