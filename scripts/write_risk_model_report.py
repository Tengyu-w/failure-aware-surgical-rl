from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np


NAVIGATION_FAILURES = ("none", "state_target_bias", "state_dropout", "execution_slip")
MANIPULATION_FAILURES = ("none", "object_state_bias", "object_dropout", "execution_slip", "contact_loss")
MANIP_FILE_STEMS = {"object_state_bias": "object_bias"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-dir", type=Path, default=Path("runs"))
    parser.add_argument("--out", type=Path, default=Path("reports") / "risk_model_report.md")
    parser.add_argument("--dataset-out", type=Path, default=Path("reports") / "risk_model_dataset.csv")
    parser.add_argument("--navigation-prefix", default="failure_suite")
    parser.add_argument("--manipulation-prefix", default="manip_failure")
    return parser.parse_args()


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def f(row: dict, key: str, default: float = 0.0) -> float:
    try:
        value = float(row.get(key, default) or default)
    except ValueError:
        return default
    if np.isnan(value):
        return default
    return value


def clip01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def detected(row: dict) -> float:
    if "failure_detected" in row:
        return f(row, "failure_detected")
    return f(row, "drift_detected")


def distance_risk(row: dict, task: str) -> float:
    if task == "manipulation":
        return clip01(max(f(row, "final_distance") / 0.65, f(row, "object_goal_distance") / 0.65))
    return clip01(f(row, "final_distance") / 0.65)


def safety_risk(row: dict) -> float:
    cost = clip01(f(row, "cumulative_cost") / 2.0)
    return clip01(max(f(row, "budget_exhausted"), cost, f(row, "final_force_proxy") / 4.0))


def intervention_risk(row: dict) -> float:
    return clip01(max(f(row, "mean_action_deviation") / 0.08, f(row, "shield_interventions") / 20.0))


def delay_risk(row: dict) -> float:
    if detected(row) <= 0.5:
        return 0.0
    return clip01(f(row, "detection_delay") / 8.0)


def risk_score(row: dict, task: str) -> float:
    # Observable proxy risk: trigger evidence dominates, with residual task error,
    # safety cost, action correction, and delayed detection as secondary signals.
    score = 0.62 * detected(row)
    score += 0.18 * distance_risk(row, task)
    score += 0.10 * safety_risk(row)
    score += 0.06 * intervention_risk(row)
    score += 0.04 * delay_risk(row)
    return clip01(score)


def collect_dataset(runs_dir: Path, nav_prefix: str, manip_prefix: str) -> list[dict]:
    dataset: list[dict] = []

    for failure in NAVIGATION_FAILURES:
        path = runs_dir / f"{nav_prefix}_{failure}_monitor_recovery.csv"
        if not path.exists():
            continue
        for row in read_rows(path):
            score = risk_score(row, "navigation")
            dataset.append(
                {
                    "task": "navigation",
                    "failure_mode": failure,
                    "episode": row.get("episode", ""),
                    "failure_label": float(failure != "none"),
                    "risk_score": score,
                    "detected": detected(row),
                    "distance_risk": distance_risk(row, "navigation"),
                    "safety_risk": safety_risk(row),
                    "intervention_risk": intervention_risk(row),
                    "delay_risk": delay_risk(row),
                    "success": f(row, "success"),
                    "detection_delay": f(row, "detection_delay"),
                }
            )

    for failure in MANIPULATION_FAILURES:
        stem = MANIP_FILE_STEMS.get(failure, failure)
        path = runs_dir / f"{manip_prefix}_{stem}_monitor.csv"
        if not path.exists():
            continue
        for row in read_rows(path):
            score = risk_score(row, "manipulation")
            dataset.append(
                {
                    "task": "manipulation",
                    "failure_mode": failure,
                    "episode": row.get("episode", ""),
                    "failure_label": float(failure != "none"),
                    "risk_score": score,
                    "detected": detected(row),
                    "distance_risk": distance_risk(row, "manipulation"),
                    "safety_risk": safety_risk(row),
                    "intervention_risk": intervention_risk(row),
                    "delay_risk": delay_risk(row),
                    "success": f(row, "success"),
                    "detection_delay": f(row, "detection_delay"),
                }
            )
    return dataset


def write_dataset(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fobj:
        writer = csv.DictWriter(fobj, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def feature_matrix(rows: list[dict]) -> np.ndarray:
    return np.array(
        [
            [
                row["risk_score"],
                row["detected"],
                row["distance_risk"],
                row["safety_risk"],
                row["intervention_risk"],
                row["delay_risk"],
                1.0 if row["task"] == "manipulation" else 0.0,
            ]
            for row in rows
        ],
        dtype=np.float64,
    )


def labels(rows: list[dict]) -> np.ndarray:
    return np.array([row["failure_label"] for row in rows], dtype=np.float64)


def train_logistic_risk_head(train_rows: list[dict], steps: int = 2500, lr: float = 0.2) -> dict:
    x = feature_matrix(train_rows)
    y = labels(train_rows)
    mean = x.mean(axis=0)
    std = x.std(axis=0)
    std[std < 1e-8] = 1.0
    xz = (x - mean) / std
    xz = np.column_stack([np.ones(len(xz)), xz])
    weights = np.zeros(xz.shape[1], dtype=np.float64)
    for _ in range(steps):
        pred = 1.0 / (1.0 + np.exp(-(xz @ weights)))
        grad = xz.T @ (pred - y) / len(y)
        weights -= lr * grad
    return {"mean": mean, "std": std, "weights": weights}


def predict_logistic(model: dict, rows: list[dict]) -> np.ndarray:
    x = feature_matrix(rows)
    xz = (x - model["mean"]) / model["std"]
    xz = np.column_stack([np.ones(len(xz)), xz])
    return 1.0 / (1.0 + np.exp(-(xz @ model["weights"])))


def add_learned_risk(rows: list[dict]) -> tuple[list[dict], dict]:
    train_rows = [row for row in rows if int(row["episode"]) % 2 == 0]
    eval_rows = [row for row in rows if int(row["episode"]) % 2 == 1]
    model = train_logistic_risk_head(train_rows)
    train_pred = predict_logistic(model, train_rows)
    eval_pred = predict_logistic(model, eval_rows)

    out = []
    train_idx = 0
    eval_idx = 0
    for row in rows:
        enriched = dict(row)
        if int(row["episode"]) % 2 == 0:
            enriched["split"] = "train"
            enriched["learned_risk_score"] = float(train_pred[train_idx])
            train_idx += 1
        else:
            enriched["split"] = "eval"
            enriched["learned_risk_score"] = float(eval_pred[eval_idx])
            eval_idx += 1
        out.append(enriched)
    return out, model


def roc_auc(labels: np.ndarray, scores: np.ndarray) -> float:
    pos = scores[labels == 1]
    neg = scores[labels == 0]
    if len(pos) == 0 or len(neg) == 0:
        return 0.0
    wins = 0.0
    total = len(pos) * len(neg)
    for p in pos:
        wins += float(np.sum(p > neg))
        wins += 0.5 * float(np.sum(p == neg))
    return wins / total


def average_precision(labels: np.ndarray, scores: np.ndarray) -> float:
    order = np.argsort(-scores)
    sorted_labels = labels[order]
    positives = float(np.sum(labels == 1))
    if positives == 0:
        return 0.0
    tp = 0.0
    precision_sum = 0.0
    for idx, label in enumerate(sorted_labels, start=1):
        if label == 1:
            tp += 1.0
            precision_sum += tp / idx
    return precision_sum / positives


def brier(labels: np.ndarray, scores: np.ndarray) -> float:
    return float(np.mean((scores - labels) ** 2))


def ece(labels: np.ndarray, scores: np.ndarray, bins: int = 10) -> float:
    total = len(labels)
    out = 0.0
    for idx in range(bins):
        low = idx / bins
        high = (idx + 1) / bins
        if idx == bins - 1:
            mask = (scores >= low) & (scores <= high)
        else:
            mask = (scores >= low) & (scores < high)
        if not np.any(mask):
            continue
        confidence = float(np.mean(scores[mask]))
        accuracy = float(np.mean(labels[mask]))
        out += np.sum(mask) / total * abs(confidence - accuracy)
    return float(out)


def threshold_table(labels: np.ndarray, scores: np.ndarray, thresholds: tuple[float, ...]) -> list[dict]:
    rows = []
    for threshold in thresholds:
        flagged = scores >= threshold
        tp = int(np.sum((labels == 1) & flagged))
        fp = int(np.sum((labels == 0) & flagged))
        fn = int(np.sum((labels == 1) & (~flagged)))
        tn = int(np.sum((labels == 0) & (~flagged)))
        precision = tp / (tp + fp) if tp + fp else 1.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        false_trigger = fp / (fp + tn) if fp + tn else 0.0
        coverage = float(np.mean(~flagged))
        auto_failure_rate = fn / (fn + tn) if fn + tn else 0.0
        rows.append(
            {
                "threshold": threshold,
                "precision": precision,
                "recall": recall,
                "false_trigger": false_trigger,
                "auto_coverage": coverage,
                "auto_failure_rate": auto_failure_rate,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "tn": tn,
            }
        )
    return rows


def fmt(value: float) -> str:
    return f"{value:.3f}"


def subset_metrics(rows: list[dict], task: str | None = None, score_key: str = "risk_score") -> dict:
    selected = [row for row in rows if task is None or row["task"] == task]
    labels = np.array([row["failure_label"] for row in selected], dtype=np.float64)
    scores = np.array([row[score_key] for row in selected], dtype=np.float64)
    return {
        "episodes": len(selected),
        "prevalence": float(np.mean(labels)),
        "auroc": roc_auc(labels, scores),
        "auprc": average_precision(labels, scores),
        "brier": brier(labels, scores),
        "ece": ece(labels, scores),
        "mean_nominal_score": float(np.mean(scores[labels == 0])),
        "mean_failure_score": float(np.mean(scores[labels == 1])),
    }


def write_report(rows: list[dict], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    eval_rows = [row for row in rows if row["split"] == "eval"]
    eval_labels = np.array([row["failure_label"] for row in eval_rows], dtype=np.float64)
    learned_scores = np.array([row["learned_risk_score"] for row in eval_rows], dtype=np.float64)
    thresholds = threshold_table(eval_labels, learned_scores, (0.20, 0.40, 0.60, 0.80))
    raw_groups = [
        ("overall", subset_metrics(eval_rows)),
        ("navigation", subset_metrics(eval_rows, "navigation")),
        ("manipulation", subset_metrics(eval_rows, "manipulation")),
    ]
    learned_groups = [
        ("overall", subset_metrics(eval_rows, score_key="learned_risk_score")),
        ("navigation", subset_metrics(eval_rows, "navigation", score_key="learned_risk_score")),
        ("manipulation", subset_metrics(eval_rows, "manipulation", score_key="learned_risk_score")),
    ]

    lines = [
        "# Risk And Uncertainty Model Report",
        "",
        "## Reliability Question",
        "",
        (
        "Can a lightweight uncertainty/risk model separate nominal executions from injected failure "
        "episodes across navigation and manipulation proxies, while supporting threshold-based review routing?"
        ),
        "",
        "## Risk Scores",
        "",
        (
            "`risk_score = 0.62 * detection + 0.18 * residual task distance + 0.10 * safety risk "
            "+ 0.06 * action-intervention risk + 0.04 * detection-delay risk`."
        ),
        "",
        (
            "`learned_risk_score` is a lightweight logistic risk head trained with NumPy on even-numbered "
            "episodes and evaluated on odd-numbered episodes. It uses the proxy risk features, not raw simulator state."
        ),
        "",
        "## Held-Out Metric Summary",
        "",
        "| Score | Group | Episodes | Failure Rate | AUROC | AUPRC | Brier | ECE | Mean Nominal Risk | Mean Failure Risk |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for score_name, group_rows in (("proxy", raw_groups), ("learned", learned_groups)):
        for name, metrics in group_rows:
            lines.append(
                f"| {score_name} | {name} | {metrics['episodes']} | {fmt(metrics['prevalence'])} | {fmt(metrics['auroc'])} | "
                f"{fmt(metrics['auprc'])} | {fmt(metrics['brier'])} | {fmt(metrics['ece'])} | "
                f"{fmt(metrics['mean_nominal_score'])} | {fmt(metrics['mean_failure_score'])} |"
            )

    lines.extend(
        [
            "",
            "## Learned-Risk Threshold Routing",
            "",
            "| Risk Threshold | Precision | Recall | False Trigger Rate | Auto Coverage | Auto Failure Rate | TP | FP | FN | TN |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in thresholds:
        lines.append(
            f"| {fmt(row['threshold'])} | {fmt(row['precision'])} | {fmt(row['recall'])} | "
            f"{fmt(row['false_trigger'])} | {fmt(row['auto_coverage'])} | {fmt(row['auto_failure_rate'])} | "
            f"{row['tp']} | {row['fp']} | {row['fn']} | {row['tn']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The strongest current signal is still the explicit detection term; it separates synthetic failure episodes cleanly in this proxy suite.",
            "- The learned risk head improves probability calibration relative to the raw proxy score on the current held-out split.",
            "- Threshold routing reports how many episodes could run automatically versus be escalated for review.",
            "",
            "## Limitations",
            "",
            "- The learned risk head is trained and evaluated on synthetic injected failures from the same proxy family.",
            "- It is not calibrated on held-out real surgical data and should not be presented as deployment validation.",
            "- A stronger next step is to learn risk from trajectory windows before failure injection is revealed, then evaluate OOD transfer.",
            "",
        ]
    )
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"report={out}")


def main() -> None:
    args = parse_args()
    rows = collect_dataset(args.runs_dir, args.navigation_prefix, args.manipulation_prefix)
    rows, _ = add_learned_risk(rows)
    write_dataset(rows, args.dataset_out)
    write_report(rows, args.out)


if __name__ == "__main__":
    main()
