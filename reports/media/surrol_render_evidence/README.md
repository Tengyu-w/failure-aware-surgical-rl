# SurRoL Render Evidence

These assets export raw SurRoL/PyBullet RGB rollouts for application and repository evidence.
They complement the CSV metrics and recovery figures by showing that the project was actually run inside SurRoL simulation tasks.

| Task | Steps | Success | Final distance | GIF | MP4 | Trace |
|---|---:|---:|---:|---|---|---|
| NeedleReach | 20 | 1 | 0.0188 | `needlereach_oracle_rollout.gif` | `needlereach_oracle_rollout.mp4` | `rollout_trace.csv` |
| NeedlePick | 40 | 1 | 0.0172 | `needlepick_oracle_rollout.gif` | `needlepick_oracle_rollout.mp4` | `rollout_trace.csv` |
| GauzeRetrieve | 34 | 1 | 0.0106 | `gauzeretrieve_oracle_rollout.gif` | `gauzeretrieve_oracle_rollout.mp4` | `rollout_trace.csv` |

Recommended GitHub use: keep one GIF and two still frames under `reports/media/surrol_render_evidence/`,
then link them from the main README as migration evidence from the custom 3D proxy to SurRoL.
