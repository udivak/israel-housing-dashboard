# CV Results — dashboard model card

Single source of truth for the dashboard's "model uncertainty" + "cross-loader ranking" panels.
Reads three JSON artifacts (each populated by the harness named below the table); this `.md`
itself is the fill-in template and lays out the exact section structure the dashboard renders.

> **Status: SCAFFOLD LANDED, NUMBERS PENDING HARNESS RUNS.** Run the three harnesses in any
> order (they're independent), then fill the `TBD` cells from the JSON outputs. Each harness
> has a `--fresh` flag (or just delete its JSON) if you need a clean restart.

---

## 1 — Per-model 5-seed CV (`mape_mean ± mape_std`)

Honest noise-band uncertainty per model. Replaces the single-seed leaderboard rows with the
mean/std over seeds {42, 43, 44, 45, 46}. Each model is CVed on its **native loader**
(moses on v1, udi on v2) — see Decision log in
[`/Users/udivak/.cursor/plans/cv-and-align-udi-models_503d13c0.plan.md`](file:///Users/udivak/.cursor/plans/cv-and-align-udi-models_503d13c0.plan.md)
for why we don't share a loader.

| Model | mape_mean | mape_std | mape_min | mape_max | mae_mean | r2_mean | n_seeds | source |
|-------|-----------|----------|----------|----------|----------|---------|---------|--------|
| `moses/stacked_v1` | TBD | TBD | TBD | TBD | TBD | TBD | 5 | `artifacts/cv_validate.json` |
| `udi/xgboost_v3`   | TBD | TBD | TBD | TBD | TBD | TBD | 5 | `artifacts/cv_validate_udi.json` |
| `udi/blend_v1`     | TBD | TBD | TBD | TBD | TBD | TBD | 5 | `artifacts/cv_validate_udi.json` |

**Harness commands**:

```bash
# moses (already exists; re-run if cv_validate.json is stale)
python3 scripts/cv_validate.py

# udi (Stage B.2 of cv-and-align plan; checkpoints per (model, seed))
python3 scripts/cv_validate_udi.py
```

**How the dashboard reads this**: each model gets a `mape ± std` line + a small sparkline
of the 5 per-seed values from `runs[].mape`. Seeds where the model exceeds `mean + 2σ` get
flagged in red as "anomalous fold" so reviewers can spot CV instability at a glance.

---

## 2 — Paired noise-band decision: `udi/blend_v1` vs `udi/xgboost_v3`

The blend contains the booster internally, so a **paired** test on the same seeds is the
honest comparison (independent-std would double-count noise).

| seed | `blend_v1` MAPE | `xgboost_v3` MAPE | diff (`blend − xgb`) |
|------|-----------------|-------------------|----------------------|
| 42   | TBD | TBD | TBD |
| 43   | TBD | TBD | TBD |
| 44   | TBD | TBD | TBD |
| 45   | TBD | TBD | TBD |
| 46   | TBD | TBD | TBD |

**`mean(diff) = TBD`   `std(diff) = TBD`**

**Decision rule** (Stage B.3 of plan):

- `mean(diff) < 0` AND `|mean(diff)| > std(diff)` → blend's lift survives → **keep `blend_v1`**.
- `mean(diff) >= 0` AND `mean(diff) > std(diff)` → xgboost wins outside the band → **ship `xgboost_v3`**.
- Otherwise (diff inside the band) → **ship `xgboost_v3`** (one fewer moving part).

**Verdict (fill in after CV)**: `TBD — recommend …`

Source: `artifacts/cv_validate_udi.json` → `paired_diff` block.

---

## 3 — Cross-loader canonical ranking (apples-to-apples)

The leaderboard scores moses (n=5,625, CPI-adjusted target) against udi (n=5,945, **nominal**
target because of the `data_v2.clean()` `real_price` fallback bug — see callout at top of
`common/data_v2.py`). This block fixes both: same rows + same target.

- Canonical slice: deterministic 10% sample of `df_v1._id ∩ df_v2._id` via
  `numpy.random.default_rng(999)` (bumps to 20% if 10% < 1,000 rows).
- Per model: train on its native-loader-`not-canonical` rows (80/20 train/val, no test);
  predict on canonical rows of native df.
- Score: udi predictions are CPI-converted via per-row `cpi_factor = df_v1.real_price / df_v1.price`
  before scoring against `df_v1.real_price` ground truth. `mape_unconverted` exposes the
  loader bug's impact when the conversion is skipped.

| rank | model | `mape_real` | `mape_unconverted` | `mae_real` | `rmse_real` | `r2_real` | n_canonical |
|------|-------|-------------|--------------------|------------|-------------|-----------|-------------|
| TBD  | `moses/stacked_v1` | TBD | TBD (no conversion needed) | TBD | TBD | TBD | TBD |
| TBD  | `udi/xgboost_v3`   | TBD | TBD                        | TBD | TBD | TBD | TBD |
| TBD  | `udi/blend_v1`     | TBD | TBD                        | TBD | TBD | TBD | TBD |

**Harness command**:

```bash
python3 scripts/cross_eval.py
```

**Outputs**:

- `artifacts/cross_eval.json` — ranking + per-model `mape_real` / `mape_unconverted` / etc.
- `artifacts/cross_eval_residuals.parquet` — per-(`_id`, model) residuals
  (`y_real`, `pred_real`, `pred_native_scale`, `cpi_factor`, `abs_pct_err`) so the dashboard
  can render where-each-model-wins maps without retraining.

**Sanity checks the harness prints**:

- `shared_id_coverage` — warns if `< 80%` on either loader (otherwise canonical slice may be
  unrepresentative).
- Year distribution of canonical slice — Mongo cache bias toward 2024-2025 would understate
  CPI conversion impact; the harness prints the year histogram so reviewers can spot it.
- `cpi_factor` quality — drops rows where `df_v1.price <= 0` or `real_price/price` is
  NaN/inf; warns if > 2% of canonical rows are dropped.

---

## 4 — Recommended serving model

> Fill in after Sections 1-3 are populated. Template:
>
> Ship **`<model>`** because (a) canonical `mape_real` = `<x>` < competitor's `<y>`,
> AND (b) per-seed `mape_std` = `<s>` envelope does not overlap the competitor's `mean ± std`,
> AND (c) `<rationale>`. Promote to `udi/blend_v2` (xgboost_v3 + nn_v3b cross-person blend)
> only after the follow-up plan lands.

**Recommendation**: TBD

**Rationale**: TBD (cite both the per-model CV `std` envelopes from §1 and the canonical
`mape_real` ranking from §3. If the paired diff in §2 says "ship xgboost", surface that
explicitly here too.)

---

## Appendix — Why this doc exists separate from `leaderboard.md`

`leaderboard.md` is single-seed point estimates appended by `run.py`. It can't show
`mape ± std` because each row is one (submission, run) snapshot. This doc consumes
`cv_validate*.json` + `cross_eval.json` directly so the dashboard sees the noise band, the
paired decision, and the cross-loader ranking — all three pieces the leaderboard structurally
can't carry.

The harnesses (`cv_validate_udi.py`, `cross_eval.py`) **deliberately bypass**
`leaderboard.add_result` so the leaderboard isn't polluted with 10 near-duplicate CV rows
or 3 cross-eval re-train rows.
