from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from evaluate_surrol_visual_risk_routing import env_args  # noqa: E402
from train_surrol_ppo_failure_aware import corrupt_rendered_image, image_features, make_env  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--surrol-root", type=Path, default=Path("external/SurRoL_clean_SR-VPPV"))
    parser.add_argument("--task", default="NeedleReachRL-v0")
    parser.add_argument("--seed", type=int, default=52400)
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--max-episode-steps", type=int, default=75)
    parser.add_argument("--vision-stride", type=int, default=4)
    parser.add_argument("--proprio-dim", type=int, default=7)
    parser.add_argument("--image-grid-size", type=int, default=8)
    parser.add_argument("--image-feature-mode", default="stats_rgb", choices=["stats_gray", "stats_rgb"])
    parser.add_argument("--severities", type=float, nargs="+", default=[0.15, 0.25, 0.4])
    parser.add_argument("--identity-repeats", type=int, default=3)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.vision_corruption = "none"
    args.vision_corruption_prob = 0.0
    args.vision_corruption_severity = 0.0
    args.visual_adapter = None
    config = env_args(args)
    config.pseudo_vision_noise = 0.0
    env = make_env(config)
    rng = np.random.default_rng(args.seed)
    inputs, targets, rows = [], [], []
    pair_index = 0
    for episode in range(args.episodes):
        episode_seed = args.seed + episode
        env.seed(episode_seed)
        env.reset()
        for step in range(args.max_episode_steps):
            if env.visual_frame_updated:
                raw_image = np.asarray(env._cached_rendered_image)
                clean = image_features(raw_image, rng, 0.0, args.image_grid_size, args.image_feature_mode)
                for _ in range(max(1, args.identity_repeats)):
                    inputs.append(clean)
                    targets.append(clean)
                    rows.append({"pair": pair_index, "episode": episode, "seed": episode_seed, "step": step, "corruption": "none", "severity": 0.0})
                    pair_index += 1
                for corruption in ["gaussian_noise", "brightness_shift", "occlusion"]:
                    for severity in args.severities:
                        corrupted_image, _, _ = corrupt_rendered_image(raw_image, rng, corruption, 1.0, severity)
                        corrupted = image_features(corrupted_image, rng, 0.0, args.image_grid_size, args.image_feature_mode)
                        inputs.append(corrupted)
                        targets.append(clean)
                        rows.append({"pair": pair_index, "episode": episode, "seed": episode_seed, "step": step, "corruption": corruption, "severity": severity})
                        pair_index += 1
            oracle_action = np.asarray(env.env.get_oracle_action(env.last_raw_obs), dtype=np.float32)
            _, _, done, _ = env.step(oracle_action)
            if done:
                break
    env.close()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.out_dir / "visual_corruption_pairs.npz", inputs=np.asarray(inputs, dtype=np.float32), targets=np.asarray(targets, dtype=np.float32))
    with (args.out_dir / "visual_corruption_pairs.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"pairs={len(rows)}")
    print(f"dataset={args.out_dir / 'visual_corruption_pairs.npz'}")


if __name__ == "__main__":
    main()
