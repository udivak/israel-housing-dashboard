# Udi Experiments

Track model runs, feature changes, and results here.

| # | Model | Main change | MAPE | MAE | R² | Notes |
|---|-------|-------------|------|-----|----|-------|
| 1 | `udi/random_forest_v1` | RF suite over temporal-only features; best candidate `rf_deep` | 0.4705 | 684,681 | 0.3667 | `python3 run.py udi/random_forest_v1`; artifact: `prediction_service/artifacts/udi/random_forest_v1/model.joblib`; train/val/test = 53,671/6,708/6,710 |

## Run 1 Notes

- Candidate validation MAPE: `rf_fast` 0.4901, `rf_balanced` 0.4892, `rf_deep` 0.4890, `rf_wide` 0.4966.
- Final test metrics: MAPE 0.4705, MAE 684,681, RMSE 960,121, R² 0.3667, n=6,710.
- Data loader used `Sheet1` because the workbook has no `transactions` worksheet, filled 71,054 missing `real_price` values from `price`, and continued without `features_osm.csv` / `features_coords.csv`.
- Several temporal columns were all missing for usable priced rows, so sklearn skipped them during imputation; this likely explains the weak score.
