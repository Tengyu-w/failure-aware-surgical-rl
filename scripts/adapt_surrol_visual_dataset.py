from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from train_surrol_ppo_failure_aware import LinearVisualDenoisingAdapter  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--visual-adapter", type=Path, required=True)
    parser.add_argument("--proprio-dim", type=int, default=7)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args()


def adapt_observations(
    observations: np.ndarray,
    adapter: LinearVisualDenoisingAdapter,
    proprio_dim: int,
) -> np.ndarray:
    observations = np.asarray(observations, dtype=np.float32)
    if observations.ndim != 2 or observations.shape[1] <= proprio_dim:
        raise ValueError("Expected a 2D proprio-plus-visual observation array")
    adapted = observations.copy()
    adapted[:, proprio_dim:] = np.asarray(
        [adapter.transform(row) for row in observations[:, proprio_dim:]],
        dtype=np.float32,
    )
    return adapted


def main() -> None:
    args = parse_args()
    values = np.load(args.dataset)
    if "observations" not in values.files:
        raise ValueError("Dataset must contain an observations array")
    adapter = LinearVisualDenoisingAdapter(args.visual_adapter)
    observations = np.asarray(values["observations"], dtype=np.float32)
    adapted_observations = adapt_observations(observations, adapter, args.proprio_dim)
    arrays = {key: np.asarray(values[key]) for key in values.files}
    arrays["observations"] = adapted_observations

    args.out_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.out_dir / f"{args.dataset.stem}_adapted.npz"
    np.savez_compressed(output_path, **arrays)
    summary = {
        "source_dataset": str(args.dataset),
        "visual_adapter": str(args.visual_adapter),
        "output_dataset": str(output_path),
        "observations": list(adapted_observations.shape),
        "proprio_dim": args.proprio_dim,
        "mean_visual_change_l2": float(
            np.linalg.norm(
                adapted_observations[:, args.proprio_dim :] - observations[:, args.proprio_dim :],
                axis=1,
            ).mean()
        ),
    }
    (args.out_dir / "adaptation_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(f"dataset={output_path}")
    print(f"mean_visual_change_l2={summary['mean_visual_change_l2']:.6f}")


if __name__ == "__main__":
    main()
