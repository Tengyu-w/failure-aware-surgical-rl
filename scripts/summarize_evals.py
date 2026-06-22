from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("eval_csvs", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, default=Path("runs") / "summary.csv")
    return parser.parse_args()


def load_rows(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def infer_variant(path: Path) -> str:
    parent = path.parent.name
    if parent.startswith("smoke_"):
        return parent.removeprefix("smoke_")
    return parent


def summarize(path: Path) -> dict:
    rows = load_rows(path)
    numeric_keys = [key for key in rows[0].keys() if key != "episode"]
    summary = {"variant": infer_variant(path), "eval_csv": str(path), "episodes": len(rows)}
    for key in numeric_keys:
        values = np.array([float(row[key]) for row in rows], dtype=np.float64)
        summary[f"{key}_mean"] = float(values.mean())
        summary[f"{key}_std"] = float(values.std(ddof=0))
    return summary


def main() -> None:
    args = parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    summaries = [summarize(path) for path in args.eval_csvs]
    fieldnames = []
    for row in summaries:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with args.out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(summaries)

    print(f"summary_csv={args.out}")
    for row in summaries:
        print(
            " | ".join(
                [
                    f"variant={row['variant']}",
                    f"success={row['success_mean']:.3f}",
                    f"budget_exhausted={row['budget_exhausted_mean']:.3f}",
                    f"cost={row['cumulative_cost_mean']:.3f}",
                    f"distance={row['final_distance_mean']:.3f}",
                ]
            )
        )


if __name__ == "__main__":
    main()
