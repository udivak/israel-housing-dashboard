"""
LightGBM v1 — baseline.

הקובץ בנוי כ-"jupyter cells" (# %%) — אפשר לפתוח אותו ב-VS Code או PyCharm
ולהריץ תא-אחר-תא כמו מחברת. ה-runner (run.py) משתמש רק בפונקציות train() ו-predict().

    python run.py moses/lightgbm_v1
"""

# %% Imports
from __future__ import annotations

import numpy as np
import pandas as pd
import lightgbm as lgb


# %% [interactive] טעינת דאטה — לא רץ דרך run.py
# זה תא לחקירה אישית. אפשר להריץ אותו ב-IDE ולראות את הדאטה.
if False:  # ← שנה ל-True כדי לחקור
    from common.data import load_data, build_dataset
    df = build_dataset()
    print(df.shape)
    print(df.head())

    X_train, y_train, X_val, y_val, X_test, y_test = load_data()
    print(f"train={len(X_train):,}  val={len(X_val):,}  test={len(X_test):,}")


# %% Hyperparameters
PARAMS = dict(
    n_estimators=2000,
    learning_rate=0.05,
    num_leaves=63,
    min_child_samples=20,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_alpha=0.1,
    reg_lambda=0.1,
    random_state=42,
    n_jobs=-1,
    verbose=-1,
)


# %% Training
def train(X_train: pd.DataFrame, y_train, X_val: pd.DataFrame, y_val) -> lgb.LGBMRegressor:
    model = lgb.LGBMRegressor(**PARAMS)
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        eval_metric="mape",
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(100)],
    )
    return model


# %% Prediction
def predict(model: lgb.LGBMRegressor, X: pd.DataFrame) -> np.ndarray:
    return model.predict(X)


# %% [interactive] Feature importance
if False:
    import matplotlib.pyplot as plt
    from common.data import load_data
    X_train, y_train, X_val, y_val, X_test, y_test = load_data()
    model = train(X_train, y_train, X_val, y_val)
    lgb.plot_importance(model, max_num_features=30, importance_type="gain")
    plt.tight_layout(); plt.show()
