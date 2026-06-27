# Figure Atlas

This document explains how the public figures and media are organized. The goal
is to make the visual evidence readable as a research story rather than as a
loose folder of PNG files.

## Figure And Media Groups

| Stage | Folder | What The Reader Should Look For |
| --- | --- | --- |
| SurRoL rendered evidence | `reports/media/surrol_render_evidence/` | Actual SurRoL/PyBullet rendered rollouts for NeedleReach, NeedlePick, and GauzeRetrieve. |
| Risk-gated tangent visuals | `reports/figures/risk_gated_tangent_visuals/` | Proxy controller architecture, budget/intervention result, trajectories, and snapshots. |
| Mechanism-routed tangent visuals | `reports/figures/mechanism_routed_tangent_v5d/` | ECG-inspired mechanism router metrics and Stage 1/Stage 2 activation split. |
| SurRoL phase-aware recovery | `reports/figures/surrol_phase_aware/` | Recovery success rates and representative distance curves. |
| Observable supervisor | `reports/figures/observable_proxy_risk/` and related observable folders | Threshold behavior and observable jaw-stuck recovery evidence. |
| Learned route classifier | `reports/tables/surrol_learned_route_classifier_*.csv` and report tables | Route prediction metrics, confusion table, and feature weights. |
| Embedding-risk PPO | `reports/figures/embedding_risk_training_pilot/` | Reward shaping and hard-negative curriculum training summaries. |

## Recommended Reading Order

1. Start with `reports/media/surrol_render_evidence/` to see that the project
   includes SurRoL/PyBullet rendered surgical simulation, not only proxy plots.
2. Open `reports/figures/risk_gated_tangent_visuals/aggregate_budget_intervention.png`
   to understand the controller-level safety/activation tradeoff.
3. Open `reports/figures/mechanism_routed_tangent_v5d/mechanism_router_metrics.png`
   and `mechanism_router_stage_split.png` to understand the ECG-inspired
   mechanism-routing upgrade.
4. Read SurRoL recovery figures and tables together with
   `reports/surrol_master_results.md`.
5. Use embedding-risk training figures only as preliminary training-loop
   evidence, not as the main project claim.

## Interpretation Notes

The proxy trajectory and controller figures are not SurRoL screenshots. They
belong to the custom constrained surgical-tool environment.

The SurRoL media are actual rendered simulation rollouts. They support the
claim that the project migrated beyond the custom proxy, but they are still
simulation evidence.

The mechanism-routed figures should be read as controller-level reliability
evidence. They show that the supervisor preserves budget safety while slightly
reducing unnecessary activation and separating route mechanisms.
