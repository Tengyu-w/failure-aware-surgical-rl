from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from surrol.tasks.needle_regrasp_bimanual_org import NeedleRegrasp
from surrol.utils.pybullet_utils import get_link_pose


def goal_distance(obs: dict) -> float:
    return float(np.linalg.norm(np.asarray(obs["achieved_goal"]) - np.asarray(obs["desired_goal"])))


def pose_distance(pos, goal) -> float:
    return float(np.linalg.norm(np.asarray(pos) - np.asarray(goal)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, default=43000)
    parser.add_argument("--max-steps", type=int, default=260)
    parser.add_argument("--variant", choices=["bimanual_org", "full_dof"], default="bimanual_org")
    args = parser.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    np.random.seed(args.seed)
    if args.variant == "bimanual_org":
        env_cls = NeedleRegrasp
    else:
        from surrol.tasks.needle_regrasp import NeedleRegraspFullDof

        env_cls = NeedleRegraspFullDof
    env = env_cls(render_mode=None)
    rows = []
    try:
        env.seed(args.seed)
        obs = env.reset()
        initial_distance = goal_distance(obs)
        action0 = env.get_oracle_action(obs)
        print(
            "reset_ok",
            f"obs_dim={len(obs['observation'])}",
            f"goal_dim={len(obs['desired_goal'])}",
            f"action_dim={len(action0)}",
            f"initial_distance={initial_distance:.4f}",
            flush=True,
        )

        success = 0.0
        final_distance = initial_distance
        for step in range(args.max_steps):
            action = env.get_oracle_action(obs)
            obs, reward, done, info = env.step(action)
            distance = goal_distance(obs)
            success = float(info.get("is_success", 0.0))
            final_distance = distance
            rows.append(
                {
                    "task": "NeedleRegrasp",
                    "variant": args.variant,
                    "seed": args.seed,
                    "step": step,
                    "success": success,
                    "distance": distance,
                    "achieved_x": float(obs["achieved_goal"][0]),
                    "achieved_y": float(obs["achieved_goal"][1]),
                    "achieved_z": float(obs["achieved_goal"][2]),
                    "goal_x": float(obs["desired_goal"][0]),
                    "goal_y": float(obs["desired_goal"][1]),
                    "goal_z": float(obs["desired_goal"][2]),
                    "link1_goal_distance": pose_distance(get_link_pose(env.obj_id, env.obj_link1)[0], obs["desired_goal"]),
                    "link2_goal_distance": pose_distance(get_link_pose(env.obj_id, env.obj_link2)[0], obs["desired_goal"]),
                    "psm1_goal_distance": pose_distance(env.psm1.pose_rcm2world(env.psm1.get_current_position(), "tuple")[0], obs["desired_goal"]),
                    "psm2_goal_distance": pose_distance(env.psm2.pose_rcm2world(env.psm2.get_current_position(), "tuple")[0], obs["desired_goal"]),
                    "reward": float(reward),
                    "action_dim": len(action),
                    "action_norm": float(np.linalg.norm(action)),
                    "active_waypoint": next(
                        (idx for idx, waypoint in enumerate(getattr(env, "_waypoints", [])) if waypoint is not None),
                        -1,
                    ),
                }
            )
            if step < 5 or success >= 1.0:
                print(
                    "step",
                    step,
                    "success",
                    success,
                    "distance",
                    f"{distance:.4f}",
                    "active_waypoint",
                    rows[-1]["active_waypoint"],
                    flush=True,
                )
            if success >= 1.0:
                break
    finally:
        if hasattr(env, "close"):
            env.close()

    if rows:
        with out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    print(
        f"csv={out}",
        f"steps={len(rows)}",
        f"success={success}",
        f"final_distance={final_distance:.4f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
