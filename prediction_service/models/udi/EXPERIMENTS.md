# Udi Experiments

Track model runs, feature changes, and results here.

| # | Model | Main change | MAPE | MAE | R² | Notes |
|---|-------|-------------|------|-----|----|-------|
| 1 | `udi/random_forest_v1` | RF suite over temporal-only features; best candidate `rf_deep` | 0.4705 | 684,681 | 0.3667 | `python3 run.py udi/random_forest_v1`; artifact: `prediction_service/artifacts/udi/random_forest_v1/model.joblib`; train/val/test = 53,671/6,708/6,710 |
| 2 | `udi/xgboost_v1` | XGBoost 5-candidate sweep on loader v2 with early stopping; best `xgb_slow_wide` | 0.2047 | 285,538 | 0.8143 | `python3 run.py udi/xgboost_v1 --data v2`; artifact: `prediction_service/artifacts/udi/xgboost_v1/model.joblib`; train/val/test = 47,550/5,943/5,945; same OrdinalEncoder preprocessor as `udi/random_forest_v2` so RF↔XGB are apples-to-apples |

## Run 1 Notes

- Candidate validation MAPE: `rf_fast` 0.4901, `rf_balanced` 0.4892, `rf_deep` 0.4890, `rf_wide` 0.4966.
- Final test metrics: MAPE 0.4705, MAE 684,681, RMSE 960,121, R² 0.3667, n=6,710.
- Data loader used `Sheet1` because the workbook has no `transactions` worksheet, filled 71,054 missing `real_price` values from `price`, and continued without `features_osm.csv` / `features_coords.csv`.
- Several temporal columns were all missing for usable priced rows, so sklearn skipped them during imputation; this likely explains the weak score.

## Run 2 Notes

- Candidate validation MAPE / `best_iteration` (early stopping rounds=100, n_estimators=4000):
  - `xgb_fast`        val_mape=0.2032  best_iter=1034
  - `xgb_balanced`    val_mape=0.2015  best_iter=778
  - `xgb_deep`        val_mape=0.1951  best_iter=889
  - `xgb_regularized` val_mape=0.2000  best_iter=1383
  - `xgb_slow_wide`   val_mape=0.1937  best_iter=793  ← winner
- Final test metrics: MAPE 0.2047, MAE 285,538, RMSE 519,800, R² 0.8143, n=5,945.
- vs `udi/random_forest_v2` (MAPE 0.2061, MAE 292,847, R² 0.801): XGBoost wins on every metric — slightly better MAPE, ~7K lower MAE, +0.014 R². The shared OrdinalEncoder preprocessor makes this a clean head-to-head; categorical handling is identical, so the delta is the booster vs forest itself plus per-tree column subsampling.
- Top feature importances: `lat`, `deal_nature`, `rooms`, `dist_to_kindergarten`, `lon` — geography + structural attributes dominate, matching what RF v2 emphasized.
- Pipeline trick: fit the `ColumnTransformer` once, transform `X_train`/`X_val` to dense matrices, fit each `XGBRegressor` directly with `eval_set=[(X_val_t, y_val_log)]`, then post-hoc wrap winner into `Pipeline([("preprocess", pre), ("model", booster)])`. Avoids xgboost ≥ 2.0 deprecating `model__early_stopping_rounds` as a `pipeline.fit` kwarg, and avoids fitting the preprocessor twice.
- Open follow-ups: `xgboost_v2` to layer on native categorical (`enable_categorical=True`) and skip the OrdinalEncoder; Optuna sweep around `xgb_slow_wide` (deep + low LR is clearly the winning regime here).
