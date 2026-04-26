# Udi Experiments

Track model runs, feature changes, and results here.

| # | Model | Main change | MAPE | MAE | R² | Notes |
|---|-------|-------------|------|-----|----|-------|
| 1 | `udi/random_forest_v1` | RF suite over temporal-only features; best candidate `rf_deep` | 0.4705 | 684,681 | 0.3667 | `python3 run.py udi/random_forest_v1`; artifact: `prediction_service/artifacts/udi/random_forest_v1/model.joblib`; train/val/test = 53,671/6,708/6,710 |
| 2 | `udi/xgboost_v1` | XGBoost 5-candidate sweep on loader v2 with early stopping; best `xgb_slow_wide` | 0.2047 | 285,538 | 0.8143 | `python3 run.py udi/xgboost_v1 --data v2`; artifact: `prediction_service/artifacts/udi/xgboost_v1/model.joblib`; train/val/test = 47,550/5,943/5,945; same OrdinalEncoder preprocessor as `udi/random_forest_v2` so RF↔XGB are apples-to-apples |
| 3 | `udi/xgboost_v2` | Native categorical (`enable_categorical=True`) + MAPE-aware early stopping + drop 4 dead features + tightened candidate grid; best `xgb_deep` | 0.2023 | 288,396 | 0.8129 | `python3 run.py udi/xgboost_v2 --data v2`; artifact: `prediction_service/artifacts/udi/xgboost_v2/model.joblib`; train/val/test = 47,550/5,943/5,945; loader unchanged |
| 4 | `udi/xgboost_v3` | v2 + engineered features (`area_per_room`, `log_area_sqm`, `floor_ratio`, `age_x_area`, `geo_cluster` from KMeans-64) + GeoKNN OOF features; best `xgb_deep` | 0.1985 | 282,393 | 0.8213 | `python3 run.py udi/xgboost_v3 --data v2`; artifact: `prediction_service/artifacts/udi/xgboost_v3/model.joblib`; train/val/test = 47,550/5,943/5,945 |
| 5 | `udi/xgboost_v4` | **REGRESSION**: v3 + smoothed `TargetEncoder(cv=5)` for city / neighborhood; best `xgb_regularized` | 0.2036 | 289,711 | 0.8189 | `python3 run.py udi/xgboost_v4 --data v2`; artifact: `prediction_service/artifacts/udi/xgboost_v4/model.joblib`; TE features overlap with native-cat + GeoKNN price signals → didn't help. v5 will branch off v3 instead |
| 6 | `udi/xgboost_v5` | **MAPE REGRESSION (MAE/RMSE/R² wins)**: v3 pipeline + Optuna 60-trial × 5-fold CV (TPESampler+MedianPruner; KMeans/KNN re-fit per fold to prevent leakage). Hit 1h timeout at 25/60 trials | 0.2015 | 278,688 | 0.8252 | `python3 run.py udi/xgboost_v5 --data v2`; artifact: `prediction_service/artifacts/udi/xgboost_v5/model.joblib`; CV picked depth-12 + lr=0.012 + 1209 estimators; CV MAPE 0.2061 → test MAPE 0.2015 (CV mildly pessimistic, healthy). MAPE up vs v3 by 0.003 but MAE/RMSE/R² all improved → optimised box minimises squared loss differently from MAPE on this slice |

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

## Run 3 Notes

- Candidate validation MAPE / `best_iteration` (early stopping rounds=150, n_estimators=4000, custom MAPE-real-scale eval_metric):
  - `xgb_balanced`     val_mape=0.1953  best_iter=918
  - `xgb_deep`         val_mape=0.1902  best_iter=1068  ← winner
  - `xgb_regularized`  val_mape=0.1927  best_iter=1505
  - `xgb_deep_reg`     val_mape=0.1912  best_iter=922
  - `xgb_mid_reg`      val_mape=0.1966  best_iter=950
- Final test metrics: MAPE 0.2023, MAE 288,396, RMSE 521,761, R² 0.8129, n=5,945.
- vs `udi/xgboost_v1` (test MAPE 0.2047, MAE 285,538, R² 0.8143): MAPE down 0.0024 (~1.2%), R² down a tick (-0.0014), MAE up ~3K. The MAPE win comes from MAPE-aware early stopping picking a different stop point on log-scale predictions; before, RMSE was minimized on `log1p(y)` so early stopping picked best RMSLE iter, not best MAPE iter.
- Top feature importances (raw column names — no `numeric__`/`categorical__` prefix now): `lat` 0.089, `rooms` 0.089, `is_residential_near_100m` 0.067, `city` 0.066, `log_dist_to_beach` 0.062. With native categorical on, `city` jumped from 0.030 (v1) to 0.066 (v2), confirming the partition-based split works better than ordinal-pseudo-numeric.
- Three engineering changes that landed:
  1. **Native categorical**: dropped the entire `ColumnTransformer`/`OrdinalEncoder`. `city`/`neighborhood`/`deal_nature` flow as `category` dtype directly into XGBRegressor with `enable_categorical=True`.
  2. **Categorical alignment helper** (`_align_categories`): `data_v2.split` calls `select_features` independently per slice, so `cat.categories` differ between train/val/test (silent correctness bug for native-cat). The helper canonicalises val/test categories to train's; unseen levels become NaN, which `enable_categorical=True` handles via default split direction.
  3. **MAPE-aware early stopping**: replaced `eval_metric="rmse"` (RMSE on `log1p(y)`) with a callable `mape_real_scale(y_true_log, y_pred_log) = MAPE(expm1(...))`. Critical gotcha: in xgboost 3.x the constructor's `early_stopping_rounds` defaults to `maximize=True` for *callable* `eval_metric` (no auto-direction inference), so we wire an explicit `EarlyStopping(rounds=150, maximize=False)` callback per fit. Without it, every candidate stops at `best_iter=0`.
- Dropped features (importance==0.0 in v1): `is_old`, `is_new`, `is_new_project`, `real_price_imputed`. Implemented defensively (only drop if present) since `real_price_imputed` is added by `data_v2.clean()` only when there are NaN target rows to fill.
- Surprises:
  - val<->test gap widened slightly (v1: 0.0110, v2: 0.0121). All five candidates show a similar ~0.012 drift, so this is shared distribution drift between val and test, not candidate-specific overfitting.
  - `xgb_slow_wide` (v1's winner) was deliberately removed; the new `xgb_deep` (max_depth=10, lr=0.03, min_child_weight=3, reg_lambda=2) lands 0.0035 better on val and 0.0024 better on test — depth=12 was indeed too aggressive.

## Run 4 Notes

- Candidate validation MAPE / `best_iteration`:
  - `xgb_balanced`     val_mape=0.1914  best_iter=878
  - `xgb_deep`         val_mape=0.1882  best_iter=1391  ← winner
  - `xgb_regularized`  val_mape=0.1916  best_iter=1329
  - `xgb_deep_reg`     val_mape=0.1910  best_iter=696
  - `xgb_mid_reg`      val_mape=0.1963  best_iter=729
- Final test metrics: MAPE 0.1985, MAE 282,393, RMSE 509,958, R² 0.8213, n=5,945.
- vs `udi/xgboost_v2` (test MAPE 0.2023, MAE 288,396, R² 0.8129): MAPE down 0.0038 (~1.9%), MAE down 6,003, R² up 0.0084. Still above the leaderboard pole-position (`moses/lightgbm_tuned` 0.1875) but now beats `moses/lightgbm_knn` (0.1907) → confirms the GeoKNN signal is the primary lever, exactly as scoped.
- val<->test gap shrunk to 0.0103 (vs v2's 0.0121, v1's 0.0110) — adding signal stabilised the val→test transfer rather than overfitting.
- Top feature importances: `knn5_dist_weighted_price` 0.191, `rooms` 0.119, `deal_nature` 0.047, `city` 0.045, `geo_cluster` 0.037. The single distance-weighted KNN price feature jumped to ~3× the next-most-important column. Engineered `log_area_sqm` lands at #11, `geo_cluster` at #5 — both surface as the plan predicted; raw `lat`/`lon` got pushed off the top-10 because their signal is now mostly absorbed by `geo_cluster` + KNN.
- Three pieces landed:
  1. **Engineered scalars**: `area_per_room`, `log_area_sqm`, `floor_ratio`, `age_x_area`. NaN-safe via `np.where(rooms>0, ..., NaN)` style guards (real `rooms==0` rows in the data would otherwise produce `inf`).
  2. **`geo_cluster`**: KMeans-64 on `train[(lat,lon) not NaN]`. Sentinel `-1` for missing-coords rows, full codebook `categories=list(range(-1, 64))` to keep splits identical across train/val/test/serving.
  3. **GeoKNN OOF**: 5-fold KFold OOF for train (no row sees its own neighbour set); single `KnnFeatureBuilder` fit on full train for val/test/serving. Mirrors `moses/lightgbm_knn` self-contained — implementation copied locally so `udi/` doesn't depend on `moses/`.
- KNN-feature NaN rate: train 24.8%, val 25.0% — driven by the 9.4% lat/lon-missing rows in the loader plus `area_sqm`-missing rows that knock out `pps`. No coverage drop between train and val (would've been the smoking gun if v3's val→test gap had widened).
- Surprise: `xgb_deep` `best_iter` jumped from 1068 (v2) to 1391 — added KNN+geo features keep useful gradient information further into training, so early stopping is more patient. No sign of overfitting (val<->test gap shrank).
- Minor noise: `np.nanmean`/`np.nanmedian` emit "All-NaN slice" warnings on KNN queries where every neighbour's `pps` is NaN (rare). The result is correctly NaN for the feature, which XGB's native missing handling consumes — no functional issue.

## Run 5 Notes (REGRESSION)

- Candidate validation MAPE / `best_iteration`:
  - `xgb_balanced`     val_mape=0.1931  best_iter=756
  - `xgb_deep`         val_mape=0.1932  best_iter=681
  - `xgb_regularized`  val_mape=0.1925  best_iter=1551  ← winner (per val)
  - `xgb_deep_reg`     val_mape=0.1941  best_iter=637
  - `xgb_mid_reg`      val_mape=0.1953  best_iter=1198
- Final test metrics: MAPE 0.2036, MAE 289,711, RMSE 513,382, R² 0.8189, n=5,945.
- **Verdict — REGRESSION vs v3**: test MAPE up 0.0051 (v3 0.1985 → v4 0.2036), MAE up 7,318, R² down 0.0024. Val MAPE also up (v3 0.1882 → v4 0.1925). Both sides got worse — TE didn't generalise, and even on val it lost to v3.
- TE leakage spot-check (computed inline during training):
  - `city`: `|mean log1p(y) − te_full|` over 60 keys = 0.0044 → smoothing-only delta, no leakage.
  - `neighborhood`: same metric over 114 keys = 0.0351 → bigger because of higher-cardinality smoothing pulling small groups toward global mean. Still consistent with `smooth="auto"` behaviour, no leakage.
- Top feature importances: `knn5_dist_weighted_price` 0.189, `rooms` 0.112, `city` 0.048, `knn10_median_price_per_sqm` 0.047, `deal_nature` 0.046. `te_neighborhood_log_price` lands at #11 (0.014); `te_city_log_price` is even lower (not in top-12). The booster prefers native `city` and the KNN price features over TE.
- Why it regressed: GeoKNN price features (`knn5_dist_weighted_price` etc.) already encode the per-(city, neighborhood)-region price level via spatial smoothing — TE on `log_price` adds essentially the same signal at coarser granularity, so the model gets no new information but more flexibility to overfit. The candidate winner shifted from `xgb_deep` (depth-10) to `xgb_regularized` (depth-8, lr=0.03, reg_lambda=5) — heavier regularisation needed for the redundant TE features, and even with that the model lost.
- Action: keep file as documented regression; **v5 (Optuna sweep) is built on top of v3, not v4**, since v4 failed criterion (1) of the validation strategy.

## Run 6 Notes (MAPE REGRESSION; MAE/RMSE/R² improved)

- Optuna sweep: 60 trials requested, **25 completed**, 0 pruned. Hit `timeout=3600s` (1h) before reaching 60 — each trial = 5-fold CV with feature engineering re-fit per fold (KMeans, GeoKNN BallTree, categorical alignment all built on the in-fold training data only), so a trial costs ~2-3 min on this dataset.
- Best CV MAPE: **0.2061** (mean across 5 folds: [0.2031, 0.1989, 0.2059, 0.2133, 0.2092]).
- Best params: `max_depth=12, learning_rate=0.0121, min_child_weight=4, subsample=0.754, colsample_bytree=0.692, reg_lambda=0.482, reg_alpha=0.0348, gamma=0.00106`. Final fit: `n_estimators=1209` (median of best_iters per fold: [1457, 1093, 1139, 1499, 1209]) on full train+val (53,493 rows × 80 feats).
- Final test metrics: MAPE 0.2015, MAE 278,688, RMSE 504,365, R² 0.8252, n=5,945.
- **vs `udi/xgboost_v3`** (MAPE 0.1985, MAE 282,393, RMSE 509,958, R² 0.8213): MAPE **up 0.0030 (~1.5%)** → fails plan criterion (1) (which allowed only ~0.001 noise band). MAE down 3,705, RMSE down 5,593, R² up 0.0039. The squared-error-optimal box from Optuna gets bigger errors *less often* (lower RMSE) but its smaller errors hurt MAPE more on the long tail of small-priced rows. CV's `mape_real_scale` eval-metric *was* used for early stopping per fold, but the trial-level objective is mean-MAPE which still optimises the average — it's the trial-→-test transfer that's the issue, not the metric.
- **CV → test gap (healthy direction)**: CV MAPE 0.2061 > Test MAPE 0.2015 — the held-out test slice is slightly easier than the 5-fold CV mean. v3's val→test gap was +0.0103 (val 0.1882 → test 0.1985); v5 has no single-val gap to compare, but CV→test is -0.0046, consistent with CV being a more pessimistic estimator than a single 80/10 val split.
- Top feature importances: `knn5_dist_weighted_price` 0.215, `rooms` 0.113, `deal_nature` 0.046, `city` 0.044, `geo_cluster` 0.034. Order ~unchanged from v3, but `knn5_dist_weighted_price` weight grew from 0.191 → 0.215, confirming the deeper trees in v5 (max_depth=12 vs v3's 10) extract more from the dominant signal.
- Why best_params landed at `max_depth=12` despite v1 showing depth-12 (`xgb_slow_wide`) was the overfitter: with the GeoKNN+geo_cluster signal added, the booster has enough new partitionable dimensions that depth-12 is no longer overcommitted (v3 already proved depth-10 wins; v5's marginally-better RMSE/MAE shows depth-12 captures slightly more without exploding val/CV variance). The MAPE regression is consistent with depth-12 over-confidently shrinking the predictions on small-price tails.
- Why only 25/60 trials: each trial fits 5 boosters with `n_estimators=5000` and early-stopping=150, plus per-fold KMeans + KNN BallTree builds. Optuna is single-process here; XGB is multi-threaded internally. To fit the full 60 in budget, drop `n_estimators_tune` to 3000 or shorten `early_stopping_rounds` to 100 (or run on a beefier box). The 25 trials still cover all 8 hyperparams via TPE — the search did converge enough to pick a reasonable region.
- 8 of the top-10 trials picked `max_depth ∈ {10, 12}` and 7 picked `learning_rate ∈ [0.01, 0.022]`, confirming the deep + low-LR regime that already won in v1/v2/v3. The CV's MedianPruner saw no pruning trigger because the first 10 startup trials defined the baseline mean and subsequent trials were close enough to escape pruning thresholds.
- **Verdict**: v3 stays the udi/ champion at MAPE 0.1985. v5 is a documented regression by the plan's primary metric (MAPE) but a Pareto-improvement on MAE/RMSE/R² — useful if the downstream consumer cares more about absolute-rial errors than relative-percent errors. Plan target (MAPE < 0.18 to beat `moses/lightgbm_tuned` 0.1875) was **not** reached by any XGBoost variant in this ladder; the gap between v3 (0.1985) and 0.18 needed something v3/v4/v5 didn't provide — most likely temporal price-index features or stacking, which were explicitly out-of-scope for this plan.
