# Risk And Uncertainty Model Report

## Reliability Question

Can a lightweight uncertainty/risk model separate nominal executions from injected failure episodes across navigation and manipulation proxies, while supporting threshold-based review routing?

## Risk Scores

`risk_score = 0.62 * detection + 0.18 * residual task distance + 0.10 * safety risk + 0.06 * action-intervention risk + 0.04 * detection-delay risk`.

`learned_risk_score` is a lightweight logistic risk head trained with NumPy on even-numbered episodes and evaluated on odd-numbered episodes. It uses the proxy risk features, not raw simulator state.

## Held-Out Metric Summary

| Score | Group | Episodes | Failure Rate | AUROC | AUPRC | Brier | ECE | Mean Nominal Risk | Mean Failure Risk |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| proxy | overall | 450 | 0.778 | 1.000 | 1.000 | 0.097 | 0.281 | 0.033 | 0.648 |
| proxy | navigation | 200 | 0.750 | 1.000 | 1.000 | 0.096 | 0.278 | 0.041 | 0.643 |
| proxy | manipulation | 250 | 0.800 | 1.000 | 1.000 | 0.097 | 0.283 | 0.024 | 0.652 |
| learned | overall | 450 | 0.778 | 1.000 | 1.000 | 0.000 | 0.001 | 0.000 | 0.998 |
| learned | navigation | 200 | 0.750 | 1.000 | 1.000 | 0.000 | 0.001 | 0.000 | 0.998 |
| learned | manipulation | 250 | 0.800 | 1.000 | 1.000 | 0.000 | 0.001 | 0.001 | 0.998 |

## Learned-Risk Threshold Routing

| Risk Threshold | Precision | Recall | False Trigger Rate | Auto Coverage | Auto Failure Rate | TP | FP | FN | TN |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.200 | 1.000 | 1.000 | 0.000 | 0.222 | 0.000 | 350 | 0 | 0 | 100 |
| 0.400 | 1.000 | 1.000 | 0.000 | 0.222 | 0.000 | 350 | 0 | 0 | 100 |
| 0.600 | 1.000 | 1.000 | 0.000 | 0.222 | 0.000 | 350 | 0 | 0 | 100 |
| 0.800 | 1.000 | 1.000 | 0.000 | 0.222 | 0.000 | 350 | 0 | 0 | 100 |

## Interpretation

- The strongest current signal is still the explicit detection term; it separates synthetic failure episodes cleanly in this proxy suite.
- The learned risk head improves probability calibration relative to the raw proxy score on the current held-out split.
- Threshold routing reports how many episodes could run automatically versus be escalated for review.

## Limitations

- The learned risk head is trained and evaluated on synthetic injected failures from the same proxy family.
- It is not calibrated on held-out real surgical data and should not be presented as deployment validation.
- A stronger next step is to learn risk from trajectory windows before failure injection is revealed, then evaluate OOD transfer.
