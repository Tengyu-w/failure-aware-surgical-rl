from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from train_surrol_visual_recovery_memory import (
    action_metrics,
    fit_pca,
    leave_one_out_nearest_distances,
    predict_knn,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, action="append", required=True)
    parser.add_argument("--steps", type=Path, action="append", required=True)
    parser.add_argument("--condition", action="append", default=None)
    parser.add_argument("--action-gap-threshold", type=float, default=0.25)
    parser.add_argument("--pca-components", type=int, default=32)
    parser.add_argument("--neighbors", type=int, nargs="+", default=[1, 3, 5, 9, 15])
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args()


def split_masks(seeds: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    residues = np.asarray(seeds, dtype=int) % 4
    return residues < 2, residues == 2, residues == 3


def load_parts(args: argparse.Namespace) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    if len(args.dataset) != len(args.steps):
        raise ValueError("Each --dataset requires one --steps")
    conditions = args.condition or [f"dataset_{index}" for index in range(len(args.dataset))]
    if len(conditions) != len(args.dataset):
        raise ValueError("Each --condition must match one --dataset")
    observation_parts = []
    action_parts = []
    step_parts = []
    for dataset_path, steps_path, condition in zip(args.dataset, args.steps, conditions):
        values = np.load(dataset_path)
        steps = pd.read_csv(steps_path).copy()
        observations = np.asarray(values["observations"], dtype=np.float64)
        actions = np.asarray(values["actions"], dtype=np.float64)
        if len(observations) != len(actions) or len(observations) != len(steps):
            raise ValueError(f"Dataset arrays and steps are not aligned: {dataset_path}")
        steps["condition"] = condition
        steps["source_dataset"] = str(dataset_path)
        observation_parts.append(observations)
        action_parts.append(actions)
        step_parts.append(steps)
    return (
        np.concatenate(observation_parts, axis=0),
        np.concatenate(action_parts, axis=0),
        pd.concat(step_parts, ignore_index=True),
    )


def transform(
    observations: np.ndarray,
    feature_mean: np.ndarray,
    feature_std: np.ndarray,
    pca_mean: np.ndarray,
    components: np.ndarray,
    latent_scale: np.ndarray,
) -> np.ndarray:
    standardized = (observations - feature_mean) / feature_std
    return ((standardized - pca_mean) @ components.T) / latent_scale


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    observations, actions, steps = load_parts(args)
    high_gap = steps["policy_oracle_action_l2"].to_numpy(dtype=float) >= args.action_gap_threshold
    seeds = steps["seed"].to_numpy(dtype=int)
    train_seed, validation_seed, test_seed = split_masks(seeds)
    train_mask = train_seed & high_gap
    validation_mask = validation_seed & high_gap
    test_mask = test_seed & high_gap
    if min(train_mask.sum(), validation_mask.sum(), test_mask.sum()) == 0:
        raise ValueError("Train, validation, and test splits must all contain high action-gap samples")

    inner_train_mask = train_mask
    feature_mean = observations[inner_train_mask].mean(axis=0)
    feature_std = observations[inner_train_mask].std(axis=0)
    feature_std[feature_std < 1e-8] = 1.0
    standardized_all = (observations - feature_mean) / feature_std
    pca_mean, components = fit_pca(standardized_all[inner_train_mask], args.pca_components)
    latent_all = (standardized_all - pca_mean) @ components.T
    latent_scale = latent_all[inner_train_mask].std(axis=0)
    latent_scale[latent_scale < 1e-8] = 1.0
    latent_all /= latent_scale

    validation_rows = []
    for neighbors in args.neighbors:
        predictions = predict_knn(
            latent_all[validation_mask],
            latent_all[train_mask],
            actions[train_mask],
            neighbors,
        )
        validation_rows.append({"neighbors": int(neighbors), **action_metrics(actions[validation_mask], predictions)})
    selected = min(validation_rows, key=lambda row: row["mean_action_l2"])
    selected_neighbors = int(selected["neighbors"])

    train_observations = observations[train_mask]
    train_actions = actions[train_mask]
    test_observations = observations[test_mask]
    test_actions = actions[test_mask]
    feature_mean = train_observations.mean(axis=0)
    feature_std = train_observations.std(axis=0)
    feature_std[feature_std < 1e-8] = 1.0
    standardized_train = (train_observations - feature_mean) / feature_std
    pca_mean, components = fit_pca(standardized_train, args.pca_components)
    latent_train_unscaled = (standardized_train - pca_mean) @ components.T
    latent_scale = latent_train_unscaled.std(axis=0)
    latent_scale[latent_scale < 1e-8] = 1.0
    latent_train = latent_train_unscaled / latent_scale
    latent_test = transform(test_observations, feature_mean, feature_std, pca_mean, components, latent_scale)
    test_predictions = predict_knn(latent_test, latent_train, train_actions, selected_neighbors)
    global_mean = np.repeat(train_actions.mean(axis=0, keepdims=True), len(test_actions), axis=0)
    memory_loo_distances = leave_one_out_nearest_distances(latent_train)
    max_neighbor_distance = float(np.quantile(memory_loo_distances, 0.75))

    test_metrics = action_metrics(test_actions, test_predictions)
    test_metrics.update(
        {
            "datasets": [str(path) for path in args.dataset],
            "conditions": args.condition or [],
            "total_steps": int(len(steps)),
            "total_high_action_gap_steps": int(high_gap.sum()),
            "train_memory_steps": int(train_mask.sum()),
            "validation_steps": int(validation_mask.sum()),
            "test_steps": int(test_mask.sum()),
            "train_episodes": int(steps.loc[train_mask, "seed"].nunique()),
            "validation_episodes": int(steps.loc[validation_mask, "seed"].nunique()),
            "test_episodes": int(steps.loc[test_mask, "seed"].nunique()),
            "selected_neighbors": selected_neighbors,
            "global_mean_action_l2": action_metrics(test_actions, global_mean)["mean_action_l2"],
            "action_gap_threshold": args.action_gap_threshold,
            "max_neighbor_distance": max_neighbor_distance,
            "ood_distance_quantile": 0.75,
            "split_rule": "seed_mod_4: train={0,1}, validation={2}, test={3}",
            "online_inputs": "true online adapter-space render_proprio_vision observation only",
        }
    )

    action_low = train_actions.min(axis=0)
    action_high = train_actions.max(axis=0)
    np.savez_compressed(
        args.out_dir / "visual_recovery_memory.npz",
        feature_mean=feature_mean,
        feature_std=feature_std,
        pca_mean=pca_mean,
        pca_components=components,
        latent_scale=latent_scale,
        memory_features=latent_train,
        memory_actions=train_actions,
        neighbors=np.array([selected_neighbors]),
        action_low=action_low,
        action_high=action_high,
        max_neighbor_distance=np.array([max_neighbor_distance]),
    )
    scored_steps = steps.copy()
    scored_steps["high_action_gap"] = high_gap
    scored_steps["split"] = np.select(
        [train_seed, validation_seed, test_seed],
        ["train", "validation", "test"],
        default="unknown",
    )
    scored_steps.to_csv(args.out_dir / "online_adapter_recovery_steps.csv", index=False)
    pd.DataFrame(validation_rows).to_csv(args.out_dir / "neighbor_validation.csv", index=False)
    (args.out_dir / "recovery_memory_metrics.json").write_text(
        json.dumps(test_metrics, indent=2),
        encoding="utf-8",
    )
    print(f"model={args.out_dir / 'visual_recovery_memory.npz'}")
    print(f"test_mean_action_l2={test_metrics['mean_action_l2']:.4f}")
    print(f"global_mean_action_l2={test_metrics['global_mean_action_l2']:.4f}")
    print(f"train_memory_steps={test_metrics['train_memory_steps']}")


if __name__ == "__main__":
    main()
