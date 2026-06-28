# SurRoL Render Evidence

These assets export raw SurRoL/PyBullet RGB rollouts for repository evidence.
They complement the CSV metrics and recovery figures by showing that the project was actually run inside SurRoL simulation tasks.

| Task | Steps | Success | Final distance | GIF | MP4 | Trace |
|---|---:|---:|---:|---|---|---|
| NeedleReach | 20 | 1 | 0.0188 | `needlereach_oracle_rollout.gif` | `needlereach_oracle_rollout.mp4` | `rollout_trace.csv` |
| NeedlePick | 40 | 1 | 0.0172 | `needlepick_oracle_rollout.gif` | `needlepick_oracle_rollout.mp4` | `rollout_trace.csv` |
| GauzeRetrieve | 34 | 1 | 0.0106 | `gauzeretrieve_oracle_rollout.gif` | `gauzeretrieve_oracle_rollout.mp4` | `rollout_trace.csv` |

## Selected Rendered Frames

| Task | Initial frame | Later frame | Rollout media |
|---|---|---|---|
| NeedleReach | ![NeedleReach initial frame](needlereach/frames/needlereach_step_000.png) | ![NeedleReach later frame](needlereach/frames/needlereach_step_020.png) | [GIF](needlereach/needlereach_oracle_rollout.gif), [MP4](needlereach/needlereach_oracle_rollout.mp4), [trace CSV](needlereach/rollout_trace.csv) |
| NeedlePick | ![NeedlePick initial frame](needlepick/frames/needlepick_step_000.png) | ![NeedlePick later frame](needlepick/frames/needlepick_step_040.png) | [GIF](needlepick/needlepick_oracle_rollout.gif), [MP4](needlepick/needlepick_oracle_rollout.mp4), [trace CSV](needlepick/rollout_trace.csv) |
| GauzeRetrieve | ![GauzeRetrieve initial frame](gauzeretrieve/frames/gauzeretrieve_step_000.png) | ![GauzeRetrieve later frame](gauzeretrieve/frames/gauzeretrieve_step_034.png) | [GIF](gauzeretrieve/gauzeretrieve_oracle_rollout.gif), [MP4](gauzeretrieve/gauzeretrieve_oracle_rollout.mp4), [trace CSV](gauzeretrieve/rollout_trace.csv) |

The main README links these media files as migration evidence from the custom
3D proxy to SurRoL.

These rollouts are included as visual simulation evidence only. They should be
read together with the route-specific recovery tables and controller-level
figures rather than as real surgical footage or clinical validation.
