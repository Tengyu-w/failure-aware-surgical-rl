from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from statistics import mean, pstdev


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, default=ROOT / "runs" / "surrol_progress_multiseed_round28")
    parser.add_argument("--manifest-name", default="manifest.json")
    parser.add_argument("--output-prefix", default="")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    manifest = json.loads((args.run_root / args.manifest_name).read_text(encoding="utf-8"))
    prefix = f"{args.output_prefix}_" if args.output_prefix else ""
    episode_rows = []
    for run in manifest["runs"]:
        eval_path = Path(run["eval"])
        if not eval_path.exists():
            continue
        for row in read_csv(eval_path):
            row = dict(row)
            row["train_seed"] = run["seed"]
            row["progress_scale"] = run["scale"]
            episode_rows.append(row)
    if not episode_rows:
        raise RuntimeError("No completed evaluation CSV files found")

    write_csv(args.run_root / f"{prefix}episode_results.csv", episode_rows)
    seed_summaries = []
    for scale in sorted({float(row["progress_scale"]) for row in episode_rows}):
        scale_rows = [row for row in episode_rows if float(row["progress_scale"]) == scale]
        for train_seed in sorted({int(row["train_seed"]) for row in scale_rows}):
            rows = [row for row in scale_rows if int(row["train_seed"]) == train_seed]
            seed_summaries.append(
                {
                    "progress_scale": scale,
                    "train_seed": train_seed,
                    "eval_episodes": len(rows),
                    "success_rate": mean(float(row["success"]) for row in rows),
                    "mean_final_distance": mean(float(row["final_distance"]) for row in rows),
                    "mean_min_distance": mean(float(row["min_distance"]) for row in rows),
                    "mean_net_distance_progress": mean(float(row["net_distance_progress"]) for row in rows),
                    "unsafe_episode_rate": mean(float(row["unsafe_events"]) > 0 for row in rows),
                }
            )
    write_csv(args.run_root / f"{prefix}seed_summary.csv", seed_summaries)

    summaries = []
    for scale in sorted({float(row["progress_scale"]) for row in episode_rows}):
        rows = [row for row in seed_summaries if float(row["progress_scale"]) == scale]
        successes = [float(row["success_rate"]) for row in rows]
        final_distances = [float(row["mean_final_distance"]) for row in rows]
        min_distances = [float(row["mean_min_distance"]) for row in rows]
        progress = [float(row["mean_net_distance_progress"]) for row in rows]
        unsafe = [float(row["unsafe_episode_rate"]) for row in rows]
        summaries.append(
            {
                "progress_scale": scale,
                "train_seeds": len(rows),
                "eval_episodes": sum(int(row["eval_episodes"]) for row in rows),
                "mean_seed_success_rate": mean(successes),
                "std_seed_success_rate": pstdev(successes),
                "mean_final_distance": mean(final_distances),
                "std_seed_final_distance": pstdev(final_distances),
                "mean_min_distance": mean(min_distances),
                "mean_net_distance_progress": mean(progress),
                "std_seed_net_distance_progress": pstdev(progress),
                "unsafe_episode_rate": mean(unsafe),
            }
        )
    write_csv(args.run_root / f"{prefix}scale_summary.csv", summaries)
    candidate = sorted(
        summaries,
        key=lambda row: (
            -float(row["mean_seed_success_rate"]),
            float(row["mean_final_distance"]),
            -float(row["mean_net_distance_progress"]),
        ),
    )[0]
    selection = {
        "selection_rule": "highest success rate, then lowest final distance, then highest net distance progress",
        "candidate": candidate,
        "limitations": [
            "three training seeds are sufficient for screening but too few for tight confidence intervals",
            "selection and reporting use the same evaluation seeds; a fresh confirmation set is still required",
            "pseudo_vision results do not prove robustness under rendered RGB corruption",
        ],
    }
    (args.run_root / f"{prefix}candidate_selection.json").write_text(json.dumps(selection, indent=2), encoding="utf-8")
    print(f"episode_results={args.run_root / f'{prefix}episode_results.csv'}")
    print(f"scale_summary={args.run_root / f'{prefix}scale_summary.csv'}")
    print(f"candidate_scale={candidate['progress_scale']}")


if __name__ == "__main__":
    main()
