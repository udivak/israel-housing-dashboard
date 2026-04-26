"""
Neural network template for Udi.

Run with:
    python run.py udi/nn_v1
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def train(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
) -> Any:
    """Train and return a neural network regressor."""
    raise NotImplementedError("Implement neural network training logic here.")


def predict(model: Any, X: pd.DataFrame) -> np.ndarray:
    """Return predicted real_price values for X."""
    raise NotImplementedError("Implement neural network prediction logic here.")
