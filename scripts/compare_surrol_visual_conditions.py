from __future__ import annotations

import argparse
import csv
from pathlib import Path
from statistics import mean, pstdev


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", type=Path, required=True)
    parser.add_argument("--corrupt", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def key(row: dict[str, str]) -> tuple[float, int, int, int]:
    return (
        float(row["progress_scale"]),
        int(row["train_seed"]),
        int(row["episode"]),
        int(row["seed"]),
    )


def main() -> None:
    args = parse_args()
    clean = {key(row): row for row in read_rows(args.clean)}
    corrupt = {key(row): row for row in read_rows(args.corrupt)}
    if clean.keys() != corrupt.keys():
        missing_corrupt = sorted(clean.keys() - corrupt.keys())
        missing_clean = sorted(corrupt.keys() - clean.keys())
        raise RuntimeError(f"Condition keys differ: missing_corrupt={missing_corrupt}, missing_clean={missing_clean}")

    paired = []
    for pair_key in sorted(clean):
        clean_row = clean[pair_key]
        corrupt_row = corrupt[pair_key]
        paired.append(
            {
                "progress_scale": pair_key[0],
                "train_seed": pair_key[1],
                "episode": pair_key[2],
                "eval_seed": pair_key[3],
                "clean_success": float(clean_row["success"]),
                "corrupt_success": float(corrupt_row["success"]),
                "clean_final_distance": float(clean_row["final_distance"]),
                "corrupt_final_distance": float(corrupt_row["final_distance"]),
                "delta_final_distance": float(corrupt_row["final_distance"]) - float(clean_row["final_distance"]),
                "delta_min_distance": float(corrupt_row["min_distance"]) - float(clean_row["min_distance"]),
                "delta_net_progress": float(corrupt_row["net_distance_progress"]) - float(clean_row["net_distance_progress"]),
                "corruption_magnitude": float(corrupt_row["mean_visual_corruption_magnitude"]),
            }
        )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_rows(args.out_dir / "paired_condition_deltas.csv", paired)
    seed_rows = []
    for scale in sorted({float(row["progress_scale"]) for row in paired}):
        scale_rows = [row for row in paired if float(row["progress_scale"]) == scale]
        for train_seed in sorted({int(row["train_seed"]) for row in scale_rows}):
            rows = [row for row in scale_rows if int(row["train_seed"]) == train_seed]
            seed_rows.append(
                {
                    "progress_scale": scale,
                    "train_seed": train_seed,
                    "pairs": len(rows),
                    "mean_delta_final_distance": mean(float(row["delta_final_distance"]) for row in rows),
                    "mean_delta_min_distance": mean(float(row["delta_min_distance"]) for row in rows),
                    "mean_delta_net_progress": mean(float(row["delta_net_progress"]) for row in rows),
                    "mean_corruption_magnitude": mean(float(row["corruption_magnitude"]) for row in rows),
                }
            )
    write_rows(args.out_dir / "paired_condition_seed_summary.csv", seed_rows)

    scale_rows = []
    for scale in sorted({float(row["progress_scale"]) for row in seed_rows}):
        rows = [row for row in seed_rows if float(row["progress_scale"]) == scale]
        final_deltas = [float(row["mean_delta_final_distance"]) for row in rows]
        scale_rows.append(
            {
                "progress_scale": scale,
                "train_seeds": len(rows),
                "mean_seed_delta_final_distance": mean(final_deltas),
                "std_seed_delta_final_distance": pstdev(final_deltas),
                "mean_seed_delta_min_distance": mean(float(row["mean_delta_min_distance"]) for row in rows),
                "mean_seed_delta_net_progress": mean(float(row["mean_delta_net_progress"]) for row in rows),
                "mean_corruption_magnitude": mean(float(row["mean_corruption_magnitude"]) for row in rows),
            }
        )
    write_rows(args.out_dir / "paired_condition_scale_summary.csv", scale_rows)
    print(f"paired_deltas={args.out_dir / 'paired_condition_deltas.csv'}")
    print(f"scale_summary={args.out_dir / 'paired_condition_scale_summary.csv'}")


if __name__ == "__main__":
    main()
