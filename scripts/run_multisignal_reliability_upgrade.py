from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "reports" / "tables"
FIGURES = ROOT / "reports" / "figures" / "multisignal_reliability_upgrade"
REPORT = ROOT / "reports" / "multisignal_reliability_upgrade.md"

ROUTES = ["auto_execute", "auto_recovery", "human_review", "abort_candidate"]

FEATURE_GROUPS = {
    "progress": [
        "steps",
        "final_distance",
        "min_distance",
        "distance_reduction",
        "risk_event_rate",
    ],
    "action": [
        "max_triage_risk",
        "first_action_anomaly_signal",
        "monitor_triggers",
        "recovery_override_rate",
    ],
    "visual": [
        "first_perception_uncertain_signal",
        "visual_reestimate_triggers",
        "learned_review_risk",
    ],
    "contact": [
        "first_grasp_uncertain_signal",
        "recovery_phase_replans",
        "recovery_replans",
    ],
    "boundary": [
        "unsafe_warning_events",
        "unsafe_abort",
        "inverse_min_danger_distance",
    ],
    "representation_proxy": [
        "learned_review_risk",
        "max_triage_risk",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a multi-signal reliability head and mechanism router for the SurRoL reliability logs."
    )
    parser.add_argument(
        "--scored-episodes",
        type=Path,
        default=TABLES / "surrol_learned_risk_head_scored.csv",
    )
    parser.add_argument("--out-dir", type=Path, default=TABLES)
    parser.add_argument("--figure-dir", type=Path, default=FIGURES)
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--route-steps", type=Path, default=TABLES / "surrol_risk_triage_scored_steps.csv")
    parser.add_argument(
        "--visual-risk-metrics",
        type=Path,
        default=ROOT
        / "runs"
        / "surrol_visual_dagger_round31_seed50710"
        / "visual_action_risk_head"
        / "risk_head_metrics.json",
    )
    parser.add_argument(
        "--visual-memory-metrics",
        type=Path,
        default=ROOT
        / "runs"
        / "surrol_visual_dagger_round31_seed50710"
        / "visual_recovery_memory"
        / "recovery_memory_metrics.json",
    )
    parser.add_argument(
        "--visual-adapter-metrics",
        type=Path,
        default=ROOT / "runs" / "surrol_visual_denoising_adapter_round40_strict_split" / "adapter_metrics.json",
    )
    return parser.parse_args()


def sigmoid(value: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(value, -40.0, 40.0)))


def softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(np.clip(shifted, -40.0, 40.0))
    return exp / exp.sum(axis=1, keepdims=True)


def roc_auc(labels: np.ndarray, scores: np.ndarray) -> float:
    labels = np.asarray(labels, dtype=int)
    scores = np.asarray(scores, dtype=float)
    positive = scores[labels == 1]
    negative = scores[labels == 0]
    if len(positive) == 0 or len(negative) == 0:
        return float("nan")
    return float(
        (positive[:, None] > negative[None, :]).mean()
        + 0.5 * (positive[:, None] == negative[None, :]).mean()
    )


def average_precision(labels: np.ndarray, scores: np.ndarray) -> float:
    labels = np.asarray(labels, dtype=int)
    scores = np.asarray(scores, dtype=float)
    order = np.argsort(-scores)
    sorted_labels = labels[order]
    positives = sorted_labels.sum()
    if positives == 0:
        return float("nan")
    precision = np.cumsum(sorted_labels) / (np.arange(len(sorted_labels)) + 1)
    return float((precision * sorted_labels).sum() / positives)


def ece(labels: np.ndarray, probabilities: np.ndarray, bins: int = 10) -> float:
    labels = np.asarray(labels, dtype=float)
    probabilities = np.asarray(probabilities, dtype=float)
    out = 0.0
    for lower in np.linspace(0.0, 1.0, bins, endpoint=False):
        upper = lower + 1.0 / bins
        mask = (probabilities >= lower) & ((probabilities < upper) if upper < 1.0 else (probabilities <= upper))
        if mask.any():
            out += float(mask.mean()) * abs(float(probabilities[mask].mean()) - float(labels[mask].mean()))
    return out


def safe_numeric(df: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in df.columns:
        return pd.Series(default, index=df.index, dtype=float)
    return pd.to_numeric(df[column], errors="coerce").fillna(default).astype(float)


def event_signal(values: pd.Series, missing_value: float = 999.0) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce").fillna(missing_value)
    signal = 1.0 - np.clip(numeric / missing_value, 0.0, 1.0)
    return pd.Series(signal, index=values.index, dtype=float)


def load_metrics(path: Path) -> dict:
    if not path.exists():
        return {"missing": True, "path": str(path)}
    return json.loads(path.read_text(encoding="utf-8"))


def prepare_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "route" not in df.columns:
        raise ValueError(f"Expected route column in {path}")
    df = df[df["route"].isin(ROUTES)].copy()
    df["seed"] = safe_numeric(df, "seed", -1).astype(int)
    df["route_idx"] = df["route"].map({route: idx for idx, route in enumerate(ROUTES)}).astype(int)
    df["review_or_abort"] = df["route"].isin(["human_review", "abort_candidate"]).astype(int)
    df["not_auto_execute"] = (~df["route"].eq("auto_execute")).astype(int)

    for column in [
        "steps",
        "final_distance",
        "min_distance",
        "distance_reduction",
        "risk_event_rate",
        "max_triage_risk",
        "monitor_triggers",
        "recovery_override_rate",
        "visual_reestimate_triggers",
        "recovery_phase_replans",
        "recovery_replans",
        "unsafe_warning_events",
        "unsafe_abort",
        "min_danger_distance",
        "learned_review_risk",
    ]:
        df[column] = safe_numeric(df, column, 0.0)

    if "initial_distance" in df.columns:
        df["initial_distance"] = safe_numeric(df, "initial_distance", df["final_distance"].median())
        denom = df["initial_distance"].replace(0.0, np.nan)
        df["progress_fraction"] = (df["distance_reduction"] / denom).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    else:
        df["progress_fraction"] = 0.0

    df["first_action_anomaly_signal"] = event_signal(df.get("first_action_anomaly_step", pd.Series(999.0, index=df.index)))
    df["first_grasp_uncertain_signal"] = event_signal(
        df.get("first_grasp_uncertain_step", pd.Series(999.0, index=df.index))
    )
    df["first_perception_uncertain_signal"] = event_signal(
        df.get("first_perception_uncertain_step", pd.Series(999.0, index=df.index))
    )
    danger = df["min_danger_distance"].replace(0.0, np.nan)
    df["inverse_min_danger_distance"] = (1.0 / danger).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    df["inverse_min_danger_distance"] = np.clip(df["inverse_min_danger_distance"], 0.0, 50.0)
    df["stall_or_slow_progress"] = np.clip(1.0 - df["progress_fraction"], 0.0, 2.0)
    df["failure_family_known"] = (~df.get("failure", pd.Series("unknown", index=df.index)).astype(str).eq("none")).astype(int)
    return df


def feature_columns(groups: list[str] | str) -> list[str]:
    if groups == "all":
        ordered: list[str] = []
        for name in FEATURE_GROUPS:
            for column in FEATURE_GROUPS[name]:
                if column not in ordered:
                    ordered.append(column)
        extras = ["progress_fraction", "stall_or_slow_progress"]
        return ordered + [column for column in extras if column not in ordered]
    out: list[str] = []
    for group in groups:
        out.extend(FEATURE_GROUPS[group])
    return list(dict.fromkeys(out))


def split_masks(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    residues = df["seed"].to_numpy(dtype=int) % 4
    train = residues < 2
    validation = residues == 2
    test = residues == 3
    if min(train.sum(), validation.sum(), test.sum()) == 0:
        split = df.get("split", pd.Series("", index=df.index)).astype(str)
        train = split.str.contains("train", case=False, na=False).to_numpy()
        test = ~train
        validation = train.copy()
    return train, validation, test


def standardize(train_x: np.ndarray, all_x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = train_x.mean(axis=0)
    std = train_x.std(axis=0)
    std[std < 1e-8] = 1.0
    return (all_x - mean) / std, mean, std


def fit_binary_logistic(
    x: np.ndarray,
    y: np.ndarray,
    lr: float = 0.05,
    steps: int = 3000,
    l2: float = 0.02,
) -> tuple[np.ndarray, float]:
    weights = np.zeros(x.shape[1], dtype=float)
    bias = 0.0
    y = y.astype(float)
    positive_weight = (len(y) - y.sum()) / max(y.sum(), 1.0)
    sample_weights = np.where(y == 1, positive_weight, 1.0)
    sample_weights = sample_weights / max(sample_weights.mean(), 1e-8)
    for _ in range(steps):
        probs = sigmoid(x @ weights + bias)
        err = (probs - y) * sample_weights
        grad_w = x.T @ err / len(y) + l2 * weights
        grad_b = float(err.mean())
        weights -= lr * grad_w
        bias -= lr * grad_b
    return weights, bias


def select_threshold(labels: np.ndarray, scores: np.ndarray, min_recall: float = 0.90) -> tuple[float, list[dict]]:
    rows = []
    for threshold in np.linspace(0.05, 0.95, 19):
        predicted = scores >= threshold
        tp = int(((predicted == 1) & (labels == 1)).sum())
        fp = int(((predicted == 1) & (labels == 0)).sum())
        fn = int(((predicted == 0) & (labels == 1)).sum())
        tn = int(((predicted == 0) & (labels == 0)).sum())
        recall = tp / (tp + fn) if tp + fn else 0.0
        fpr = fp / (fp + tn) if fp + tn else 0.0
        precision = tp / (tp + fp) if tp + fp else 0.0
        rows.append(
            {
                "threshold": float(threshold),
                "precision": precision,
                "recall": recall,
                "false_positive_rate": fpr,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "tn": tn,
            }
        )
    eligible = [row for row in rows if row["recall"] >= min_recall]
    if not eligible:
        return 0.5, rows
    selected = min(eligible, key=lambda row: (row["false_positive_rate"], -row["threshold"]))
    return float(selected["threshold"]), rows


def binary_metrics(labels: np.ndarray, scores: np.ndarray, threshold: float) -> dict[str, float]:
    predicted = scores >= threshold
    tp = int(((predicted == 1) & (labels == 1)).sum())
    fp = int(((predicted == 1) & (labels == 0)).sum())
    fn = int(((predicted == 0) & (labels == 1)).sum())
    tn = int(((predicted == 0) & (labels == 0)).sum())
    return {
        "threshold": float(threshold),
        "AUROC": roc_auc(labels, scores),
        "AUPRC": average_precision(labels, scores),
        "ECE": ece(labels, scores),
        "precision": tp / (tp + fp) if tp + fp else 0.0,
        "recall": tp / (tp + fn) if tp + fn else 0.0,
        "false_positive_rate": fp / (fp + tn) if fp + tn else 0.0,
        "capture_at_20pct": capture_at_budget(labels, scores, 0.20),
        "capture_at_30pct": capture_at_budget(labels, scores, 0.30),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def capture_at_budget(labels: np.ndarray, scores: np.ndarray, budget: float) -> float:
    labels = np.asarray(labels, dtype=int)
    scores = np.asarray(scores, dtype=float)
    positives = int(labels.sum())
    if positives == 0:
        return float("nan")
    count = max(1, int(round(len(labels) * budget)))
    selected = np.argsort(-scores)[:count]
    return float(labels[selected].sum() / positives)


def fit_multiclass_logistic(
    x: np.ndarray,
    y: np.ndarray,
    num_classes: int,
    lr: float = 0.05,
    steps: int = 4000,
    l2: float = 0.02,
) -> tuple[np.ndarray, np.ndarray]:
    weights = np.zeros((x.shape[1], num_classes), dtype=float)
    bias = np.zeros(num_classes, dtype=float)
    one_hot = np.eye(num_classes)[y]
    class_counts = np.bincount(y, minlength=num_classes).astype(float)
    class_weights = class_counts.sum() / np.maximum(class_counts, 1.0)
    sample_weights = class_weights[y]
    sample_weights = sample_weights / max(sample_weights.mean(), 1e-8)
    for _ in range(steps):
        probs = softmax(x @ weights + bias)
        err = (probs - one_hot) * sample_weights[:, None]
        grad_w = x.T @ err / len(y) + l2 * weights
        grad_b = err.mean(axis=0)
        weights -= lr * grad_w
        bias -= lr * grad_b
    return weights, bias


def route_metrics(y_true: np.ndarray, y_pred: np.ndarray, probs: np.ndarray) -> tuple[pd.DataFrame, dict[str, float]]:
    rows = []
    for idx, route in enumerate(ROUTES):
        tp = int(((y_true == idx) & (y_pred == idx)).sum())
        fp = int(((y_true != idx) & (y_pred == idx)).sum())
        fn = int(((y_true == idx) & (y_pred != idx)).sum())
        support = int((y_true == idx).sum())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        rows.append(
            {
                "route": route,
                "support": support,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "tp": tp,
                "fp": fp,
                "fn": fn,
            }
        )
    accuracy = float((y_true == y_pred).mean())
    macro_f1 = float(np.mean([row["f1"] for row in rows]))
    should_review = np.isin(y_true, [ROUTES.index("human_review"), ROUTES.index("abort_candidate")])
    predicted_auto = np.isin(y_pred, [ROUTES.index("auto_execute"), ROUTES.index("auto_recovery")])
    missed_review = predicted_auto & should_review
    false_review = (~predicted_auto) & (~should_review)
    summary = {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "missed_review_or_abort_rate": float(missed_review.sum() / max(1, should_review.sum())),
        "false_review_or_abort_rate": float(false_review.sum() / max(1, (~should_review).sum())),
        "mean_confidence": float(probs.max(axis=1).mean()),
    }
    return pd.DataFrame(rows), summary


def train_binary_ablation(df: pd.DataFrame, train: np.ndarray, validation: np.ndarray, test: np.ndarray) -> pd.DataFrame:
    y = df["review_or_abort"].to_numpy(dtype=int)
    rows = []
    ablations: dict[str, list[str] | str] = {
        "progress_only": ["progress"],
        "action_only": ["action"],
        "visual_only": ["visual"],
        "contact_only": ["contact"],
        "boundary_only": ["boundary"],
        "representation_proxy_only": ["representation_proxy"],
        "handcrafted_multisignal": "handcrafted",
        "all_multisignal": "all",
    }
    for name, groups in ablations.items():
        if groups == "handcrafted":
            columns = [column for column in feature_columns("all") if column != "learned_review_risk"]
        else:
            columns = feature_columns(groups)
        x = df[columns].to_numpy(dtype=float)
        standardized, _, _ = standardize(x[train], x)
        weights, bias = fit_binary_logistic(standardized[train], y[train])
        scores = sigmoid(standardized @ weights + bias)
        threshold, _ = select_threshold(y[validation], scores[validation])
        metrics = binary_metrics(y[test], scores[test], threshold)
        rows.append({"model": name, "features": ",".join(columns), "test_rows": int(test.sum()), **metrics})
    return pd.DataFrame(rows)


def train_multisignal_models(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train, validation, test = split_masks(df)
    binary_table = train_binary_ablation(df, train, validation, test)

    columns = feature_columns("all")
    x = df[columns].to_numpy(dtype=float)
    standardized, mean, std = standardize(x[train], x)
    y_review = df["review_or_abort"].to_numpy(dtype=int)
    weights, bias = fit_binary_logistic(standardized[train], y_review[train])
    review_scores = sigmoid(standardized @ weights + bias)
    threshold, threshold_rows = select_threshold(y_review[validation], review_scores[validation])

    y_route = df["route_idx"].to_numpy(dtype=int)
    route_weights, route_bias = fit_multiclass_logistic(standardized[train], y_route[train], len(ROUTES))
    route_probs = softmax(standardized @ route_weights + route_bias)
    route_pred = route_probs.argmax(axis=1)
    route_table, route_summary = route_metrics(y_route[test], route_pred[test], route_probs[test])

    scored = df.copy()
    scored["multisignal_review_score"] = review_scores
    scored["multisignal_review_pred"] = (review_scores >= threshold).astype(int)
    scored["multisignal_route_pred"] = [ROUTES[idx] for idx in route_pred]
    scored["multisignal_route_confidence"] = route_probs.max(axis=1)
    scored["split_multisignal"] = np.select([train, validation, test], ["train", "validation", "test"], default="other")

    weight_rows = []
    for column, weight_value, mean_value, std_value in zip(columns, weights, mean, std):
        weight_rows.append(
            {
                "target": "review_or_abort",
                "feature": column,
                "weight": float(weight_value),
                "abs_weight": float(abs(weight_value)),
                "train_mean": float(mean_value),
                "train_std": float(std_value),
            }
        )
    for route_idx, route in enumerate(ROUTES):
        for column, weight_value in zip(columns, route_weights[:, route_idx]):
            weight_rows.append(
                {
                    "target": f"route::{route}",
                    "feature": column,
                    "weight": float(weight_value),
                    "abs_weight": float(abs(weight_value)),
                    "train_mean": np.nan,
                    "train_std": np.nan,
                }
            )
    weights_table = pd.DataFrame(weight_rows)

    route_summary_table = pd.DataFrame([route_summary])
    route_summary_table["test_rows"] = int(test.sum())
    route_summary_table["threshold_review_or_abort"] = threshold
    threshold_table = pd.DataFrame(threshold_rows)

    return binary_table, route_table, route_summary_table, weights_table, scored, threshold_table


def plot_ablation(binary_table: pd.DataFrame, route_summary: pd.DataFrame, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.2), constrained_layout=True)
    ordered = binary_table.sort_values("AUROC", ascending=False)
    axes[0].barh(ordered["model"], ordered["AUROC"], color="#4C78A8")
    axes[0].invert_yaxis()
    axes[0].set_xlim(0.0, 1.0)
    axes[0].set_xlabel("Review/abort AUROC")
    axes[0].set_title("Single-family vs multi-signal risk")
    for idx, value in enumerate(ordered["AUROC"]):
        axes[0].text(min(value + 0.015, 0.98), idx, f"{value:.3f}", va="center", fontsize=8)

    metrics = [
        ("accuracy", "Accuracy"),
        ("macro_f1", "Macro-F1"),
        ("missed_review_or_abort_rate", "Missed review/abort"),
        ("false_review_or_abort_rate", "False review/abort"),
    ]
    values = [float(route_summary.iloc[0][key]) for key, _ in metrics]
    labels = [label for _, label in metrics]
    colors = ["#54A24B", "#54A24B", "#E45756", "#F58518"]
    axes[1].bar(labels, values, color=colors)
    axes[1].set_ylim(0.0, 1.0)
    axes[1].tick_params(axis="x", rotation=20)
    axes[1].set_title("Mechanism router held-out behavior")
    for idx, value in enumerate(values):
        axes[1].text(idx, min(value + 0.025, 0.98), f"{value:.3f}", ha="center", fontsize=8)

    out_path = out_dir / "multisignal_reliability_upgrade.png"
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    return out_path


def write_report(
    path: Path,
    binary_table: pd.DataFrame,
    route_table: pd.DataFrame,
    route_summary: pd.DataFrame,
    weights_table: pd.DataFrame,
    figure_path: Path,
    visual_metrics: dict,
    memory_metrics: dict,
    adapter_metrics: dict,
) -> None:
    best = binary_table.sort_values("AUROC", ascending=False).iloc[0]
    all_row = binary_table[binary_table["model"].eq("all_multisignal")].iloc[0]
    route = route_summary.iloc[0]
    top_weights = weights_table[weights_table["target"].eq("review_or_abort")].sort_values(
        "abs_weight", ascending=False
    ).head(12)

    def metric(payload: dict, *keys: str, default: str = "n/a") -> str:
        value = payload
        for key in keys:
            if not isinstance(value, dict) or key not in value:
                return default
            value = value[key]
        if isinstance(value, float):
            return f"{value:.3f}"
        return str(value)

    lines = [
        "# Multi-Signal Reliability Upgrade",
        "",
        "## Question",
        "",
        (
            "Can the surgical RL project move beyond a single embedding/KNN analysis and "
            "train ECG-style reliability models from multiple evidence families?"
        ),
        "",
        "## What Was Added",
        "",
        "This upgrade trains and evaluates two lightweight supervisors from existing SurRoL reliability logs:",
        "",
        "1. a binary `review_or_abort` risk head;",
        "2. a four-way mechanism router over `auto_execute`, `auto_recovery`, `human_review`, and `abort_candidate`.",
        "",
        "The input evidence families are:",
        "",
        "- progress and stagnation evidence;",
        "- action anomaly and recovery burden evidence;",
        "- visual/perception uncertainty evidence;",
        "- grasp/contact uncertainty evidence;",
        "- boundary and unsafe-zone evidence;",
        "- representation-proxy evidence from learned review risk and triage scores.",
        "",
        "This is intentionally broader than embedding/PCA/KNN alone.",
        "",
        "## Binary Review/Abort Head",
        "",
        "| Model | AUROC | AUPRC | Recall | FPR | Capture@20% | Capture@30% |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in binary_table.sort_values("AUROC", ascending=False).iterrows():
        lines.append(
            f"| {row['model']} | {row['AUROC']:.3f} | {row['AUPRC']:.3f} | "
            f"{row['recall']:.3f} | {row['false_positive_rate']:.3f} | "
            f"{row['capture_at_20pct']:.3f} | {row['capture_at_30pct']:.3f} |"
        )

    lines.extend(
        [
            "",
            (
                f"Best AUROC in this held-out split is `{best['model']}` at {best['AUROC']:.3f}. "
                f"The all-signal model achieves AUROC {all_row['AUROC']:.3f}, "
                f"AUPRC {all_row['AUPRC']:.3f}, and recall {all_row['recall']:.3f}."
            ),
            "",
            f"![Multi-signal reliability upgrade]({figure_path.relative_to(path.parent).as_posix()})",
            "",
            "## Mechanism Router",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| accuracy | {route['accuracy']:.3f} |",
            f"| macro-F1 | {route['macro_f1']:.3f} |",
            f"| missed review-or-abort rate | {route['missed_review_or_abort_rate']:.3f} |",
            f"| false review-or-abort rate | {route['false_review_or_abort_rate']:.3f} |",
            f"| mean confidence | {route['mean_confidence']:.3f} |",
            "",
            "Per-route metrics:",
            "",
            "| Route | Support | Precision | Recall | F1 |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for _, row in route_table.iterrows():
        lines.append(
            f"| {row['route']} | {int(row['support'])} | {row['precision']:.3f} | "
            f"{row['recall']:.3f} | {row['f1']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Highest-Magnitude Review-Risk Weights",
            "",
            "| Feature | Weight | Interpretation family |",
            "|---|---:|---|",
        ]
    )
    family_for_feature = {}
    for family, columns in FEATURE_GROUPS.items():
        for column in columns:
            family_for_feature.setdefault(column, family)
    family_for_feature["progress_fraction"] = "progress"
    family_for_feature["stall_or_slow_progress"] = "progress"
    for _, row in top_weights.iterrows():
        lines.append(f"| {row['feature']} | {row['weight']:.3f} | {family_for_feature.get(row['feature'], 'other')} |")

    lines.extend(
        [
            "",
            "## Existing Visual And Representation Modules Used As Evidence",
            "",
            "| Module | Held-out evidence | Interpretation |",
            "|---|---|---|",
            (
                f"| visual action-risk head | AUROC {metric(visual_metrics, 'AUROC')}, "
                f"AUPRC {metric(visual_metrics, 'AUPRC')}, recall {metric(visual_metrics, 'recall')} | "
                "Detects high policy-vs-oracle action-gap steps. |"
            ),
            (
                f"| visual recovery memory | mean action L2 {metric(memory_metrics, 'mean_action_l2')}, "
                f"global mean L2 {metric(memory_metrics, 'global_mean_action_l2')} | "
                "PCA/KNN recovery memory gives a local action suggestion for high-risk visual states. |"
            ),
            (
                f"| visual denoising adapter | corrupt MSE reduction "
                f"{metric(adapter_metrics, 'test', 'corrupt_mse_reduction')} | "
                "Clean/corrupt visual-feature pairs support a perception reliability branch. |"
            ),
            "",
            "## Interpretation",
            "",
            (
                "This upgrade makes the RL project closer to the ECG project structurally. "
                "The supervisor is no longer described as only embedding/KNN. It uses multiple "
                "evidence families, trains a new risk head, trains a mechanism router, reports "
                "single-family ablations, and keeps the final claim focused on reliability routing."
            ),
            "",
            "## Limitations",
            "",
            "- The labels are distilled from simulator logs and injected failures, not expert surgical annotations.",
            "- Some features are episode-level or summary features, so this is a research audit and supervisor prototype rather than a fully deployable online controller.",
            "- The visual modules are lightweight feature-level models, not full surgical scene segmentation or clinical perception validation.",
            "- The evidence is internal simulation evidence only.",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.figure_dir.mkdir(parents=True, exist_ok=True)
    df = prepare_dataset(args.scored_episodes)
    binary_table, route_table, route_summary, weights_table, scored, threshold_table = train_multisignal_models(df)

    binary_path = args.out_dir / "multisignal_review_ablation.csv"
    route_path = args.out_dir / "multisignal_mechanism_router_metrics.csv"
    route_summary_path = args.out_dir / "multisignal_mechanism_router_summary.csv"
    weights_path = args.out_dir / "multisignal_reliability_weights.csv"
    scored_path = args.out_dir / "multisignal_reliability_scored.csv"
    thresholds_path = args.out_dir / "multisignal_review_thresholds.csv"

    binary_table.to_csv(binary_path, index=False)
    route_table.to_csv(route_path, index=False)
    route_summary.to_csv(route_summary_path, index=False)
    weights_table.to_csv(weights_path, index=False)
    scored.to_csv(scored_path, index=False)
    threshold_table.to_csv(thresholds_path, index=False)

    figure_path = plot_ablation(binary_table, route_summary, args.figure_dir)
    write_report(
        args.report,
        binary_table,
        route_table,
        route_summary,
        weights_table,
        figure_path,
        load_metrics(args.visual_risk_metrics),
        load_metrics(args.visual_memory_metrics),
        load_metrics(args.visual_adapter_metrics),
    )

    print(f"binary_ablation={binary_path}")
    print(f"route_summary={route_summary_path}")
    print(f"weights={weights_path}")
    print(f"scored={scored_path}")
    print(f"figure={figure_path}")
    print(f"report={args.report}")


if __name__ == "__main__":
    main()
