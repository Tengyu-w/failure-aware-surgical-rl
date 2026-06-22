from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "reports" / "tables"
REPORTS = ROOT / "reports"

ROUTES = ["auto_execute", "auto_recovery", "human_review", "abort_candidate"]

FEATURES = [
    "success",
    "steps",
    "initial_distance",
    "final_distance",
    "min_distance",
    "distance_reduction",
    "risk_event_rate",
    "monitor_triggers",
    "recovery_replans",
    "recovery_phase_replans",
    "recovery_override_rate",
    "visual_reestimate_triggers",
    "unsafe_warning_events",
    "unsafe_abort",
    "min_danger_distance",
]


def route_for_row(row: pd.Series) -> str:
    failure = str(row.get("failure", ""))
    controller = str(row.get("controller", ""))
    unsafe_abort = float(row.get("unsafe_abort", 0.0) or 0.0)
    if unsafe_abort > 0:
        return "abort_candidate"
    if controller == "clean" or failure == "none":
        return "auto_execute"
    if failure in {"perception_bias", "perception_jitter", "depth_scale_error", "jaw_stuck_open"}:
        return "human_review"
    if failure in {"action_noise", "action_dropout", "execution_slip", "action_freeze", "near_target_drift"}:
        return "auto_recovery"
    return "human_review"


def family_for_failure(failure: str) -> str:
    if failure == "none":
        return "nominal_execution"
    if failure in {"action_noise", "action_dropout", "execution_slip", "action_freeze"}:
        return "reversible_execution_drift"
    if failure == "near_target_drift":
        return "near_target_recovery_risk"
    if failure == "jaw_stuck_open":
        return "grasp_contact_uncertainty"
    if failure in {"perception_bias", "perception_jitter", "depth_scale_error"}:
        return "visual_state_error"
    return "other"


def load_dataset() -> pd.DataFrame:
    master = pd.read_csv(TABLES / "surrol_master_episode_rows.csv")
    master["source"] = "master_episode_rows"
    frames = [master]
    unsafe_path = ROOT / "runs" / "surrol_needlepick_unsafe_abort_r052_w16_20seed.csv"
    if unsafe_path.exists():
        unsafe = pd.read_csv(unsafe_path)
        unsafe["source"] = "unsafe_zone_20seed"
        # Align with master schema.
        unsafe["initial_distance"] = unsafe.get("initial_distance", np.nan)
        unsafe["distance_reduction"] = unsafe.get("distance_reduction", np.nan)
        unsafe["risk_event_rate"] = unsafe.get("risk_event_rate", 0.0)
        unsafe["recovery_replans"] = 0.0
        unsafe["recovery_phase_replans"] = 0.0
        unsafe["visual_reestimate_triggers"] = 0.0
        frames.append(unsafe)
    df = pd.concat(frames, ignore_index=True, sort=False)
    df["route_label"] = [route_for_row(row) for _, row in df.iterrows()]
    df["fault_family"] = [family_for_failure(str(item)) for item in df["failure"]]
    df["seed"] = pd.to_numeric(df["seed"], errors="coerce").fillna(-1).astype(int)
    for col in FEATURES:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # Fill distances with conservative neutral values from observed data.
    for col in ["initial_distance", "final_distance", "min_distance", "distance_reduction"]:
        df[col] = df[col].fillna(df[col].median())
    for col in FEATURES:
        df[col] = df[col].fillna(0.0)
    df["min_danger_distance"] = df["min_danger_distance"].replace(0.0, 1.0)
    return df


def split_by_seed(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = df[df["seed"] % 2 == 0].copy()
    test = df[df["seed"] % 2 == 1].copy()
    if train.empty or test.empty:
        raise RuntimeError("Seed split produced an empty train or test set.")
    return train, test


def standardize(train: np.ndarray, test: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mu = train.mean(axis=0)
    sigma = train.std(axis=0)
    sigma[sigma < 1e-8] = 1.0
    return (train - mu) / sigma, (test - mu) / sigma, mu, sigma


def softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(np.clip(shifted, -40, 40))
    return exp / exp.sum(axis=1, keepdims=True)


def fit_multiclass_logistic(
    x: np.ndarray,
    y: np.ndarray,
    num_classes: int,
    class_weights: np.ndarray | None = None,
    lr: float = 0.08,
    steps: int = 3000,
    l2: float = 0.01,
) -> tuple[np.ndarray, np.ndarray]:
    weights = np.zeros((x.shape[1], num_classes), dtype=float)
    bias = np.zeros(num_classes, dtype=float)
    one_hot = np.eye(num_classes)[y]
    sample_weights = np.ones(len(y), dtype=float)
    if class_weights is not None:
        sample_weights = class_weights[y].astype(float)
        sample_weights = sample_weights / max(1e-8, sample_weights.mean())
    for _ in range(steps):
        probs = softmax(x @ weights + bias)
        err = (probs - one_hot) * sample_weights[:, None]
        grad_w = x.T @ err / len(y) + l2 * weights
        grad_b = err.mean(axis=0)
        weights -= lr * grad_w
        bias -= lr * grad_b
    return weights, bias


def classification_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> pd.DataFrame:
    rows = []
    for idx, label in enumerate(ROUTES):
        tp = int(((y_true == idx) & (y_pred == idx)).sum())
        fp = int(((y_true != idx) & (y_pred == idx)).sum())
        fn = int(((y_true == idx) & (y_pred != idx)).sum())
        support = int((y_true == idx).sum())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        rows.append(
            {
                "route": label,
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
    rows.append(
        {
            "route": "overall",
            "support": int(len(y_true)),
            "precision": accuracy,
            "recall": accuracy,
            "f1": macro_f1,
            "tp": int((y_true == y_pred).sum()),
            "fp": int((y_true != y_pred).sum()),
            "fn": 0,
        }
    )
    return pd.DataFrame(rows)


def confusion(y_true: np.ndarray, y_pred: np.ndarray) -> pd.DataFrame:
    rows = []
    for i, true_label in enumerate(ROUTES):
        for j, pred_label in enumerate(ROUTES):
            rows.append(
                {
                    "true_route": true_label,
                    "pred_route": pred_label,
                    "count": int(((y_true == i) & (y_pred == j)).sum()),
                }
            )
    return pd.DataFrame(rows)


def reliability_summary(test: pd.DataFrame, probs: np.ndarray, y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    human_idx = ROUTES.index("human_review")
    abort_idx = ROUTES.index("abort_candidate")
    safe_auto = np.isin(y_pred, [ROUTES.index("auto_execute"), ROUTES.index("auto_recovery")])
    should_review = np.isin(y_true, [human_idx, abort_idx])
    false_auto = safe_auto & should_review
    false_review = (~safe_auto) & (~should_review)
    return {
        "test_episodes": float(len(test)),
        "accuracy": float((y_true == y_pred).mean()),
        "macro_f1": float(classification_metrics(y_true, y_pred).query("route == 'overall'")["f1"].iloc[0]),
        "missed_review_or_abort_rate": float(false_auto.sum() / max(1, should_review.sum())),
        "false_review_or_abort_rate": float(false_review.sum() / max(1, (~should_review).sum())),
        "mean_confidence": float(probs.max(axis=1).mean()),
        "human_review_support": float((y_true == human_idx).sum()),
        "abort_candidate_support": float((y_true == abort_idx).sum()),
    }


def write_report(
    path: Path,
    metrics: pd.DataFrame,
    summary: dict[str, float],
    weights: pd.DataFrame,
    errors: pd.DataFrame,
) -> None:
    lines = [
        "# SurRoL Learned Route Classifier",
        "",
        "## Takeaway",
        "",
        (
            "This step upgrades the rule/proxy taxonomy into an episode-level learned route classifier. "
            "The classifier predicts `auto_execute`, `auto_recovery`, `human_review`, or `abort_candidate` "
            "from numeric SurRoL rollout features and is evaluated with an even/odd seed split to reduce "
            "episode leakage. It remains a prototype reliability classifier because the labels are distilled "
            "from current rule-based routing and simulator logs."
        ),
        "",
        "## Held-Out Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key, value in summary.items():
        lines.append(f"| {key} | {value:.3f} |")
    lines.extend(
        [
            "",
            "## Per-Route Metrics",
            "",
            "| Route | Support | Precision | Recall | F1 |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for _, row in metrics.iterrows():
        lines.append(
            f"| {row['route']} | {int(row['support'])} | {row['precision']:.3f} | "
            f"{row['recall']:.3f} | {row['f1']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Highest-Magnitude Feature Weights",
            "",
            "| Route | Feature | Weight |",
            "|---|---|---:|",
        ]
    )
    for _, row in weights.sort_values("abs_weight", ascending=False).head(20).iterrows():
        lines.append(f"| {row['route']} | {row['feature']} | {row['weight']:.3f} |")
    lines.extend(
        [
            "",
            "## Boundary Errors",
            "",
            "| Task | Failure | Controller | Seed | True | Pred | Confidence |",
            "|---|---|---|---:|---|---|---:|",
        ]
    )
    if errors.empty:
        lines.append("| none | none | none | 0 | none | none | 0.000 |")
    else:
        for _, row in errors.head(20).iterrows():
            lines.append(
                f"| {row['task']} | {row['failure']} | {row['controller']} | {int(row['seed'])} | "
                f"{row['route_label']} | {row['pred_route']} | {row['confidence']:.3f} |"
            )
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- Labels are distilled from the current rule/proxy routing policy, not independent expert annotations.",
            "- The classifier is episode-level; Step 4 should move toward observable online/window-level routing.",
            "- `abort_candidate` remains low-support and geometry-proxy based.",
            "- Features include post-episode quantities such as final distance and success; do not present this as deployable online control yet.",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    df = load_dataset()
    train, test = split_by_seed(df)
    x_train_raw = train[FEATURES].to_numpy(dtype=float)
    x_test_raw = test[FEATURES].to_numpy(dtype=float)
    x_train, x_test, mu, sigma = standardize(x_train_raw, x_test_raw)
    label_to_id = {label: idx for idx, label in enumerate(ROUTES)}
    y_train = train["route_label"].map(label_to_id).to_numpy(dtype=int)
    y_test = test["route_label"].map(label_to_id).to_numpy(dtype=int)
    # Safety-biased weights reduce the costlier mistake: routing review/abort
    # cases into automatic execution or automatic recovery.
    class_weights = np.array([1.0, 1.0, 2.2, 4.0], dtype=float)
    weights, bias = fit_multiclass_logistic(x_train, y_train, len(ROUTES), class_weights=class_weights)
    test_probs = softmax(x_test @ weights + bias)
    train_probs = softmax(x_train @ weights + bias)
    y_pred = test_probs.argmax(axis=1)

    train_scored = train.copy()
    test_scored = test.copy()
    train_scored["split"] = "train_even_seed"
    test_scored["split"] = "test_odd_seed"
    train_scored["pred_route"] = [ROUTES[i] for i in train_probs.argmax(axis=1)]
    test_scored["pred_route"] = [ROUTES[i] for i in y_pred]
    train_scored["confidence"] = train_probs.max(axis=1)
    test_scored["confidence"] = test_probs.max(axis=1)
    for idx, route in enumerate(ROUTES):
        train_scored[f"prob_{route}"] = train_probs[:, idx]
        test_scored[f"prob_{route}"] = test_probs[:, idx]
    scored = pd.concat([train_scored, test_scored], ignore_index=True)

    metrics = classification_metrics(y_test, y_pred)
    conf = confusion(y_test, y_pred)
    summary = reliability_summary(test, test_probs, y_test, y_pred)
    weight_rows = []
    for route_idx, route in enumerate(ROUTES):
        for feature_idx, feature in enumerate(FEATURES):
            value = float(weights[feature_idx, route_idx])
            weight_rows.append({"route": route, "feature": feature, "weight": value, "abs_weight": abs(value)})
    weight_df = pd.DataFrame(weight_rows)
    errors = test_scored[test_scored["route_label"] != test_scored["pred_route"]].copy()

    TABLES.mkdir(parents=True, exist_ok=True)
    scored.to_csv(TABLES / "surrol_learned_route_classifier_scored.csv", index=False)
    metrics.to_csv(TABLES / "surrol_learned_route_classifier_metrics.csv", index=False)
    conf.to_csv(TABLES / "surrol_learned_route_classifier_confusion.csv", index=False)
    weight_df.to_csv(TABLES / "surrol_learned_route_classifier_weights.csv", index=False)
    with (TABLES / "surrol_learned_route_classifier_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)
    write_report(REPORTS / "surrol_learned_route_classifier_step3.md", metrics, summary, weight_df, errors)
    print(f"scored={TABLES / 'surrol_learned_route_classifier_scored.csv'}")
    print(f"metrics={TABLES / 'surrol_learned_route_classifier_metrics.csv'}")
    print(f"report={REPORTS / 'surrol_learned_route_classifier_step3.md'}")


if __name__ == "__main__":
    main()
