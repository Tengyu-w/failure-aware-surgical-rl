from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FEATURES = [
    "distance_to_goal",
    "distance_to_forbidden",
    "force_proxy",
    "remaining_budget",
    "normalized_time",
    "progress_5",
    "action_norm",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train interpretable risk heads for tangent-shield gating.")
    parser.add_argument("--data", type=Path, default=ROOT / "outputs" / "risk_dataset" / "risk_dataset.csv")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "outputs" / "risk_model")
    parser.add_argument("--test-size", type=float, default=0.25)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--logistic-steps", type=int, default=3000)
    parser.add_argument("--logistic-lr", type=float, default=0.08)
    return parser.parse_args()


def split_indices(df: pd.DataFrame, args: argparse.Namespace) -> tuple[np.ndarray, np.ndarray, str]:
    rng = np.random.default_rng(args.random_state)
    if "episode_id" in df and df["episode_id"].nunique() >= 3:
        groups = df["episode_id"].astype(str).to_numpy()
        unique_groups = np.unique(groups)
        rng.shuffle(unique_groups)
        n_test_groups = max(1, int(round(len(unique_groups) * args.test_size)))
        test_groups = set(unique_groups[:n_test_groups])
        test_mask = np.array([group in test_groups for group in groups])
        train_idx = np.flatnonzero(~test_mask)
        test_idx = np.flatnonzero(test_mask)
        if len(train_idx) > 0 and len(test_idx) > 0:
            return train_idx, test_idx, "group_shuffle_by_episode_id"

    indices = np.arange(len(df))
    rng.shuffle(indices)
    n_test = max(1, int(round(len(indices) * args.test_size)))
    return indices[n_test:], indices[:n_test], "row_shuffle_fallback"


def sigmoid(z: np.ndarray) -> np.ndarray:
    z = np.clip(z, -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-z))


def fit_logistic_numpy(
    X: np.ndarray, y: np.ndarray, steps: int, lr: float, l2: float = 1e-3
) -> dict[str, np.ndarray | float]:
    mean = X.mean(axis=0)
    scale = X.std(axis=0)
    scale = np.where(scale > 1e-8, scale, 1.0)
    Xs = (X - mean) / scale
    Xb = np.column_stack([Xs, np.ones(len(Xs))])

    n_pos = max(int((y == 1).sum()), 1)
    n_neg = max(int((y == 0).sum()), 1)
    sample_weight = np.where(y == 1, len(y) / (2.0 * n_pos), len(y) / (2.0 * n_neg))
    weights = np.zeros(Xb.shape[1], dtype=np.float64)

    for _ in range(steps):
        pred = sigmoid(Xb @ weights)
        error = (pred - y) * sample_weight
        grad = Xb.T @ error / len(Xb)
        grad[:-1] += l2 * weights[:-1]
        weights -= lr * grad

    return {
        "mean": mean,
        "scale": scale,
        "coef": weights[:-1],
        "intercept": float(weights[-1]),
    }


def predict_logistic_numpy(model: dict[str, np.ndarray | float], X: np.ndarray) -> np.ndarray:
    mean = np.asarray(model["mean"], dtype=np.float64)
    scale = np.asarray(model["scale"], dtype=np.float64)
    coef = np.asarray(model["coef"], dtype=np.float64)
    intercept = float(model["intercept"])
    return sigmoid(((X - mean) / np.maximum(scale, 1e-8)) @ coef + intercept)


def gini(y: np.ndarray) -> float:
    if len(y) == 0:
        return 0.0
    p = float(y.mean())
    return 1.0 - p * p - (1.0 - p) * (1.0 - p)


def fit_tree_numpy(
    X: np.ndarray, y: np.ndarray, feature_names: list[str], depth: int = 3, min_leaf: int = 20
) -> dict:
    node = {"prob": float(y.mean()), "samples": int(len(y)), "positives": int(y.sum())}
    if depth <= 0 or len(y) < 2 * min_leaf or len(np.unique(y)) < 2:
        return node

    parent = gini(y)
    best = None
    for feature_idx, feature_name in enumerate(feature_names):
        values = X[:, feature_idx]
        finite = values[np.isfinite(values)]
        if len(np.unique(finite)) < 2:
            continue
        thresholds = np.unique(np.quantile(finite, np.linspace(0.1, 0.9, 9)))
        for threshold in thresholds:
            left = values <= threshold
            right = ~left
            if left.sum() < min_leaf or right.sum() < min_leaf:
                continue
            score = (left.mean() * gini(y[left])) + (right.mean() * gini(y[right]))
            gain = parent - score
            if best is None or gain > best["gain"]:
                best = {
                    "gain": gain,
                    "feature_idx": feature_idx,
                    "feature": feature_name,
                    "threshold": float(threshold),
                    "left": left,
                    "right": right,
                }

    if best is None or best["gain"] <= 1e-9:
        return node

    node.update(
        {
            "feature_idx": int(best["feature_idx"]),
            "feature": best["feature"],
            "threshold": float(best["threshold"]),
            "gain": float(best["gain"]),
            "left": fit_tree_numpy(X[best["left"]], y[best["left"]], feature_names, depth - 1, min_leaf),
            "right": fit_tree_numpy(X[best["right"]], y[best["right"]], feature_names, depth - 1, min_leaf),
        }
    )
    return node


def predict_tree_numpy(tree: dict, X: np.ndarray) -> np.ndarray:
    out = np.zeros(len(X), dtype=np.float64)
    for idx, row in enumerate(X):
        node = tree
        while "feature_idx" in node:
            if row[node["feature_idx"]] <= node["threshold"]:
                node = node["left"]
            else:
                node = node["right"]
        out[idx] = float(node["prob"])
    return out


def tree_rules(tree: dict, indent: str = "") -> str:
    if "feature" not in tree:
        return f"{indent}risk_prob={tree['prob']:.3f} samples={tree['samples']} positives={tree['positives']}\n"
    left = tree_rules(tree["left"], indent + "|   ")
    right = tree_rules(tree["right"], indent + "|   ")
    return (
        f"{indent}|--- {tree['feature']} <= {tree['threshold']:.6f}\n"
        f"{left}"
        f"{indent}|--- {tree['feature']} >  {tree['threshold']:.6f}\n"
        f"{right}"
    )


def roc_auc(y_true: np.ndarray, prob: np.ndarray) -> float | None:
    n_pos = int((y_true == 1).sum())
    n_neg = int((y_true == 0).sum())
    if n_pos == 0 or n_neg == 0:
        return None
    ranks = pd.Series(prob).rank(method="average").to_numpy()
    pos_rank_sum = ranks[y_true == 1].sum()
    return float((pos_rank_sum - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def average_precision(y_true: np.ndarray, prob: np.ndarray) -> float | None:
    n_pos = int((y_true == 1).sum())
    if n_pos == 0:
        return None
    order = np.argsort(-prob)
    sorted_y = y_true[order]
    tp = np.cumsum(sorted_y == 1)
    fp = np.cumsum(sorted_y == 0)
    precision = tp / np.maximum(tp + fp, 1)
    recall = tp / n_pos
    recall_prev = np.concatenate([[0.0], recall[:-1]])
    return float(np.sum((recall - recall_prev) * precision))


def safe_metrics(y_true: np.ndarray, prob: np.ndarray, pred: np.ndarray) -> dict[str, float | None]:
    tp = int(((y_true == 1) & (pred == 1)).sum())
    fp = int(((y_true == 0) & (pred == 1)).sum())
    fn = int(((y_true == 1) & (pred == 0)).sum())
    tn = int(((y_true == 0) & (pred == 0)).sum())
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2.0 * precision * recall / max(precision + recall, 1e-12)
    return {
        "auroc": roc_auc(y_true, prob),
        "aupr": average_precision(y_true, prob),
        "f1": float(f1),
        "precision": float(precision),
        "recall": float(recall),
        "false_safe_rate": float(fn / max(tp + fn, 1)),
        "false_alarm_rate": float(fp / max(fp + tn, 1)),
    }


def threshold_sweep(y_true: np.ndarray, prob: np.ndarray) -> pd.DataFrame:
    rows = []
    for threshold in np.round(np.arange(0.1, 0.91, 0.05), 2):
        pred = (prob >= threshold).astype(int)
        metric = safe_metrics(y_true, prob, pred)
        metric["threshold"] = float(threshold)
        metric["intervention_rate"] = float(pred.mean())
        rows.append(metric)
    return pd.DataFrame(rows)


def save_logistic_model(model: dict[str, np.ndarray | float], out_path: Path) -> None:
    payload = {
        "model_type": "standardized_logistic_regression_numpy",
        "features": FEATURES,
        "mean": [float(value) for value in np.asarray(model["mean"], dtype=np.float64)],
        "scale": [float(value) if value > 0 else 1.0 for value in np.asarray(model["scale"], dtype=np.float64)],
        "coef": [float(value) for value in np.asarray(model["coef"], dtype=np.float64)],
        "intercept": float(model["intercept"]),
    }
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(args.data)
    missing = [feature for feature in FEATURES if feature not in df.columns]
    if missing:
        raise ValueError(f"Risk dataset is missing required features: {missing}")
    if "risk_label" not in df.columns:
        raise ValueError("Risk dataset must include risk_label.")

    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=[*FEATURES, "risk_label"]).copy()
    df["risk_label"] = df["risk_label"].astype(int)
    if df["risk_label"].nunique() < 2:
        raise ValueError("risk_label has one class only; add more rollouts or adjust weak labeling thresholds.")

    train_idx, test_idx, split_strategy = split_indices(df, args)
    X_train = df.iloc[train_idx][FEATURES].to_numpy(dtype=np.float64)
    y_train = df.iloc[train_idx]["risk_label"].to_numpy(dtype=int)
    X_test = df.iloc[test_idx][FEATURES].to_numpy(dtype=np.float64)
    y_test = df.iloc[test_idx]["risk_label"].to_numpy(dtype=int)

    logistic = fit_logistic_numpy(X_train, y_train, steps=args.logistic_steps, lr=args.logistic_lr)
    logistic_prob = predict_logistic_numpy(logistic, X_test)
    logistic_pred = (logistic_prob >= args.threshold).astype(int)

    min_leaf = max(5, min(50, len(train_idx) // 100))
    tree = fit_tree_numpy(X_train, y_train, FEATURES, depth=3, min_leaf=min_leaf)
    tree_prob = predict_tree_numpy(tree, X_test)
    tree_pred = (tree_prob >= args.threshold).astype(int)

    metrics = {
        "data_path": str(args.data),
        "implementation": "numpy_logistic_and_greedy_depth3_tree",
        "split_strategy": split_strategy,
        "features": FEATURES,
        "threshold": args.threshold,
        "n_rows": int(len(df)),
        "n_train": int(len(train_idx)),
        "n_test": int(len(test_idx)),
        "positive_rate_all": float(df["risk_label"].mean()),
        "positive_rate_train": float(y_train.mean()),
        "positive_rate_test": float(y_test.mean()),
        "logistic": safe_metrics(y_test, logistic_prob, logistic_pred),
        "decision_tree": safe_metrics(y_test, tree_prob, tree_pred),
    }
    with (args.out_dir / "risk_model_metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)

    coefficients = pd.DataFrame(
        {
            "feature": FEATURES,
            "coefficient": np.asarray(logistic["coef"], dtype=np.float64),
            "abs_coefficient": np.abs(np.asarray(logistic["coef"], dtype=np.float64)),
        }
    ).sort_values("abs_coefficient", ascending=False)
    coefficients.to_csv(args.out_dir / "logistic_coefficients.csv", index=False)

    rules = tree_rules(tree)
    (args.out_dir / "decision_tree_rules.txt").write_text(rules, encoding="utf-8")
    save_logistic_model(logistic, args.out_dir / "risk_model.json")

    predictions = df.iloc[test_idx].copy()
    predictions["risk_prob_logistic"] = logistic_prob
    predictions["risk_pred_logistic"] = logistic_pred
    predictions["risk_prob_tree"] = tree_prob
    predictions["risk_pred_tree"] = tree_pred
    predictions.to_csv(args.out_dir / "risk_score_predictions.csv", index=False)

    sweep = threshold_sweep(y_test, logistic_prob)
    sweep.to_csv(args.out_dir / "risk_threshold_sweep.csv", index=False)

    print(json.dumps(metrics, indent=2))
    print("\nDecision tree rules:\n")
    print(rules)
    print(f"saved_model={args.out_dir / 'risk_model.json'}")


if __name__ == "__main__":
    main()
