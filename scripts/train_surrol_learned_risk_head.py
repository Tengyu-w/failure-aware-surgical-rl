from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "reports" / "tables" / "surrol_risk_triage_episode_routes.csv"
UNSAFE_INPUT = ROOT / "runs" / "surrol_needlepick_unsafe_abort_r052_w16_5seed.csv"
FEATURES = [
    "max_triage_risk",
    "final_distance",
    "steps",
    "monitor_triggers",
    "recovery_phase_replans",
    "recovery_override_rate",
    "unsafe_warning_events",
    "min_danger_distance",
    "first_action_anomaly_missing",
    "first_grasp_uncertain_missing",
    "first_perception_uncertain_missing",
    "first_review_missing",
]


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -40, 40)))


def load_dataset() -> pd.DataFrame:
    base = pd.read_csv(INPUT)
    frames = [base]
    if UNSAFE_INPUT.exists():
        unsafe = pd.read_csv(UNSAFE_INPUT)
        unsafe["suite"] = "unsafe_zone_abort_proxy"
        unsafe["route"] = np.where(unsafe["unsafe_abort"].astype(float) > 0, "abort_candidate", "auto_recovery")
        unsafe.loc[(unsafe["failure"] == "none") & (unsafe["controller"] != "perturbed"), "route"] = "auto_execute"
        unsafe["route_reason"] = np.where(
            unsafe["route"] == "abort_candidate",
            "unsafe_zone_violation",
            np.where(unsafe["route"] == "auto_execute", "nominal_no_unsafe_abort", "safe_or_failed_without_abort"),
        )
        unsafe["max_triage_risk"] = unsafe["unsafe_warning_events"].astype(float)
        unsafe["recovery_phase_replans"] = 0.0
        unsafe["recovery_override_rate"] = unsafe.get("recovery_override_rate", 0.0)
        for col in [
            "first_action_anomaly_step",
            "first_grasp_uncertain_step",
            "first_perception_uncertain_step",
            "first_review_step",
        ]:
            unsafe[col] = np.nan
        frames.append(unsafe)
    return pd.concat(frames, ignore_index=True, sort=False)


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["review_needed"] = df["route"].isin(["human_review", "abort_candidate"]).astype(int)
    df["failure_or_review"] = ((df["failure"] != "none") | (df["review_needed"] == 1)).astype(int)
    for col in [
        "first_action_anomaly_step",
        "first_grasp_uncertain_step",
        "first_perception_uncertain_step",
        "first_review_step",
    ]:
        base = col.replace("_step", "")
        df[f"{base}_missing"] = df[col].isna().astype(float)
        df[col] = df[col].fillna(999.0)
    for col in FEATURES:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["min_danger_distance"] = df["min_danger_distance"].replace(0.0, 1.0)
    return df


def standardize(train: np.ndarray, test: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mu = train.mean(axis=0)
    sigma = train.std(axis=0)
    sigma[sigma < 1e-8] = 1.0
    return (train - mu) / sigma, (test - mu) / sigma, mu, sigma


def fit_logistic(x: np.ndarray, y: np.ndarray, lr: float = 0.08, steps: int = 2500, l2: float = 0.01) -> tuple[np.ndarray, float]:
    w = np.zeros(x.shape[1], dtype=float)
    b = 0.0
    for _ in range(steps):
        p = sigmoid(x @ w + b)
        err = p - y
        grad_w = x.T @ err / len(y) + l2 * w
        grad_b = float(err.mean())
        w -= lr * grad_w
        b -= lr * grad_b
    return w, b


def roc_auc(y: np.ndarray, score: np.ndarray) -> float:
    pos = score[y == 1]
    neg = score[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    return float(((pos[:, None] > neg[None, :]).mean() + 0.5 * (pos[:, None] == neg[None, :]).mean()))


def average_precision(y: np.ndarray, score: np.ndarray) -> float:
    order = np.argsort(-score)
    y_sorted = y[order]
    positives = y_sorted.sum()
    if positives == 0:
        return float("nan")
    precision = np.cumsum(y_sorted) / (np.arange(len(y_sorted)) + 1)
    return float((precision * y_sorted).sum() / positives)


def ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    total = len(y)
    value = 0.0
    for lo in np.linspace(0.0, 1.0, bins, endpoint=False):
        hi = lo + 1.0 / bins
        mask = (p >= lo) & (p < hi if hi < 1.0 else p <= hi)
        if not mask.any():
            continue
        value += mask.mean() * abs(float(p[mask].mean()) - float(y[mask].mean()))
    return float(value)


def threshold_table(df: pd.DataFrame, thresholds: list[float]) -> pd.DataFrame:
    rows = []
    y = df["review_needed"].to_numpy(dtype=int)
    p = df["learned_review_risk"].to_numpy(dtype=float)
    for t in thresholds:
        pred = p >= t
        tp = int(((pred == 1) & (y == 1)).sum())
        fp = int(((pred == 1) & (y == 0)).sum())
        fn = int(((pred == 0) & (y == 1)).sum())
        tn = int(((pred == 0) & (y == 0)).sum())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        false_trigger_rate = fp / (fp + tn) if fp + tn else 0.0
        auto_coverage = (tn + fn) / len(y)
        auto_review_miss_rate = fn / (fn + tn) if fn + tn else 0.0
        rows.append(
            {
                "threshold": t,
                "precision": precision,
                "recall": recall,
                "false_trigger_rate": false_trigger_rate,
                "auto_coverage": auto_coverage,
                "auto_review_miss_rate": auto_review_miss_rate,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "tn": tn,
            }
        )
    return pd.DataFrame(rows)


def write_report(metrics: dict[str, float], thresh: pd.DataFrame, weights: pd.DataFrame, out: Path) -> None:
    lines = [
        "# SurRoL Learned Risk Head",
        "",
        "## Takeaway",
        "",
        (
            "A lightweight logistic risk head was trained from existing SurRoL episode-routing logs to predict whether an "
            "episode should be routed to review/abort rather than automatic execution/recovery. This version also includes "
            "the unsafe-zone abort proxy, so the head begins to model both visual-state review and geometric abort candidates. "
            "It is still best interpreted as reliability-policy distillation, evaluated with an even/odd seed split."
        ),
        "",
        "## Held-Out Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key, value in metrics.items():
        lines.append(f"| {key} | {value:.3f} |")
    lines.extend(
        [
            "",
            "## Threshold Routing",
            "",
            "| Threshold | Precision | Recall | False Trigger | Auto Coverage | Auto Review Miss | TP | FP | FN | TN |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for _, row in thresh.iterrows():
        lines.append(
            f"| {row['threshold']:.2f} | {row['precision']:.3f} | {row['recall']:.3f} | "
            f"{row['false_trigger_rate']:.3f} | {row['auto_coverage']:.3f} | {row['auto_review_miss_rate']:.3f} | "
            f"{int(row['tp'])} | {int(row['fp'])} | {int(row['fn'])} | {int(row['tn'])} |"
        )
    lines.extend(
        [
            "",
            "## Feature Weights",
            "",
            "| Feature | Weight |",
            "|---|---:|",
        ]
    )
    for _, row in weights.sort_values("abs_weight", ascending=False).iterrows():
        lines.append(f"| {row['feature']} | {row['weight']:.3f} |")
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- The labels come from the current rule-based triage and unsafe-zone outputs, so this is distillation rather than independent ground truth.",
            "- The split is seed-based and small; it is useful for a prototype reliability head but not deployment validation.",
            "- The unsafe-zone evidence is still geometric and task-local, not a true tissue-damage model.",
        ]
    )
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    table_dir = ROOT / "reports" / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    df = prepare(load_dataset())
    train = df[df["seed"] % 2 == 0].copy()
    test = df[df["seed"] % 2 == 1].copy()

    x_train_raw = train[FEATURES].to_numpy(dtype=float)
    x_test_raw = test[FEATURES].to_numpy(dtype=float)
    y_train = train["review_needed"].to_numpy(dtype=float)
    y_test = test["review_needed"].to_numpy(dtype=int)
    x_train, x_test, mu, sigma = standardize(x_train_raw, x_test_raw)
    w, b = fit_logistic(x_train, y_train)

    train["learned_review_risk"] = sigmoid(x_train @ w + b)
    test["learned_review_risk"] = sigmoid(x_test @ w + b)
    scored = pd.concat([train, test], ignore_index=True)
    scored["split"] = np.where(scored["seed"] % 2 == 0, "train_even_seed", "test_odd_seed")
    test_p = test["learned_review_risk"].to_numpy(dtype=float)
    metrics = {
        "test_episodes": float(len(test)),
        "test_review_rate": float(y_test.mean()),
        "AUROC": roc_auc(y_test, test_p),
        "AUPRC": average_precision(y_test, test_p),
        "Brier": float(np.mean((test_p - y_test) ** 2)),
        "ECE": ece(y_test, test_p),
    }
    thresh = threshold_table(test, [0.2, 0.4, 0.6, 0.8])
    weights = pd.DataFrame({"feature": FEATURES, "weight": w})
    weights["abs_weight"] = weights["weight"].abs()

    scored.to_csv(table_dir / "surrol_learned_risk_head_scored.csv", index=False)
    thresh.to_csv(table_dir / "surrol_learned_risk_head_thresholds.csv", index=False)
    weights.to_csv(table_dir / "surrol_learned_risk_head_weights.csv", index=False)
    report_path = ROOT / "reports" / "surrol_learned_risk_head.md"
    write_report(metrics, thresh, weights, report_path)
    print(f"scored={table_dir / 'surrol_learned_risk_head_scored.csv'}")
    print(f"thresholds={table_dir / 'surrol_learned_risk_head_thresholds.csv'}")
    print(f"weights={table_dir / 'surrol_learned_risk_head_weights.csv'}")
    print(f"report={report_path}")


if __name__ == "__main__":
    main()
