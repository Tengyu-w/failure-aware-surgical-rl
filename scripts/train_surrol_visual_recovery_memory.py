from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--steps", type=Path, required=True)
    parser.add_argument("--augmentation-dataset", type=Path, action="append", default=[])
    parser.add_argument("--augmentation-steps", type=Path, action="append", default=[])
    parser.add_argument("--action-gap-threshold", type=float, default=0.25)
    parser.add_argument("--pca-components", type=int, default=32)
    parser.add_argument("--neighbors", type=int, nargs="+", default=[1, 3, 5, 9, 15])
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args()


def fit_pca(train: np.ndarray, components: int) -> tuple[np.ndarray, np.ndarray]:
    mean_value = train.mean(axis=0)
    _, _, vh = np.linalg.svd(train - mean_value, full_matrices=False)
    return mean_value, vh[: min(int(components), vh.shape[0])]


def predict_knn(
    queries: np.ndarray,
    memory_features: np.ndarray,
    memory_actions: np.ndarray,
    neighbors: int,
) -> np.ndarray:
    queries = np.atleast_2d(np.asarray(queries, dtype=np.float64))
    memory_features = np.asarray(memory_features, dtype=np.float64)
    memory_actions = np.asarray(memory_actions, dtype=np.float64)
    if len(memory_features) == 0:
        raise ValueError("Recovery memory is empty")
    k = min(max(1, int(neighbors)), len(memory_features))
    predictions = []
    for query in queries:
        squared_distances = np.sum((memory_features - query) ** 2, axis=1)
        indices = np.argpartition(squared_distances, k - 1)[:k]
        distances = np.sqrt(np.maximum(squared_distances[indices], 0.0))
        weights = 1.0 / np.maximum(distances, 1e-6)
        weights /= weights.sum()
        predictions.append(weights @ memory_actions[indices])
    return np.asarray(predictions, dtype=np.float32)


def nearest_distances(queries: np.ndarray, memory_features: np.ndarray) -> np.ndarray:
    queries = np.atleast_2d(np.asarray(queries, dtype=np.float64))
    memory_features = np.asarray(memory_features, dtype=np.float64)
    return np.asarray(
        [np.sqrt(np.min(np.sum((memory_features - query) ** 2, axis=1))) for query in queries],
        dtype=np.float64,
    )


def leave_one_out_nearest_distances(memory_features: np.ndarray) -> np.ndarray:
    memory_features = np.asarray(memory_features, dtype=np.float64)
    if len(memory_features) < 2:
        raise ValueError("At least two recovery memories are required for OOD calibration")
    squared = np.sum((memory_features[:, None, :] - memory_features[None, :, :]) ** 2, axis=2)
    np.fill_diagonal(squared, np.inf)
    return np.sqrt(np.min(squared, axis=1))


def action_metrics(targets: np.ndarray, predictions: np.ndarray) -> dict[str, float]:
    errors = np.asarray(predictions) - np.asarray(targets)
    return {
        "mean_action_l2": float(np.linalg.norm(errors, axis=1).mean()),
        "median_action_l2": float(np.median(np.linalg.norm(errors, axis=1))),
        "action_rmse": float(np.sqrt(np.mean(errors**2))),
    }


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    dataset = np.load(args.dataset)
    steps = pd.read_csv(args.steps)
    observations = np.asarray(dataset["observations"], dtype=np.float64)[-len(steps) :]
    actions = np.asarray(dataset["actions"], dtype=np.float64)[-len(steps) :]
    if len(observations) != len(steps) or len(actions) != len(steps):
        raise ValueError("DAgger observations, actions, and step rows are not aligned")

    high_risk = steps["policy_oracle_action_l2"].to_numpy(dtype=float) >= args.action_gap_threshold
    seeds = steps["seed"].to_numpy(dtype=int)
    train_mask = (seeds % 2 == 0) & high_risk
    test_mask = (seeds % 2 == 1) & high_risk
    inner_train_mask = train_mask & (seeds % 4 == 0)
    validation_mask = train_mask & (seeds % 4 == 2)
    if min(train_mask.sum(), test_mask.sum(), inner_train_mask.sum(), validation_mask.sum()) == 0:
        raise ValueError("Episode split must contain high-risk samples in train, validation, and test")

    augmentation_observations = np.empty((0, observations.shape[1]), dtype=np.float64)
    augmentation_actions = np.empty((0, actions.shape[1]), dtype=np.float64)
    if len(args.augmentation_dataset) != len(args.augmentation_steps):
        raise ValueError("Each --augmentation-dataset requires one --augmentation-steps")
    augmentation_observation_parts = []
    augmentation_action_parts = []
    for dataset_path, steps_path in zip(args.augmentation_dataset, args.augmentation_steps):
        augmentation = np.load(dataset_path)
        augmentation_step_rows = pd.read_csv(steps_path)
        part_observations = np.asarray(augmentation["observations"], dtype=np.float64)
        part_actions = np.asarray(augmentation["actions"], dtype=np.float64)
        if len(part_observations) != len(augmentation_step_rows):
            raise ValueError(f"Augmentation observations and steps are not aligned: {dataset_path}")
        part_high_risk = (
            augmentation_step_rows["policy_oracle_action_l2"].to_numpy(dtype=float) >= args.action_gap_threshold
        )
        augmentation_observation_parts.append(part_observations[part_high_risk])
        augmentation_action_parts.append(part_actions[part_high_risk])
    if augmentation_observation_parts:
        augmentation_observations = np.concatenate(augmentation_observation_parts, axis=0)
        augmentation_actions = np.concatenate(augmentation_action_parts, axis=0)

    feature_mean = observations[inner_train_mask].mean(axis=0)
    feature_std = observations[inner_train_mask].std(axis=0)
    feature_std[feature_std < 1e-8] = 1.0
    standardized = (observations - feature_mean) / feature_std
    pca_mean, components = fit_pca(standardized[inner_train_mask], args.pca_components)
    latent = (standardized - pca_mean) @ components.T
    latent_scale = latent[inner_train_mask].std(axis=0)
    latent_scale[latent_scale < 1e-8] = 1.0
    latent /= latent_scale

    validation_rows = []
    for neighbors in args.neighbors:
        predictions = predict_knn(
            latent[validation_mask], latent[inner_train_mask], actions[inner_train_mask], neighbors
        )
        validation_rows.append({"neighbors": int(neighbors), **action_metrics(actions[validation_mask], predictions)})
    selected = min(validation_rows, key=lambda row: row["mean_action_l2"])
    selected_neighbors = int(selected["neighbors"])

    # Refit on even-seed base episodes plus targeted OOD data; odd base seeds remain untouched.
    train_observations = np.concatenate([observations[train_mask], augmentation_observations], axis=0)
    train_actions = np.concatenate([actions[train_mask], augmentation_actions], axis=0)
    test_observations = observations[test_mask]
    test_actions = actions[test_mask]
    feature_mean = train_observations.mean(axis=0)
    feature_std = train_observations.std(axis=0)
    feature_std[feature_std < 1e-8] = 1.0
    standardized_train = (train_observations - feature_mean) / feature_std
    standardized_test = (test_observations - feature_mean) / feature_std
    pca_mean, components = fit_pca(standardized_train, args.pca_components)
    latent_train = (standardized_train - pca_mean) @ components.T
    latent_test = (standardized_test - pca_mean) @ components.T
    latent_scale = latent_train.std(axis=0)
    latent_scale[latent_scale < 1e-8] = 1.0
    latent_train /= latent_scale
    latent_test /= latent_scale
    memory_loo_distances = leave_one_out_nearest_distances(latent_train)
    max_neighbor_distance = float(np.quantile(memory_loo_distances, 0.75))
    test_predictions = predict_knn(latent_test, latent_train, train_actions, selected_neighbors)
    test_metrics = action_metrics(test_actions, test_predictions)
    global_mean = np.repeat(train_actions.mean(axis=0, keepdims=True), len(test_actions), axis=0)
    test_metrics.update(
        {
            "test_steps": int(test_mask.sum()),
            "test_episodes": int(np.unique(seeds[test_mask]).size),
            "train_memory_steps": int(len(train_observations)),
            "augmentation_steps": int(len(augmentation_observations)),
            "selected_neighbors": selected_neighbors,
            "global_mean_action_l2": action_metrics(test_actions, global_mean)["mean_action_l2"],
            "action_gap_threshold": args.action_gap_threshold,
            "max_neighbor_distance": max_neighbor_distance,
            "ood_distance_quantile": 0.75,
            "online_inputs": "render_proprio_vision observation only",
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
    pd.DataFrame(validation_rows).to_csv(args.out_dir / "neighbor_validation.csv", index=False)
    (args.out_dir / "recovery_memory_metrics.json").write_text(
        json.dumps(test_metrics, indent=2), encoding="utf-8"
    )
    print(f"model={args.out_dir / 'visual_recovery_memory.npz'}")
    print(f"test_mean_action_l2={test_metrics['mean_action_l2']:.4f}")
    print(f"global_mean_action_l2={test_metrics['global_mean_action_l2']:.4f}")


if __name__ == "__main__":
    main()
