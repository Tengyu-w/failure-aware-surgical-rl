from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--l2", type=float, default=1.0)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args()


def mse(target: np.ndarray, prediction: np.ndarray) -> float:
    return float(np.mean((np.asarray(target) - np.asarray(prediction)) ** 2))


def seed_split_masks(seeds: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    residues = np.asarray(seeds, dtype=int) % 4
    return residues < 2, residues == 2, residues == 3


def split_metrics(
    inputs: np.ndarray,
    targets: np.ndarray,
    metadata: pd.DataFrame,
    mask: np.ndarray,
    residual: np.ndarray,
    blend: float,
) -> dict[str, float]:
    split_meta = metadata.loc[mask].reset_index(drop=True)
    clean_mask = split_meta["corruption"].eq("none").to_numpy()
    predictions = inputs[mask] + blend * residual
    return {
        "pairs": int(mask.sum()),
        "seeds": int(split_meta["seed"].nunique()),
        "corrupt_mse_before": mse(targets[mask][~clean_mask], inputs[mask][~clean_mask]),
        "corrupt_mse_after": mse(targets[mask][~clean_mask], predictions[~clean_mask]),
        "clean_mse_after": mse(targets[mask][clean_mask], predictions[clean_mask]),
    }


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    values = np.load(args.dataset)
    metadata = pd.read_csv(args.metadata)
    inputs = np.asarray(values["inputs"], dtype=np.float64)
    targets = np.asarray(values["targets"], dtype=np.float64)
    if len(inputs) != len(targets) or len(inputs) != len(metadata):
        raise ValueError("Pair arrays and metadata are not aligned")
    train_mask, validation_mask, test_mask = seed_split_masks(metadata["seed"].to_numpy(dtype=int))
    if min(train_mask.sum(), validation_mask.sum(), test_mask.sum()) == 0:
        raise ValueError("Seed split must contain training, validation, and test pairs")
    input_mean = inputs[train_mask].mean(axis=0)
    input_std = inputs[train_mask].std(axis=0)
    input_std[input_std < 1e-8] = 1.0
    x = (inputs[train_mask] - input_mean) / input_std
    residual_targets = targets[train_mask] - inputs[train_mask]
    design = np.concatenate([x, np.ones((len(x), 1))], axis=1)
    regularizer = np.eye(design.shape[1]) * args.l2
    regularizer[-1, -1] = 0.0
    solution = np.linalg.solve(design.T @ design + regularizer, design.T @ residual_targets)
    residual_weights = solution[:-1]
    residual_bias = solution[-1]

    validation_x = (inputs[validation_mask] - input_mean) / input_std
    validation_residual = validation_x @ residual_weights + residual_bias
    validation_meta = metadata.loc[validation_mask].reset_index(drop=True)
    validation_clean_mask = validation_meta["corruption"].eq("none").to_numpy()
    blend_rows = []
    for blend in np.linspace(0.0, 1.0, 21):
        predictions = inputs[validation_mask] + blend * validation_residual
        clean_error = mse(
            targets[validation_mask][validation_clean_mask],
            predictions[validation_clean_mask],
        )
        corrupt_error = mse(
            targets[validation_mask][~validation_clean_mask],
            predictions[~validation_clean_mask],
        )
        blend_rows.append({"blend": float(blend), "clean_mse": clean_error, "corrupt_mse": corrupt_error, "objective": corrupt_error + 3.0 * clean_error})
    selected = min(blend_rows, key=lambda row: row["objective"])
    blend = float(selected["blend"])
    test_x = (inputs[test_mask] - input_mean) / input_std
    test_residual = test_x @ residual_weights + residual_bias
    validation_metrics = split_metrics(
        inputs,
        targets,
        metadata,
        validation_mask,
        validation_residual,
        blend,
    )
    test_metrics = split_metrics(inputs, targets, metadata, test_mask, test_residual, blend)
    metrics = {
        "train_pairs": int(train_mask.sum()),
        "train_seeds": int(metadata.loc[train_mask, "seed"].nunique()),
        "validation": validation_metrics,
        "test": test_metrics,
        "feature_dim": int(inputs.shape[1]),
        "blend": blend,
        "split_rule": "seed_mod_4: train={0,1}, validation={2}, test={3}",
    }
    metrics["test"]["corrupt_mse_reduction"] = 1.0 - test_metrics["corrupt_mse_after"] / max(
        test_metrics["corrupt_mse_before"], 1e-12
    )
    np.savez_compressed(args.out_dir / "visual_denoising_adapter.npz", input_mean=input_mean, input_std=input_std, residual_weights=residual_weights, residual_bias=residual_bias, blend=np.array([blend]))
    pd.DataFrame(blend_rows).to_csv(args.out_dir / "blend_validation.csv", index=False)
    (args.out_dir / "adapter_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"model={args.out_dir / 'visual_denoising_adapter.npz'}")
    print(f"test_corrupt_mse_reduction={metrics['test']['corrupt_mse_reduction']:.4f}")
    print(f"test_clean_mse_after={metrics['test']['clean_mse_after']:.8f}")


if __name__ == "__main__":
    main()
