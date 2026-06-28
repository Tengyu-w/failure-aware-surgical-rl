from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "reports" / "tables"
FIGURES = ROOT / "reports" / "figures" / "failure_aware_vppv"
REPORT = ROOT / "reports" / "failure_aware_vppv_model_derived_routing.md"

SOURCE = TABLES / "failure_aware_vppv_step_dataset.csv"

CLUSTER_TABLE = TABLES / "failure_aware_vppv_model_derived_clusters.csv"
STEP_TABLE = TABLES / "failure_aware_vppv_model_derived_step_routes.csv"
SUMMARY_TABLE = TABLES / "failure_aware_vppv_model_derived_summary.csv"
CONFUSION_TABLE = TABLES / "failure_aware_vppv_model_derived_confusion.csv"
TRANSITION_TABLE = TABLES / "failure_aware_vppv_model_derived_transition_points.csv"

PCA_FIG = FIGURES / "failure_aware_vppv_model_derived_pca.png"
FINGERPRINT_FIG = FIGURES / "failure_aware_vppv_model_derived_cluster_fingerprints.png"

ROUTE_ORDER = [
    "continue",
    "reobserve_reestimate",
    "depth_reestimate_or_cautious_approach",
    "low_gain_correction_or_replan",
]

FEATURE_COLUMNS = [
    "distance",
    "progress",
    "action_deviation",
    "perception_error_norm",
    "action_anomaly_score",
    "stall_score",
    "far_score",
    "no_improve_score",
    "triage_risk_score",
    "visual_state_evidence",
    "depth_scale_evidence",
    "policy_embedding_proxy_evidence",
    "action_outcome_mismatch_evidence",
    "progress_regularity_evidence",
    "local_neighborhood_proxy_evidence",
]

FINGERPRINT_COLUMNS = [
    "visual_state_evidence",
    "depth_scale_evidence",
    "policy_embedding_proxy_evidence",
    "action_outcome_mismatch_evidence",
    "progress_regularity_evidence",
    "local_neighborhood_proxy_evidence",
]


def markdown_table(df: pd.DataFrame, max_rows: int | None = None) -> str:
    if df.empty:
        return "_No rows._"
    out = df.copy()
    if max_rows is not None:
        out = out.head(max_rows)
    for col in out.columns:
        if pd.api.types.is_float_dtype(out[col]):
            out[col] = out[col].map(lambda x: "" if pd.isna(x) else f"{x:.3f}")
        else:
            out[col] = out[col].astype(str)
    header = "| " + " | ".join(out.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(out.columns)) + " |"
    rows = ["| " + " | ".join(row) + " |" for row in out.to_numpy(dtype=str)]
    return "\n".join([header, sep, *rows])


def standardize(train: pd.DataFrame, all_df: pd.DataFrame, columns: list[str]) -> tuple[np.ndarray, np.ndarray, pd.Series, pd.Series]:
    train_values = train[columns].astype(float)
    all_values = all_df[columns].astype(float)
    mean = train_values.mean(axis=0)
    std = train_values.std(axis=0).replace(0.0, 1.0)
    return (
        ((train_values - mean) / std).to_numpy(dtype=float),
        ((all_values - mean) / std).to_numpy(dtype=float),
        mean,
        std,
    )


def pca_transform(train_x: np.ndarray, all_x: np.ndarray, n_components: int = 6) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    _, _, vt = np.linalg.svd(train_x, full_matrices=False)
    components = vt[:n_components]
    return train_x @ components.T, all_x @ components.T, components


def kmeans_fit(x: np.ndarray, k: int = 10, iterations: int = 80, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    if len(x) < k:
        raise ValueError("Not enough rows for requested cluster count")
    first = int(rng.integers(0, len(x)))
    centers = [x[first]]
    distances = np.full(len(x), np.inf)
    for _ in range(1, k):
        distances = np.minimum(distances, np.sum((x - centers[-1]) ** 2, axis=1))
        probs = distances / max(float(distances.sum()), 1e-12)
        centers.append(x[int(rng.choice(len(x), p=probs))])
    centers = np.vstack(centers)

    labels = np.zeros(len(x), dtype=int)
    for _ in range(iterations):
        dist = ((x[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        new_labels = dist.argmin(axis=1)
        if np.array_equal(labels, new_labels):
            break
        labels = new_labels
        for idx in range(k):
            mask = labels == idx
            if mask.any():
                centers[idx] = x[mask].mean(axis=0)
    return centers


def assign_clusters(x: np.ndarray, centers: np.ndarray) -> np.ndarray:
    dist = ((x[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
    return dist.argmin(axis=1)


def derive_cluster_route(row: pd.Series) -> tuple[str, str]:
    visual = float(row["visual_state_evidence"])
    depth = float(row["depth_scale_evidence"])
    policy = float(row["policy_embedding_proxy_evidence"])
    mismatch = float(row["action_outcome_mismatch_evidence"])
    local = float(row["local_neighborhood_proxy_evidence"])
    progress = float(row["progress_regularity_evidence"])

    state_risk = max(visual, depth, policy, mismatch, local)
    if state_risk < 0.38 and progress < 0.82:
        return "continue", "low model-state risk"
    if depth >= 0.55 and depth >= visual * 0.75:
        return "depth_reestimate_or_cautious_approach", "depth fingerprint dominates"
    if visual >= 0.45 and visual >= policy:
        return "reobserve_reestimate", "visual-state fingerprint dominates"
    if max(policy, mismatch) >= 0.42 or (local >= 0.60 and policy >= 0.25):
        return "low_gain_correction_or_replan", "policy/action-outcome fingerprint dominates"
    if progress >= 0.90 and visual >= 0.25:
        return "reobserve_reestimate", "progress stall with visual residual"
    return "continue", "below route threshold"


def macro_f1(labels: pd.Series, preds: pd.Series) -> float:
    scores = []
    for route in ROUTE_ORDER:
        y = labels.eq(route)
        p = preds.eq(route)
        tp = int((y & p).sum())
        fp = int((~y & p).sum())
        fn = int((y & ~p).sum())
        if tp == 0 and fp == 0 and fn == 0:
            continue
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        scores.append(0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall))
    return float(np.mean(scores)) if scores else 0.0


def summarize_predictions(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split, group in df.groupby("split"):
        labels = group["expected_step_route"]
        preds = group["model_derived_route"]
        high = labels.ne("continue")
        rows.append(
            {
                "split": split,
                "step_rows": len(group),
                "episodes": int(group["episode_id"].nunique()),
                "accuracy": float(preds.eq(labels).mean()),
                "macro_f1": macro_f1(labels, preds),
                "missed_high_risk_step_rate": float((high & preds.eq("continue")).sum() / max(high.sum(), 1)),
                "false_alarm_on_nominal_step_rate": float((~high & preds.ne("continue")).sum() / max((~high).sum(), 1)),
                "route_diversity": int(preds.nunique()),
            }
        )
    return pd.DataFrame(rows).sort_values("split").reset_index(drop=True)


def confusion(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split, group in df.groupby("split"):
        for expected in ROUTE_ORDER:
            sub = group[group["expected_step_route"].eq(expected)]
            for predicted in ROUTE_ORDER:
                rows.append(
                    {
                        "split": split,
                        "expected_route": expected,
                        "predicted_route": predicted,
                        "count": int(sub["model_derived_route"].eq(predicted).sum()),
                    }
                )
    return pd.DataFrame(rows)


def transition_points(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for episode_id, group in df.sort_values("step").groupby("episode_id"):
        expected_high = group[group["expected_step_route"].ne("continue")]
        derived_high = group[group["model_derived_route"].ne("continue")]
        first_expected = np.nan if expected_high.empty else int(expected_high["step"].iloc[0])
        first_derived = np.nan if derived_high.empty else int(derived_high["step"].iloc[0])
        if not math.isnan(first_expected) and not math.isnan(first_derived):
            lead_time = first_expected - first_derived
        else:
            lead_time = np.nan
        rows.append(
            {
                "split": group["split"].iloc[0],
                "episode_id": episode_id,
                "task": group["task"].iloc[0],
                "mechanism_label": group["mechanism_label"].iloc[0],
                "expected_route": group["expected_step_route"].mode().iloc[0],
                "first_expected_step": first_expected,
                "first_model_derived_step": first_derived,
                "lead_time_positive_is_early": lead_time,
                "model_alerted": not math.isnan(first_derived),
            }
        )
    return pd.DataFrame(rows)


def make_figures(step_routes: pd.DataFrame, clusters: pd.DataFrame) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5), constrained_layout=True)
    sample = step_routes.sample(min(3500, len(step_routes)), random_state=4)
    route_colors = {
        "continue": "#8aa4b8",
        "reobserve_reestimate": "#4f7cac",
        "depth_reestimate_or_cautious_approach": "#c78b55",
        "low_gain_correction_or_replan": "#2f8f5f",
    }
    mechanism_colors = {
        "nominal": "#8aa4b8",
        "visual_estimation_bias": "#4f7cac",
        "depth_scale_error": "#c78b55",
        "policy_approach_drift": "#2f8f5f",
    }
    for route, color in route_colors.items():
        sub = sample[sample["model_derived_route"].eq(route)]
        axes[0].scatter(sub["pca_1"], sub["pca_2"], s=8, alpha=0.35, color=color, label=route)
    axes[0].set_title("Behavior-derived routes in rollout/PCA space")
    axes[0].set_xlabel("PC1")
    axes[0].set_ylabel("PC2")
    axes[0].legend(frameon=False, fontsize=8)
    axes[0].grid(alpha=0.25)

    for mechanism, color in mechanism_colors.items():
        sub = sample[sample["mechanism_label"].eq(mechanism)]
        axes[1].scatter(sub["pca_1"], sub["pca_2"], s=8, alpha=0.35, color=color, label=mechanism)
    axes[1].set_title("Held-out weak labels used only for evaluation")
    axes[1].set_xlabel("PC1")
    axes[1].set_ylabel("PC2")
    axes[1].legend(frameon=False, fontsize=8)
    axes[1].grid(alpha=0.25)

    fig.suptitle("Failure-aware VPPV behavior-derived routing assignment", fontweight="bold")
    fig.savefig(PCA_FIG, dpi=180)
    plt.close(fig)

    heat = clusters.set_index("cluster")[FINGERPRINT_COLUMNS]
    fig, ax = plt.subplots(figsize=(11, 5.2), constrained_layout=True)
    im = ax.imshow(heat.to_numpy(dtype=float), aspect="auto", cmap="viridis", vmin=0.0, vmax=1.0)
    ax.set_xticks(np.arange(len(FINGERPRINT_COLUMNS)))
    ax.set_xticklabels([c.replace("_evidence", "").replace("_", "\n") for c in FINGERPRINT_COLUMNS], fontsize=8)
    ax.set_yticks(np.arange(len(heat.index)))
    ax.set_yticklabels([f"C{idx}" for idx in heat.index], fontsize=8)
    for i in range(heat.shape[0]):
        for j in range(heat.shape[1]):
            ax.text(j, i, f"{heat.iloc[i, j]:.2f}", ha="center", va="center", color="white", fontsize=7)
    ax.set_title("Cluster fingerprints used to assign routes", fontweight="bold")
    fig.colorbar(im, ax=ax, fraction=0.028, pad=0.02)
    fig.savefig(FINGERPRINT_FIG, dpi=180)
    plt.close(fig)


def write_report(summary: pd.DataFrame, clusters: pd.DataFrame, transitions: pd.DataFrame) -> None:
    test_summary = summary[summary["split"].eq("test")]
    if test_summary.empty:
        test_summary = summary.tail(1)
    test = test_summary.iloc[0]

    transition_summary = (
        transitions.groupby(["split", "mechanism_label"], as_index=False)
        .agg(
            episodes=("episode_id", "count"),
            alert_rate=("model_alerted", "mean"),
            median_lead_time=("lead_time_positive_is_early", "median"),
        )
        .sort_values(["split", "mechanism_label"])
    )

    top_clusters = clusters.sort_values(["split", "cluster"]).copy()
    report = f"""# Failure-Aware VPPV Behavior-Derived Routing Assignment

## Purpose

This experiment addresses the main limitation of a hand-written mechanism
router. The earlier VPPV router used simulator fault families and weak labels
to define routes. Here the route assignment is derived from rollout behavior
first: distance, progress, action deviation, perception error,
policy-proxy evidence, action-outcome mismatch, and local neighborhood
instability are embedded, clustered, and converted into routes by cluster
fingerprints.

The mechanism labels are not used to form the clusters. They are used only at
the end to evaluate whether the discovered behavior regions align with the
weak mechanism routes.

This is not a full model-internal analysis of the teacher's original VPPV
policy. The original checkpoint, training set, hidden activations, and model
confidence outputs are not available in this repository. The closest available
substitute is a behavior-representation analysis over simulator rollouts.

## Method

```text
SurRoL/VPPV step traces
  -> behavior and evidence feature vector
  -> train-seed standardization
  -> PCA behavior representation
  -> k-means clusters on train seeds
  -> cluster fingerprints from evidence means
  -> route assignment from cluster fingerprint priority
  -> held-out seed evaluation against weak route labels
```

The assignment rule is cluster-level, not step-label lookup:

1. Low-risk behavior clusters route to `continue`.
2. Depth-dominant clusters route to `depth_reestimate_or_cautious_approach`.
3. Visual-state clusters route to `reobserve_reestimate`.
4. Policy/action-outcome clusters route to `low_gain_correction_or_replan`.

## Summary

{markdown_table(summary)}

Held-out test result: accuracy={test['accuracy']:.3f}, macro-F1={test['macro_f1']:.3f},
missed high-risk step rate={test['missed_high_risk_step_rate']:.3f}, nominal false
alarm rate={test['false_alarm_on_nominal_step_rate']:.3f}.

## Discovered Cluster Routes

{markdown_table(top_clusters[['split', 'cluster', 'rows', 'model_derived_route', 'assignment_reason', 'visual_state_evidence', 'depth_scale_evidence', 'policy_embedding_proxy_evidence', 'action_outcome_mismatch_evidence', 'progress_regularity_evidence', 'local_neighborhood_proxy_evidence']], max_rows=20)}

## Transition-Point Check

{markdown_table(transition_summary)}

## Figures

![behavior-derived PCA](figures/failure_aware_vppv/failure_aware_vppv_model_derived_pca.png)

![behavior-derived cluster fingerprints](figures/failure_aware_vppv/failure_aware_vppv_model_derived_cluster_fingerprints.png)

## Interpretation

This is closer to the ECG logic than the earlier hand-designed route table:
the system first finds behavior regions in a rollout representation, then
assigns routes from the evidence fingerprint of each region. The result is
still not a real clinical dataset result, and it is not teacher-model
hidden-layer analysis. It is a simulator-rollout, weak-label validation of
behavior-derived routing.

The strongest use of this result is to say: the project now has an explicit
bridge from rollout behavior and representation analysis to route assignment.
It should not be described as a fully independent discovery of surgical
failure mechanisms from real-world data.

## Output Tables

- `reports/tables/failure_aware_vppv_model_derived_clusters.csv`
- `reports/tables/failure_aware_vppv_model_derived_step_routes.csv`
- `reports/tables/failure_aware_vppv_model_derived_summary.csv`
- `reports/tables/failure_aware_vppv_model_derived_confusion.csv`
- `reports/tables/failure_aware_vppv_model_derived_transition_points.csv`
"""
    REPORT.write_text(report, encoding="utf-8")


def main() -> None:
    df = pd.read_csv(SOURCE)
    df = df.copy()
    df[FEATURE_COLUMNS] = df[FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    df["split"] = "train"
    for _, group in df[["task", "mechanism_label", "episode_id"]].drop_duplicates().groupby(
        ["task", "mechanism_label"]
    ):
        episodes = sorted(group["episode_id"].tolist())
        test_count = max(1, int(round(len(episodes) * 0.30)))
        test_episodes = set(episodes[-test_count:])
        df.loc[df["episode_id"].isin(test_episodes), "split"] = "test"

    train = df[df["split"].eq("train")].copy()
    train_x, all_x, _, _ = standardize(train, df, FEATURE_COLUMNS)
    train_pca, all_pca, _ = pca_transform(train_x, all_x, n_components=6)
    centers = kmeans_fit(train_pca, k=10, iterations=100, seed=11)
    df["cluster"] = assign_clusters(all_pca, centers)
    df["pca_1"] = all_pca[:, 0]
    df["pca_2"] = all_pca[:, 1]
    df["pca_3"] = all_pca[:, 2]

    cluster_rows = []
    train_clustered = df[df["split"].eq("train")].copy()
    for cluster, group in train_clustered.groupby("cluster"):
        means = group[FINGERPRINT_COLUMNS].mean()
        route, reason = derive_cluster_route(means)
        row = {
            "split": "train_fingerprint",
            "cluster": int(cluster),
            "rows": len(group),
            "episodes": int(group["episode_id"].nunique()),
            "model_derived_route": route,
            "assignment_reason": reason,
        }
        for col in FINGERPRINT_COLUMNS:
            row[col] = float(means[col])
        cluster_rows.append(row)
    clusters = pd.DataFrame(cluster_rows).sort_values(["split", "cluster"]).reset_index(drop=True)

    route_lookup = {
        int(row["cluster"]): row["model_derived_route"]
        for _, row in clusters.iterrows()
    }
    reason_lookup = {
        int(row["cluster"]): row["assignment_reason"]
        for _, row in clusters.iterrows()
    }
    df["model_derived_route"] = [
        route_lookup[int(cluster)] for cluster in df["cluster"]
    ]
    df["model_derived_reason"] = [
        reason_lookup[int(cluster)] for cluster in df["cluster"]
    ]

    summary = summarize_predictions(df)
    conf = confusion(df)
    transitions = transition_points(df)

    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    clusters.to_csv(CLUSTER_TABLE, index=False)
    df.to_csv(STEP_TABLE, index=False)
    summary.to_csv(SUMMARY_TABLE, index=False)
    conf.to_csv(CONFUSION_TABLE, index=False)
    transitions.to_csv(TRANSITION_TABLE, index=False)
    make_figures(df, clusters)
    write_report(summary, clusters, transitions)

    print(f"report={REPORT}")
    print(f"summary={SUMMARY_TABLE}")
    print(f"clusters={CLUSTER_TABLE}")


if __name__ == "__main__":
    main()
