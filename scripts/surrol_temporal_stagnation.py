from __future__ import annotations

from collections import deque
from pathlib import Path

import numpy as np


FEATURE_NAMES = [
    "step_fraction",
    "current_risk",
    "memory_distance",
    "total_recovery_fraction",
    "consecutive_recovery_fraction",
    "recent_risk_mean",
    "recent_risk_std",
    "recent_risk_slope",
    "recent_high_risk_fraction",
    "recent_recovery_fraction",
]


class TemporalFeatureState:
    def __init__(self, window: int = 8, max_steps: int = 50):
        self.window = max(2, int(window))
        self.max_steps = max(1, int(max_steps))
        self.risks: deque[float] = deque(maxlen=self.window - 1)
        self.high_risks: deque[float] = deque(maxlen=self.window - 1)
        self.recoveries: deque[float] = deque(maxlen=self.window - 1)
        self.total_recoveries = 0
        self.consecutive_recoveries = 0

    def features(self, step: int, risk: float, memory_distance: float, high_risk: bool) -> np.ndarray:
        recent_risks = np.asarray([*self.risks, float(risk)], dtype=np.float64)
        recent_high = np.asarray([*self.high_risks, float(high_risk)], dtype=np.float64)
        recent_recovery = np.asarray([*self.recoveries, 0.0], dtype=np.float64)
        slope = 0.0 if len(recent_risks) < 2 else float((recent_risks[-1] - recent_risks[0]) / (len(recent_risks) - 1))
        distance = float(memory_distance) if np.isfinite(memory_distance) else 0.0
        return np.asarray(
            [
                min(1.0, float(step) / self.max_steps),
                float(risk),
                distance,
                self.total_recoveries / max(1.0, float(self.max_steps)),
                self.consecutive_recoveries / max(1.0, float(self.window)),
                float(recent_risks.mean()),
                float(recent_risks.std()),
                slope,
                float(recent_high.mean()),
                float(recent_recovery.mean()),
            ],
            dtype=np.float64,
        )

    def update(self, risk: float, high_risk: bool, recovered: bool) -> None:
        self.risks.append(float(risk))
        self.high_risks.append(float(high_risk))
        self.recoveries.append(float(recovered))
        if recovered:
            self.total_recoveries += 1
            self.consecutive_recoveries += 1
        else:
            self.consecutive_recoveries = 0


class TemporalStagnationHead:
    def __init__(self, path: Path):
        values = np.load(path)
        self.feature_mean = values["feature_mean"]
        self.feature_std = values["feature_std"]
        self.weights = values["logistic_weights"]
        self.bias = float(values["logistic_bias"][0])
        self.threshold = float(values["threshold"][0])
        self.min_step = int(values["min_step"][0])
        self.window = int(values["window"][0])

    def score(self, features: np.ndarray) -> float:
        normalized = (np.asarray(features, dtype=np.float64) - self.feature_mean) / self.feature_std
        logit = float(normalized @ self.weights + self.bias)
        return float(1.0 / (1.0 + np.exp(-np.clip(logit, -40.0, 40.0))))
