from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--steps", type=Path, required=True)
    parser.add_argument("--action-gap-threshold", type=float, default=0.25)
    parser.add_argument("--pca-components", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--optimization-steps", type=int, default=5000)
    parser.add_argument("--l2", type=float, default=0.02)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args()


def sigmoid(value: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(value, -40.0, 40.0)))


def roc_auc(labels: np.ndarray, scores: np.ndarray) -> float:
    positive = scores[labels == 1]
    negative = scores[labels == 0]
    if len(positive) == 0 or len(negative) == 0:
        return float("nan")
    return float(
        (positive[:, None] > negative[None, :]).mean()
        + 0.5 * (positive[:, None] == negative[None, :]).mean()
    )


def average_precision(labels: np.ndarray, scores: np.ndarray) -> float:
    order = np.argsort(-scores)
    sorted_labels = labels[order]
    positives = sorted_labels.sum()
    if positives == 0:
        return float("nan")
    precision = np.cumsum(sorted_labels) / (np.arange(len(sorted_labels)) + 1)
    return float((precision * sorted_labels).sum() / positives)


def ece(labels: np.ndarray, probabilities: np.ndarray, bins: int = 10) -> float:
    result = 0.0
    for lower in np.linspace(0.0, 1.0, bins, endpoint=False):
        upper = lower + 1.0 / bins
        mask = (probabilities >= lower) & (probabilities < upper if upper < 1.0 else probabilities <= upper)
        if mask.any():
            result += float(mask.mean()) * abs(float(probabilities[mask].mean()) - float(labels[mask].mean()))
    return result


def fit_pca(train: np.ndarray, components: int):
    mean_value = train.mean(axis=0)
    centered = train - mean_value
    _, _, vh = np.linalg.svd(centered, full_matrices=False)
    count = min(int(components), vh.shape[0])
    return mean_value, vh[:count]


def fit_logistic(x: np.ndarray, y: np.ndarray, lr: float, steps: int, l2: float):
    weights = np.zeros(x.shape[1], dtype=np.float64)
    bias = 0.0
    positive_weight = (len(y) - y.sum()) / max(1.0, y.sum())
    sample_weights = np.where(y == 1, positive_weight, 1.0)
    for _ in range(steps):
        probabilities = sigmoid(x @ weights + bias)
        error = (probabilities - y) * sample_weights
        gradient = x.T @ error / sample_weights.sum() + l2 * weights
        bias_gradient = float(error.sum() / sample_weights.sum())
        weights -= lr * gradient
        bias -= lr * bias_gradient
    return weights, bias


def confusion(labels: np.ndarray, scores: np.ndarray, threshold: float) -> dict[str, float]:
    predicted = scores >= threshold
    tp = int(((predicted == 1) & (labels == 1)).sum())
    fp = int(((predicted == 1) & (labels == 0)).sum())
    fn = int(((predicted == 0) & (labels == 1)).sum())
    tn = int(((predicted == 0) & (labels == 0)).sum())
    return {
        "threshold": threshold,
        "precision": tp / (tp + fp) if tp + fp else 0.0,
        "recall": tp / (tp + fn) if tp + fn else 0.0,
        "false_positive_rate": fp / (fp + tn) if fp + tn else 0.0,
        "coverage": (tn + fn) / len(labels),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def select_threshold(labels: np.ndarray, scores: np.ndarray) -> tuple[float, list[dict[str, float]]]:
    table = [confusion(labels, scores, float(value)) for value in np.linspace(0.05, 0.95, 19)]
    eligible = [row for row in table if row["recall"] >= 0.90]
    if not eligible:
        return 0.5, table
    selected = min(eligible, key=lambda row: (row["false_positive_rate"], -row["threshold"]))
    return float(selected["threshold"]), table


def seed_split_masks(seeds: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    residues = np.asarray(seeds, dtype=int) % 4
    return residues < 2, residues == 2, residues == 3


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    dataset = np.load(args.dataset)
    steps = pd.read_csv(args.steps)
    observations = np.asarray(dataset["observations"], dtype=np.float64)[-len(steps) :]
    if len(observations) != len(steps):
        raise ValueError("DAgger observations and step rows are not aligned")
    labels = (steps["policy_oracle_action_l2"].to_numpy(dtype=float) >= args.action_gap_threshold).astype(int)
    train_mask, validation_mask, test_mask = seed_split_masks(steps["seed"].to_numpy(dtype=int))
    for split_name, split_mask in (
        ("train", train_mask),
        ("validation", validation_mask),
        ("test", test_mask),
    ):
        if len(np.unique(labels[split_mask])) < 2:
            raise ValueError(f"{split_name} episode split must contain safe and high-gap actions")

    feature_mean = observations[train_mask].mean(axis=0)
    feature_std = observations[train_mask].std(axis=0)
    feature_std[feature_std < 1e-8] = 1.0
    standardized_train = (observations[train_mask] - feature_mean) / feature_std
    standardized_all = (observations - feature_mean) / feature_std
    pca_mean, components = fit_pca(standardized_train, args.pca_components)
    projected_all = (standardized_all - pca_mean) @ components.T
    projected_train = projected_all[train_mask]
    latent_mean = projected_train.mean(axis=0)
    latent_std = projected_train.std(axis=0)
    latent_std[latent_std < 1e-8] = 1.0
    normalized_all = (projected_all - latent_mean) / latent_std
    weights, bias = fit_logistic(
        normalized_all[train_mask],
        labels[train_mask].astype(float),
        args.learning_rate,
        args.optimization_steps,
        args.l2,
    )
    probabilities = sigmoid(normalized_all @ weights + bias)
    selected_threshold, validation_threshold_table = select_threshold(
        labels[validation_mask], probabilities[validation_mask]
    )
    test_metrics = confusion(labels[test_mask], probabilities[test_mask], selected_threshold)
    validation_metrics = confusion(
        labels[validation_mask], probabilities[validation_mask], selected_threshold
    )
    test_metrics.update(
        {
            "test_steps": int(test_mask.sum()),
            "test_episodes": int(steps.loc[test_mask, "seed"].nunique()),
            "test_positive_rate": float(labels[test_mask].mean()),
            "AUROC": roc_auc(labels[test_mask], probabilities[test_mask]),
            "AUPRC": average_precision(labels[test_mask], probabilities[test_mask]),
            "Brier": float(np.mean((probabilities[test_mask] - labels[test_mask]) ** 2)),
            "ECE": ece(labels[test_mask], probabilities[test_mask]),
            "action_gap_threshold": args.action_gap_threshold,
            "selected_risk_threshold": selected_threshold,
            "split_rule": "seed_mod_4: train={0,1}, validation={2}, test={3}",
            "validation": validation_metrics,
        }
    )

    scored = steps.copy()
    scored["high_oracle_correction"] = labels
    scored["predicted_action_risk"] = probabilities
    scored["split"] = np.select(
        [train_mask, validation_mask, test_mask],
        ["train_seed_mod_0_1", "validation_seed_mod_2", "test_seed_mod_3"],
        default="unknown",
    )
    scored.to_csv(args.out_dir / "risk_scored_steps.csv", index=False)
    with (args.out_dir / "validation_thresholds.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(validation_threshold_table[0].keys()))
        writer.writeheader()
        writer.writerows(validation_threshold_table)
    np.savez_compressed(
        args.out_dir / "visual_action_risk_head.npz",
        feature_mean=feature_mean,
        feature_std=feature_std,
        pca_mean=pca_mean,
        pca_components=components,
        latent_mean=latent_mean,
        latent_std=latent_std,
        logistic_weights=weights,
        logistic_bias=np.array([bias]),
        action_gap_threshold=np.array([args.action_gap_threshold]),
        risk_threshold=np.array([selected_threshold]),
    )
    (args.out_dir / "risk_head_metrics.json").write_text(json.dumps(test_metrics, indent=2), encoding="utf-8")
    print(f"model={args.out_dir / 'visual_action_risk_head.npz'}")
    print(f"metrics={args.out_dir / 'risk_head_metrics.json'}")
    print(f"test_AUROC={test_metrics['AUROC']:.4f}")
    print(f"test_recall={test_metrics['recall']:.4f}")


if __name__ == "__main__":
    main()
