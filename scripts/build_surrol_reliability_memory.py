from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ROUTE_INPUT = ROOT / "reports" / "tables" / "surrol_risk_triage_episode_routes.csv"
UNSAFE_INPUT_CANDIDATES = [
    ROOT / "runs" / "surrol_needlepick_unsafe_abort_r052_w16_20seed.csv",
    ROOT / "runs" / "surrol_needlepick_unsafe_abort_r052_w16_5seed.csv",
]

FEATURES = [
    "success",
    "final_distance",
    "steps",
    "max_triage_risk",
    "monitor_triggers",
    "recovery_phase_replans",
    "recovery_override_rate",
    "unsafe_warning_events",
    "min_danger_distance",
    "first_action_anomaly_observed",
    "first_grasp_uncertain_observed",
    "first_perception_uncertain_observed",
    "first_review_observed",
    "first_abort_observed",
]


def failure_family(
    failure: str,
    route: str,
    controller: str = "",
    success: float = 0.0,
    unsafe_abort: float = 0.0,
) -> str:
    if controller == "clean" and success >= 1.0 and unsafe_abort <= 0 and route == "auto_execute":
        return "nominal"
    if unsafe_abort > 0 or route == "abort_candidate":
        return "unsafe_abort"
    if failure == "none":
        return "nominal"
    if failure in {"perception_bias", "perception_jitter", "depth_scale_error"}:
        return "visual_state_error"
    if failure in {"near_target_drift", "action_freeze", "action_noise", "action_dropout", "execution_slip"}:
        return "execution_drift"
    if failure == "jaw_stuck_open":
        return "grasp_outcome_uncertain"
    return "other_failure"


def load_routes() -> pd.DataFrame:
    df = pd.read_csv(ROUTE_INPUT)
    df["unsafe_warning_events"] = 0.0
    df["unsafe_abort"] = 0.0
    df["min_danger_distance"] = 1.0
    df["source"] = "triage_routes"
    frames = [df]
    unsafe_input = next((path for path in UNSAFE_INPUT_CANDIDATES if path.exists()), None)
    if unsafe_input is not None:
        unsafe = pd.read_csv(unsafe_input)
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
        unsafe["source"] = "unsafe_zone"
        for col in [
            "first_action_anomaly_step",
            "first_grasp_uncertain_step",
            "first_perception_uncertain_step",
            "first_review_step",
            "first_abort_step",
        ]:
            unsafe[col] = np.nan
        frames.append(unsafe)
    out = pd.concat(frames, ignore_index=True, sort=False)
    out["family"] = [
        failure_family(
            str(failure),
            str(route),
            str(controller),
            float(success) if not pd.isna(success) else 0.0,
            float(unsafe_abort) if not pd.isna(unsafe_abort) else 0.0,
        )
        for failure, route, controller, success, unsafe_abort in zip(
            out["failure"],
            out["route"],
            out["controller"],
            out["success"],
            out.get("unsafe_abort", 0.0),
        )
    ]
    return out


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in [
        "first_action_anomaly_step",
        "first_grasp_uncertain_step",
        "first_perception_uncertain_step",
        "first_review_step",
        "first_abort_step",
    ]:
        base = col.replace("_step", "_observed")
        df[base] = (~df[col].isna()).astype(float) if col in df.columns else 0.0
    for col in FEATURES:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["min_danger_distance"] = df["min_danger_distance"].replace(0.0, 1.0)
    return df


def standardize(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mu = x.mean(axis=0)
    sigma = x.std(axis=0)
    sigma[sigma < 1e-8] = 1.0
    return (x - mu) / sigma, mu, sigma


def pca2(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    centered = x - x.mean(axis=0)
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    components = vt[:2]
    return centered @ components.T, components


def nearest_centroid(train_x: np.ndarray, train_y: np.ndarray, test_x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    labels = np.array(sorted(set(train_y)))
    centroids = np.stack([train_x[train_y == label].mean(axis=0) for label in labels], axis=0)
    dists = np.linalg.norm(test_x[:, None, :] - centroids[None, :, :], axis=2)
    idx = dists.argmin(axis=1)
    return labels[idx], dists.min(axis=1)


def classification_report(y_true: np.ndarray, y_pred: np.ndarray, label_name: str) -> pd.DataFrame:
    labels = sorted(set(y_true) | set(y_pred))
    rows = []
    for label in labels:
        tp = int(((y_true == label) & (y_pred == label)).sum())
        fp = int(((y_true != label) & (y_pred == label)).sum())
        fn = int(((y_true == label) & (y_pred != label)).sum())
        support = int((y_true == label).sum())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        rows.append(
            {
                "label_type": label_name,
                "label": label,
                "support": support,
                "precision": precision,
                "recall": recall,
                "f1": f1,
            }
        )
    rows.append(
        {
            "label_type": label_name,
            "label": "overall_accuracy",
            "support": len(y_true),
            "precision": float((y_true == y_pred).mean()),
            "recall": float((y_true == y_pred).mean()),
            "f1": float((y_true == y_pred).mean()),
        }
    )
    return pd.DataFrame(rows)


def confusion_table(y_true: np.ndarray, y_pred: np.ndarray, label_name: str) -> pd.DataFrame:
    labels = sorted(set(y_true) | set(y_pred))
    rows = []
    for true_label in labels:
        for pred_label in labels:
            rows.append(
                {
                    "label_type": label_name,
                    "true_label": true_label,
                    "pred_label": pred_label,
                    "count": int(((y_true == true_label) & (y_pred == pred_label)).sum()),
                }
            )
    return pd.DataFrame(rows)


def plot_embedding(df: pd.DataFrame, out_dir: Path, color_col: str, filename: str) -> None:
    fig, ax = plt.subplots(figsize=(8.0, 6.0))
    for label, group in df.groupby(color_col):
        ax.scatter(group["pc1"], group["pc2"], s=34, alpha=0.78, label=str(label))
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.set_title(f"SurRoL Reliability Embedding by {color_col}")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, fontsize=8, loc="best")
    fig.tight_layout()
    fig.savefig(out_dir / filename, dpi=200)
    plt.close(fig)


def write_report(metrics: pd.DataFrame, family_acc: float, route_acc: float, out: Path) -> None:
    family = metrics[metrics["label_type"] == "family"]
    route = metrics[metrics["label_type"] == "route"]
    lines = [
        "# SurRoL External Reliability Memory Prototype",
        "",
        "## Takeaway",
        "",
        (
            "This prototype embeds existing SurRoL episode logs into a reliability memory and uses a nearest-prototype "
            "classifier for failure-family and route prediction. It is a reliability-oriented retrieval layer: instead "
            "of retrieving how to manipulate an object, it asks whether the current execution segment resembles historical "
            "visual-state errors, execution drift, grasp uncertainty, or unsafe-abort candidates."
        ),
        "",
        "## Label Definition",
        "",
        (
            "Successful clean-controller episodes without unsafe aborts and with an auto-execute route are labeled as "
            "nominal. This keeps the failure-family label closer to the observed reliability state rather than simply "
            "copying the injected fault name."
        ),
        "",
        "## Held-Out Prototype Accuracy",
        "",
        "| Prediction | Accuracy |",
        "|---|---:|",
        f"| Failure family | {family_acc:.3f} |",
        f"| Route | {route_acc:.3f} |",
        "",
        "## Failure-Family Metrics",
        "",
        "| Family | Support | Precision | Recall | F1 |",
        "|---|---:|---:|---:|---:|",
    ]
    for _, row in family[family["label"] != "overall_accuracy"].iterrows():
        lines.append(
            f"| {row['label']} | {int(row['support'])} | {row['precision']:.3f} | {row['recall']:.3f} | {row['f1']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Route Metrics",
            "",
            "| Route | Support | Precision | Recall | F1 |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for _, row in route[route["label"] != "overall_accuracy"].iterrows():
        lines.append(
            f"| {row['label']} | {int(row['support'])} | {row['precision']:.3f} | {row['recall']:.3f} | {row['f1']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This is the first external reliability-memory layer: episode features are embedded, then classified by distance to historical prototypes.",
            "- If error classes cluster in embedding space, it supports the ECG-style argument that mixed/overlapping regions are reliability-risk regions.",
            "- The prototype is intentionally simple; it is a baseline before trying learned encoders, sequence windows, or image-derived features.",
            "",
            "## Limitations",
            "",
            "- Current embeddings are based on simulator state/log features, not real visual embeddings.",
            "- The labels partly come from synthetic injected failures and rule-based routing.",
            "- Unsafe-zone evidence is still task-local and geometric, not a real tissue-damage model.",
            "",
            "## Outputs",
            "",
            "- `reports/tables/surrol_reliability_memory_embeddings.csv`",
            "- `reports/tables/surrol_reliability_memory_predictions.csv`",
            "- `reports/tables/surrol_reliability_memory_metrics.csv`",
            "- `reports/tables/surrol_reliability_memory_confusion.csv`",
            "- `reports/figures/surrol_reliability_memory/embedding_by_family.png`",
            "- `reports/figures/surrol_reliability_memory/embedding_by_route.png`",
        ]
    )
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    table_dir = ROOT / "reports" / "tables"
    fig_dir = ROOT / "reports" / "figures" / "surrol_reliability_memory"
    table_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    df = prepare_features(load_routes())
    x_raw = df[FEATURES].to_numpy(dtype=float)
    x, _, _ = standardize(x_raw)
    coords, _ = pca2(x)
    df["pc1"] = coords[:, 0]
    df["pc2"] = coords[:, 1]
    df["split"] = np.where(df["seed"].astype(int) % 2 == 0, "train_even_seed", "test_odd_seed")

    train_mask = df["split"] == "train_even_seed"
    test_mask = ~train_mask
    pred_family, dist_family = nearest_centroid(
        x[train_mask], df.loc[train_mask, "family"].to_numpy(str), x[test_mask]
    )
    pred_route, dist_route = nearest_centroid(
        x[train_mask], df.loc[train_mask, "route"].to_numpy(str), x[test_mask]
    )
    pred = df.loc[test_mask, ["suite", "task", "failure", "controller", "seed", "route", "family"]].copy()
    pred["pred_family"] = pred_family
    pred["family_distance"] = dist_family
    pred["pred_route"] = pred_route
    pred["route_distance"] = dist_route
    family_acc = float((pred["family"].to_numpy(str) == pred["pred_family"].to_numpy(str)).mean())
    route_acc = float((pred["route"].to_numpy(str) == pred["pred_route"].to_numpy(str)).mean())
    metrics = pd.concat(
        [
            classification_report(pred["family"].to_numpy(str), pred["pred_family"].to_numpy(str), "family"),
            classification_report(pred["route"].to_numpy(str), pred["pred_route"].to_numpy(str), "route"),
        ],
        ignore_index=True,
    )
    confusion = pd.concat(
        [
            confusion_table(pred["family"].to_numpy(str), pred["pred_family"].to_numpy(str), "family"),
            confusion_table(pred["route"].to_numpy(str), pred["pred_route"].to_numpy(str), "route"),
        ],
        ignore_index=True,
    )

    df.to_csv(table_dir / "surrol_reliability_memory_embeddings.csv", index=False)
    pred.to_csv(table_dir / "surrol_reliability_memory_predictions.csv", index=False)
    metrics.to_csv(table_dir / "surrol_reliability_memory_metrics.csv", index=False)
    confusion.to_csv(table_dir / "surrol_reliability_memory_confusion.csv", index=False)
    plot_embedding(df, fig_dir, "family", "embedding_by_family.png")
    plot_embedding(df, fig_dir, "route", "embedding_by_route.png")
    report_path = ROOT / "reports" / "surrol_reliability_memory.md"
    write_report(metrics, family_acc, route_acc, report_path)

    print(f"embeddings={table_dir / 'surrol_reliability_memory_embeddings.csv'}")
    print(f"predictions={table_dir / 'surrol_reliability_memory_predictions.csv'}")
    print(f"metrics={table_dir / 'surrol_reliability_memory_metrics.csv'}")
    print(f"figures={fig_dir}")
    print(f"report={report_path}")


if __name__ == "__main__":
    main()
