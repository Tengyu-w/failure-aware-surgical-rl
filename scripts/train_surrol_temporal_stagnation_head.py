from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from surrol_temporal_stagnation import FEATURE_NAMES, TemporalFeatureState
from train_surrol_visual_action_risk_head import average_precision, confusion, fit_logistic, roc_auc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-run", type=Path, action="append", required=True)
    parser.add_argument("--validation-run", type=Path, action="append", required=True)
    parser.add_argument("--test-run", type=Path, action="append", required=True)
    parser.add_argument("--max-episode-risk", type=float, default=0.6)
    parser.add_argument("--min-step", type=int, default=15)
    parser.add_argument("--window", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=0.03)
    parser.add_argument("--optimization-steps", type=int, default=6000)
    parser.add_argument("--l2", type=float, default=0.05)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args()


def build_run_examples(run: Path, min_step: int, window: int, max_episode_risk: float):
    episodes = pd.read_csv(run / "risk_routing_episodes.csv")
    steps = pd.read_csv(run / "risk_routing_steps.csv")
    episodes = episodes[(~episodes["deferred"].astype(bool)) & (episodes["max_risk"] < max_episode_risk)].copy()
    feature_rows = []
    episode_rows = []
    for _, episode in episodes.iterrows():
        sequence = steps[steps["episode"] == episode["episode"]].sort_values("step")
        state = TemporalFeatureState(window=window, max_steps=50)
        candidate_features = []
        for _, row in sequence.iterrows():
            high_risk = str(row["high_risk"]).lower() == "true"
            recovered = row["route"] == "auto_recovery_visual_memory"
            features = state.features(int(row["step"]), float(row["predicted_risk"]), float(row["memory_distance"]), high_risk)
            if int(row["step"]) >= min_step and high_risk and recovered:
                candidate_features.append(features)
            state.update(float(row["predicted_risk"]), high_risk, recovered)
        label = int(float(episode["success"]) < 1.0)
        for features in candidate_features:
            feature_rows.append(
                {
                    "seed": int(episode["seed"]),
                    "label": label,
                    "features": features,
                    "episode_windows": max(1, len(candidate_features)),
                }
            )
        episode_rows.append({"seed": int(episode["seed"]), "label": label, "windows": len(candidate_features)})
    return feature_rows, episode_rows


def load_split(runs: list[Path], args: argparse.Namespace):
    feature_rows = []
    episode_rows = []
    for run in runs:
        features, episodes = build_run_examples(run, args.min_step, args.window, args.max_episode_risk)
        feature_rows.extend(features)
        episode_rows.extend(episodes)
    return feature_rows, episode_rows


def episode_scores(feature_rows, episode_rows, feature_mean, feature_std, weights, bias):
    by_seed: dict[int, list[float]] = {}
    for row in feature_rows:
        x = (row["features"] - feature_mean) / feature_std
        score = float(1.0 / (1.0 + np.exp(-np.clip(float(x @ weights + bias), -40.0, 40.0))))
        by_seed.setdefault(row["seed"], []).append(score)
    labels = np.asarray([row["label"] for row in episode_rows], dtype=int)
    scores = np.asarray([max(by_seed.get(row["seed"], [0.0])) for row in episode_rows], dtype=float)
    return labels, scores


def select_threshold(labels: np.ndarray, scores: np.ndarray):
    candidates = sorted(set([0.05, *scores.tolist(), 0.95]))
    table = [confusion(labels, scores, float(value)) for value in candidates]
    eligible = [row for row in table if row["recall"] >= 1.0]
    selected = min(eligible, key=lambda row: (row["false_positive_rate"], -row["threshold"]))
    return float(selected["threshold"]), table


def metrics(labels: np.ndarray, scores: np.ndarray, threshold: float):
    result = confusion(labels, scores, threshold)
    result.update(
        {
            "episodes": int(len(labels)),
            "failures": int(labels.sum()),
            "AUROC": roc_auc(labels, scores),
            "AUPRC": average_precision(labels, scores),
        }
    )
    return result


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    train_rows, train_episodes = load_split(args.train_run, args)
    validation_rows, validation_episodes = load_split(args.validation_run, args)
    test_rows, test_episodes = load_split(args.test_run, args)
    if not train_rows or len({row["label"] for row in train_rows}) < 2:
        raise ValueError("Training windows must include successful and failed episodes")

    x = np.asarray([row["features"] for row in train_rows], dtype=np.float64)
    y = np.asarray([row["label"] for row in train_rows], dtype=float)
    feature_mean = x.mean(axis=0)
    feature_std = x.std(axis=0)
    feature_std[feature_std < 1e-8] = 1.0
    normalized = (x - feature_mean) / feature_std
    # Equalize episode contribution before class balancing in fit_logistic.
    expanded_x = []
    expanded_y = []
    max_windows = max(row["episode_windows"] for row in train_rows)
    for row, vector in zip(train_rows, normalized):
        repeats = max(1, int(round(max_windows / row["episode_windows"])))
        expanded_x.extend([vector] * repeats)
        expanded_y.extend([row["label"]] * repeats)
    weights, bias = fit_logistic(
        np.asarray(expanded_x), np.asarray(expanded_y, dtype=float), args.learning_rate, args.optimization_steps, args.l2
    )
    validation_labels, validation_scores = episode_scores(
        validation_rows, validation_episodes, feature_mean, feature_std, weights, bias
    )
    threshold, threshold_table = select_threshold(validation_labels, validation_scores)
    test_labels, test_scores = episode_scores(test_rows, test_episodes, feature_mean, feature_std, weights, bias)

    output_metrics = {
        "feature_names": FEATURE_NAMES,
        "train_episodes": len(train_episodes),
        "train_failures": int(sum(row["label"] for row in train_episodes)),
        "validation": metrics(validation_labels, validation_scores, threshold),
        "test": metrics(test_labels, test_scores, threshold),
        "threshold": threshold,
        "min_step": args.min_step,
        "window": args.window,
        "online_inputs": "risk, embedding distance, and routing history only",
    }
    np.savez_compressed(
        args.out_dir / "temporal_stagnation_head.npz",
        feature_mean=feature_mean,
        feature_std=feature_std,
        logistic_weights=weights,
        logistic_bias=np.array([bias]),
        threshold=np.array([threshold]),
        min_step=np.array([args.min_step]),
        window=np.array([args.window]),
    )
    pd.DataFrame(threshold_table).to_csv(args.out_dir / "validation_thresholds.csv", index=False)
    (args.out_dir / "temporal_stagnation_metrics.json").write_text(
        json.dumps(output_metrics, indent=2), encoding="utf-8"
    )
    print(f"model={args.out_dir / 'temporal_stagnation_head.npz'}")
    print(f"test_AUROC={output_metrics['test']['AUROC']:.4f}")
    print(f"test_recall={output_metrics['test']['recall']:.4f}")
    print(f"test_fpr={output_metrics['test']['false_positive_rate']:.4f}")


if __name__ == "__main__":
    main()
