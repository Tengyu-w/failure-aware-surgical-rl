from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from run_multisignal_reliability_upgrade import (
    ROOT,
    ROUTES,
    feature_columns,
    prepare_dataset,
    sigmoid,
    softmax,
    split_masks,
    standardize,
    fit_binary_logistic,
    fit_multiclass_logistic,
    route_metrics,
    roc_auc,
    average_precision,
)


TABLES = ROOT / "reports" / "tables"
FIGURES = ROOT / "reports" / "figures" / "ecg_style_rl_reliability_suite"
REPORT = ROOT / "reports" / "ecg_style_rl_reliability_suite.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run an ECG-style broad reliability suite for the surgical RL logs: "
            "representation geometry, uncertainty, trajectory structure, "
            "perturbation robustness, model intervention, and mechanism routing."
        )
    )
    parser.add_argument("--scored-episodes", type=Path, default=TABLES / "surrol_learned_risk_head_scored.csv")
    parser.add_argument("--out-dir", type=Path, default=TABLES)
    parser.add_argument("--figure-dir", type=Path, default=FIGURES)
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--run-multisignal-first", action="store_true")
    return parser.parse_args()


def pca_projection(x: np.ndarray, components: int = 3) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = x.mean(axis=0)
    centered = x - mean
    _, _, vh = np.linalg.svd(centered, full_matrices=False)
    basis = vh[: min(components, vh.shape[0])]
    return centered @ basis.T, mean, basis


def pairwise_distances(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    return np.sqrt(np.maximum(((x[:, None, :] - y[None, :, :]) ** 2).sum(axis=2), 0.0))


def silhouette_score(x: np.ndarray, labels: np.ndarray) -> float:
    unique = [label for label in np.unique(labels) if (labels == label).sum() > 1]
    if len(unique) < 2:
        return float("nan")
    distances = pairwise_distances(x, x)
    values = []
    for i, label in enumerate(labels):
        same = labels == label
        same[i] = False
        if not same.any():
            continue
        a = float(distances[i, same].mean())
        b = min(float(distances[i, labels == other].mean()) for other in unique if other != label and (labels == other).any())
        values.append((b - a) / max(a, b, 1e-8))
    return float(np.mean(values)) if values else float("nan")


def davies_bouldin_score(x: np.ndarray, labels: np.ndarray) -> float:
    unique = [label for label in np.unique(labels) if (labels == label).sum() > 0]
    if len(unique) < 2:
        return float("nan")
    centroids = []
    scatters = []
    for label in unique:
        subset = x[labels == label]
        centroid = subset.mean(axis=0)
        centroids.append(centroid)
        scatters.append(float(np.linalg.norm(subset - centroid, axis=1).mean()))
    centroids = np.asarray(centroids)
    center_dist = pairwise_distances(centroids, centroids)
    np.fill_diagonal(center_dist, np.inf)
    ratios = []
    for i in range(len(unique)):
        ratios.append(max((scatters[i] + scatters[j]) / max(center_dist[i, j], 1e-8) for j in range(len(unique)) if j != i))
    return float(np.mean(ratios))


def entropy_from_counts(counts: np.ndarray) -> float:
    probs = counts.astype(float) / max(float(counts.sum()), 1e-8)
    probs = probs[probs > 0]
    return float(-(probs * np.log(probs)).sum() / max(math.log(len(counts)), 1e-8))


def representation_analysis(df: pd.DataFrame, x: np.ndarray, columns: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    labels = df["route"].astype(str).to_numpy()
    route_indices = df["route_idx"].to_numpy(dtype=int)
    projected, _, _ = pca_projection(x, 3)

    centroid_rows = []
    centroids = {}
    scatters = {}
    for route in ROUTES:
        mask = labels == route
        if not mask.any():
            continue
        centroids[route] = x[mask].mean(axis=0)
        scatters[route] = float(np.linalg.norm(x[mask] - centroids[route], axis=1).mean())
    for a in centroids:
        for b in centroids:
            if a >= b:
                continue
            distance = float(np.linalg.norm(centroids[a] - centroids[b]))
            normalized = distance / max((scatters[a] + scatters[b]) / 2.0, 1e-8)
            centroid_rows.append(
                {
                    "route_a": a,
                    "route_b": b,
                    "centroid_distance": distance,
                    "normalized_centroid_distance": normalized,
                    "scatter_a": scatters[a],
                    "scatter_b": scatters[b],
                }
            )

    centroid_table = pd.DataFrame(centroid_rows)
    quality_table = pd.DataFrame(
        [
            {
                "embedding": "multisignal_feature_space",
                "features": ",".join(columns),
                "silhouette": silhouette_score(x, route_indices),
                "davies_bouldin": davies_bouldin_score(x, route_indices),
                "pca_var_dim1": float(np.var(projected[:, 0])) if projected.shape[1] > 0 else np.nan,
                "pca_var_dim2": float(np.var(projected[:, 1])) if projected.shape[1] > 1 else np.nan,
                "pca_var_dim3": float(np.var(projected[:, 2])) if projected.shape[1] > 2 else np.nan,
            }
        ]
    )

    prototype_centers = np.vstack([centroids[route] for route in ROUTES])
    proto_dist = pairwise_distances(x, prototype_centers)
    nearest = proto_dist.argmin(axis=1)
    sorted_dist = np.sort(proto_dist, axis=1)
    ambiguity = 1.0 - np.clip((sorted_dist[:, 1] - sorted_dist[:, 0]) / np.maximum(sorted_dist[:, 1], 1e-8), 0.0, 1.0)
    prototype_table = df[["task", "failure", "route", "seed", "episode"]].copy()
    prototype_table["nearest_prototype_route"] = [ROUTES[idx] for idx in nearest]
    prototype_table["nearest_prototype_distance"] = proto_dist[np.arange(len(df)), nearest]
    prototype_table["prototype_ambiguity"] = ambiguity
    prototype_table["prototype_classifier_conflict"] = (nearest != route_indices).astype(int)
    if ROUTES.index("auto_recovery") < proto_dist.shape[1] and ROUTES.index("human_review") < proto_dist.shape[1]:
        ar = proto_dist[:, ROUTES.index("auto_recovery")]
        hr = proto_dist[:, ROUTES.index("human_review")]
        prototype_table["recovery_review_prototype_ambiguity"] = 1.0 - np.abs(ar - hr) / np.maximum(np.maximum(ar, hr), 1e-8)
    return centroid_table, quality_table, prototype_table


def knn_analysis(df: pd.DataFrame, x: np.ndarray, train_mask: np.ndarray, k: int = 7) -> pd.DataFrame:
    labels = df["route_idx"].to_numpy(dtype=int)
    train_x = x[train_mask]
    train_labels = labels[train_mask]
    distances = pairwise_distances(x, train_x)
    rows = []
    for i in range(len(df)):
        order = np.argsort(distances[i])[: min(k, len(train_x))]
        neighbor_labels = train_labels[order]
        counts = np.bincount(neighbor_labels, minlength=len(ROUTES))
        true_label = labels[i]
        recovery_review = counts[ROUTES.index("auto_recovery")] + counts[ROUTES.index("human_review")]
        rows.append(
            {
                "task": df.iloc[i].get("task", "unknown"),
                "failure": df.iloc[i].get("failure", "unknown"),
                "route": df.iloc[i]["route"],
                "seed": int(df.iloc[i]["seed"]),
                "episode": int(df.iloc[i]["episode"]),
                "knn_distance": float(distances[i, order[0]]),
                "knn_label_entropy": entropy_from_counts(counts),
                "knn_local_purity": float((neighbor_labels == true_label).mean()),
                "knn_recovery_review_mixing": float(recovery_review / len(order)),
                "knn_majority_route": ROUTES[int(counts.argmax())],
                "knn_route_conflict": int(counts.argmax() != true_label),
            }
        )
    return pd.DataFrame(rows)


def decision_uncertainty(df: pd.DataFrame, route_probs: np.ndarray, review_scores: np.ndarray, route_pred: np.ndarray) -> pd.DataFrame:
    y_route = df["route_idx"].to_numpy(dtype=int)
    route_error = (route_pred != y_route).astype(int)
    sorted_probs = np.sort(route_probs, axis=1)
    max_prob = sorted_probs[:, -1]
    margin = sorted_probs[:, -1] - sorted_probs[:, -2]
    entropy = -(route_probs * np.log(np.clip(route_probs, 1e-12, 1.0))).sum(axis=1) / math.log(route_probs.shape[1])
    uncertainty = pd.DataFrame(
        {
            "score": ["msp", "entropy", "margin_inverse", "review_score"],
            "route_error_AUROC": [
                roc_auc(route_error, 1.0 - max_prob),
                roc_auc(route_error, entropy),
                roc_auc(route_error, 1.0 - margin),
                roc_auc(route_error, review_scores),
            ],
            "review_or_abort_AUROC": [
                roc_auc(df["review_or_abort"].to_numpy(dtype=int), 1.0 - max_prob),
                roc_auc(df["review_or_abort"].to_numpy(dtype=int), entropy),
                roc_auc(df["review_or_abort"].to_numpy(dtype=int), 1.0 - margin),
                roc_auc(df["review_or_abort"].to_numpy(dtype=int), review_scores),
            ],
            "review_or_abort_AUPRC": [
                average_precision(df["review_or_abort"].to_numpy(dtype=int), 1.0 - max_prob),
                average_precision(df["review_or_abort"].to_numpy(dtype=int), entropy),
                average_precision(df["review_or_abort"].to_numpy(dtype=int), 1.0 - margin),
                average_precision(df["review_or_abort"].to_numpy(dtype=int), review_scores),
            ],
        }
    )
    return uncertainty


def trajectory_structure_analysis(df: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = [
        "steps",
        "final_distance",
        "distance_reduction",
        "progress_fraction",
        "stall_or_slow_progress",
        "monitor_triggers",
        "recovery_phase_replans",
        "recovery_override_rate",
        "unsafe_warning_events",
        "unsafe_abort",
    ]
    rows = []
    for failure, group in df.groupby("failure"):
        row = {"failure": failure, "episodes": int(len(group))}
        for col in numeric_cols:
            if col in group:
                row[f"{col}_mean"] = float(pd.to_numeric(group[col], errors="coerce").fillna(0.0).mean())
        rows.append(row)
    return pd.DataFrame(rows).sort_values("episodes", ascending=False)


def robustness_analysis(df: pd.DataFrame, review_scores: np.ndarray) -> pd.DataFrame:
    tmp = df.copy()
    tmp["review_score"] = review_scores
    rows = []
    for failure, group in tmp.groupby("failure"):
        rows.append(
            {
                "failure": failure,
                "episodes": int(len(group)),
                "mean_review_score": float(group["review_score"].mean()),
                "review_or_abort_rate": float(group["review_or_abort"].mean()),
                "mean_final_distance": float(group["final_distance"].mean()),
                "mean_steps": float(group["steps"].mean()),
                "mean_recovery_phase_replans": float(group["recovery_phase_replans"].mean()),
            }
        )
    return pd.DataFrame(rows).sort_values("mean_review_score", ascending=False)


def plot_suite(df: pd.DataFrame, projected: np.ndarray, review_scores: np.ndarray, robustness: pd.DataFrame, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(14.0, 4.2), constrained_layout=True)
    route_colors = {
        "auto_execute": "#4C78A8",
        "auto_recovery": "#54A24B",
        "human_review": "#E45756",
        "abort_candidate": "#F58518",
    }
    for route, group in df.assign(pc1=projected[:, 0], pc2=projected[:, 1]).groupby("route"):
        axes[0].scatter(group["pc1"], group["pc2"], s=28, alpha=0.82, label=route, color=route_colors.get(route))
    axes[0].set_title("Multi-signal representation PCA")
    axes[0].set_xlabel("PC1")
    axes[0].set_ylabel("PC2")
    axes[0].legend(frameon=False, fontsize=8)

    ordered = robustness.head(10).sort_values("mean_review_score")
    axes[1].barh(ordered["failure"], ordered["mean_review_score"], color="#B279A2")
    axes[1].set_xlim(0.0, 1.0)
    axes[1].set_title("Risk by injected failure")
    axes[1].set_xlabel("Mean review score")

    bins = np.linspace(0.0, 1.0, 11)
    axes[2].hist(review_scores[df["review_or_abort"].eq(0)], bins=bins, alpha=0.7, label="execute/recover", color="#4C78A8")
    axes[2].hist(review_scores[df["review_or_abort"].eq(1)], bins=bins, alpha=0.7, label="review/abort", color="#E45756")
    axes[2].set_title("Review score separation")
    axes[2].set_xlabel("Review score")
    axes[2].set_ylabel("Episodes")
    axes[2].legend(frameon=False, fontsize=8)

    out = out_dir / "ecg_style_rl_reliability_suite.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def write_report(
    path: Path,
    centroid: pd.DataFrame,
    quality: pd.DataFrame,
    knn: pd.DataFrame,
    uncertainty: pd.DataFrame,
    robustness: pd.DataFrame,
    route_summary: dict,
    figure: Path,
) -> None:
    q = quality.iloc[0]
    knn_summary = {
        "mean_knn_entropy": float(knn["knn_label_entropy"].mean()),
        "mean_local_purity": float(knn["knn_local_purity"].mean()),
        "route_conflict_rate": float(knn["knn_route_conflict"].mean()),
    }
    lines = [
        "# ECG-Style RL Reliability Suite",
        "",
        "## Purpose",
        "",
        "This suite transfers the ECG project's broad reliability logic into the surgical RL project.",
        "It is not only an embedding analysis. It covers representation geometry, decision uncertainty, trajectory structure, perturbation/failure robustness, model-side intervention, and mechanism routing.",
        "",
        f"![ECG-style RL reliability suite]({figure.relative_to(path.parent).as_posix()})",
        "",
        "## 1. Representation / Embedding Structure",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| silhouette | {q['silhouette']:.3f} |",
        f"| Davies-Bouldin | {q['davies_bouldin']:.3f} |",
        f"| mean KNN label entropy | {knn_summary['mean_knn_entropy']:.3f} |",
        f"| mean local purity | {knn_summary['mean_local_purity']:.3f} |",
        f"| KNN route conflict rate | {knn_summary['route_conflict_rate']:.3f} |",
        "",
        "Closest route-centroid pairs:",
        "",
        "| Route A | Route B | Distance | Normalized distance |",
        "|---|---|---:|---:|",
    ]
    for _, row in centroid.sort_values("normalized_centroid_distance").head(6).iterrows():
        lines.append(
            f"| {row['route_a']} | {row['route_b']} | {row['centroid_distance']:.3f} | {row['normalized_centroid_distance']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## 2. Decision Boundary / Confidence",
            "",
            "| Score | Route-error AUROC | Review/abort AUROC | Review/abort AUPRC |",
            "|---|---:|---:|---:|",
        ]
    )
    for _, row in uncertainty.iterrows():
        lines.append(
            f"| {row['score']} | {row['route_error_AUROC']:.3f} | {row['review_or_abort_AUROC']:.3f} | {row['review_or_abort_AUPRC']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## 3. Trajectory / Signal Structure And Robustness",
            "",
            "Highest-risk injected failures by mean review score:",
            "",
            "| Failure | Episodes | Mean review score | Review/abort rate | Mean final distance |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for _, row in robustness.head(10).iterrows():
        lines.append(
            f"| {row['failure']} | {int(row['episodes'])} | {row['mean_review_score']:.3f} | "
            f"{row['review_or_abort_rate']:.3f} | {row['mean_final_distance']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## 4. Model Upgrade / Intervention",
            "",
            "The model-side upgrade is the multi-signal reliability head and four-way mechanism router generated by `scripts/run_multisignal_reliability_upgrade.py`.",
            "",
            "| Router metric | Value |",
            "|---|---:|",
            f"| accuracy | {route_summary['accuracy']:.3f} |",
            f"| macro-F1 | {route_summary['macro_f1']:.3f} |",
            f"| missed review-or-abort rate | {route_summary['missed_review_or_abort_rate']:.3f} |",
            f"| false review-or-abort rate | {route_summary['false_review_or_abort_rate']:.3f} |",
            "",
            "## 5. Interpretation",
            "",
            "This suite follows the ECG logic: broad analysis first, model intervention second, mechanism routing third.",
            "For the current RL project, the evidence suggests that multiple runtime signals are more useful than a single embedding-only score.",
            "The policy-improvement side remains limited, so the mature claim should emphasize reliability supervision and route-specific recovery.",
            "",
            "## Limitations",
            "",
            "- The analysis uses simulator and injected-failure labels, not surgeon annotations.",
            "- Route features include some episode-level summaries, so this is a research supervisor audit before a fully online controller.",
            "- The held-out split is internal and small for some rare routes such as `abort_candidate`.",
            "- The suite does not claim clinical validation, hardware validation, or solved surgical autonomy.",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.figure_dir.mkdir(parents=True, exist_ok=True)
    if args.run_multisignal_first:
        subprocess.run(
            [sys.executable, "scripts/run_multisignal_reliability_upgrade.py"],
            cwd=ROOT,
            check=True,
        )

    df = prepare_dataset(args.scored_episodes)
    train, validation, test = split_masks(df)
    columns = feature_columns("all")
    x_raw = df[columns].to_numpy(dtype=float)
    x, _, _ = standardize(x_raw[train], x_raw)
    projected, _, _ = pca_projection(x, 3)

    y_review = df["review_or_abort"].to_numpy(dtype=int)
    review_weights, review_bias = fit_binary_logistic(x[train], y_review[train])
    review_scores = sigmoid(x @ review_weights + review_bias)
    y_route = df["route_idx"].to_numpy(dtype=int)
    route_weights, route_bias = fit_multiclass_logistic(x[train], y_route[train], len(ROUTES))
    route_probs = softmax(x @ route_weights + route_bias)
    route_pred = route_probs.argmax(axis=1)
    _, route_summary = route_metrics(y_route[test], route_pred[test], route_probs[test])

    centroid, quality, prototype = representation_analysis(df, x, columns)
    knn = knn_analysis(df, x, train)
    uncertainty = decision_uncertainty(df, route_probs, review_scores, route_pred)
    trajectory = trajectory_structure_analysis(df)
    robustness = robustness_analysis(df, review_scores)

    centroid.to_csv(args.out_dir / "ecg_style_rl_centroid_distances.csv", index=False)
    quality.to_csv(args.out_dir / "ecg_style_rl_representation_quality.csv", index=False)
    prototype.to_csv(args.out_dir / "ecg_style_rl_prototype_diagnostics.csv", index=False)
    knn.to_csv(args.out_dir / "ecg_style_rl_knn_diagnostics.csv", index=False)
    uncertainty.to_csv(args.out_dir / "ecg_style_rl_uncertainty_diagnostics.csv", index=False)
    trajectory.to_csv(args.out_dir / "ecg_style_rl_trajectory_structure.csv", index=False)
    robustness.to_csv(args.out_dir / "ecg_style_rl_robustness_by_failure.csv", index=False)
    pd.DataFrame([route_summary]).to_csv(args.out_dir / "ecg_style_rl_mechanism_router_summary.csv", index=False)

    figure = plot_suite(df, projected, review_scores, robustness, args.figure_dir)
    write_report(args.report, centroid, quality, knn, uncertainty, robustness, route_summary, figure)

    manifest = {
        "centroid": str(args.out_dir / "ecg_style_rl_centroid_distances.csv"),
        "quality": str(args.out_dir / "ecg_style_rl_representation_quality.csv"),
        "prototype": str(args.out_dir / "ecg_style_rl_prototype_diagnostics.csv"),
        "knn": str(args.out_dir / "ecg_style_rl_knn_diagnostics.csv"),
        "uncertainty": str(args.out_dir / "ecg_style_rl_uncertainty_diagnostics.csv"),
        "trajectory": str(args.out_dir / "ecg_style_rl_trajectory_structure.csv"),
        "robustness": str(args.out_dir / "ecg_style_rl_robustness_by_failure.csv"),
        "router": str(args.out_dir / "ecg_style_rl_mechanism_router_summary.csv"),
        "figure": str(figure),
        "report": str(args.report),
    }
    (args.out_dir / "ecg_style_rl_suite_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
