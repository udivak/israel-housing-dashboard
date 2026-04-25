"""
🎮 Playground — לחקור את הדאטה שכבה-אחרי-שכבה.

פתח ב-VS Code / PyCharm / Jupyter. לחץ "Run Cell" מעל כל `# %%` כדי להריץ תא בודד.
אפשר לשנות כל דבר — זה הקובץ האישי שלך לניסיונות.

זרימה:
    1. Load temporal         ← העסקאות + macro + CBS
    2. Load OSM              ← פיצ'רים מרחביים
    3. Join layers           ← שני הקבצים יחד
    4. Clean                 ← סינון outliers
    5. Select features       ← מה באמת נכנס למודל
    6. Split                 ← train/val/test כרונולוגי
    7. Explore distributions
    8. Correlations
"""

# %% Imports
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from common import data


# %% 1. Load temporal_features.xlsx (השכבה הראשית)
temporal = data.load_temporal()
print(f"shape: {temporal.shape}")
print(f"columns: {list(temporal.columns)}")
temporal.head()


# %% בדוק null rates
temporal.isna().mean().sort_values(ascending=False).head(20)


# %% התפלגות ה-target (real_price)
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
temporal["real_price"].dropna().hist(bins=100, ax=axes[0])
axes[0].set_title("real_price")
np.log1p(temporal["real_price"].dropna()).hist(bins=100, ax=axes[1])
axes[1].set_title("log(1 + real_price)")
plt.tight_layout(); plt.show()


# %% 2. Load features_osm.csv
osm = data.load_osm()
print(f"shape: {osm.shape}")
print(f"columns: {list(osm.columns)[:10]}...")
osm.head()


# %% 3. Join — כמה רשומות מתמזגות בהצלחה?
merged = data.join_layers(temporal, osm)
osm_coverage = merged[osm.columns.drop("_id")[0]].notna().mean()
print(f"joined rows: {len(merged):,}")
print(f"OSM coverage: {osm_coverage:.1%}")


# %% 4. Clean — לראות כמה נופל בכל שלב
print(f"before clean:  {len(merged):,}")
cleaned = data.clean(merged)
print(f"after clean:   {len(cleaned):,}")
print(f"date range:    {cleaned['transaction_date'].min()} → {cleaned['transaction_date'].max()}")


# %% 5. Select features — מה נכנס למודל
X_sample = data.select_features(cleaned.head(1000))
print(f"{X_sample.shape[1]} features:")
print(list(X_sample.columns))


# %% 6. Split כרונולוגי
X_train, y_train, X_val, y_val, X_test, y_test = data.split(cleaned)
print(f"train: {len(X_train):>7,}   ({y_train.mean():>12,.0f} mean real_price)")
print(f"val:   {len(X_val):>7,}   ({y_val.mean():>12,.0f})")
print(f"test:  {len(X_test):>7,}   ({y_test.mean():>12,.0f})")


# %% 7. התפלגות מחירים לפי שנה
cleaned.groupby(cleaned["transaction_date"].dt.year)["real_price"].median().plot(kind="bar")
plt.title("median real_price by year")
plt.tight_layout(); plt.show()


# %% התפלגות לפי עיר (top 15)
top_cities = cleaned["city"].value_counts().head(15).index
cleaned[cleaned["city"].isin(top_cities)].boxplot(
    column="real_price", by="city", rot=45, figsize=(14, 5)
)
plt.yscale("log")
plt.tight_layout(); plt.show()


# %% 8. Correlations עם ה-target (numeric only)
num_cols = X_train.select_dtypes(include="number").columns
corr = X_train[num_cols].assign(y=y_train).corr()["y"].drop("y").sort_values(key=abs, ascending=False)
print("Top 20 features by |correlation with real_price|:")
print(corr.head(20))


# %% Scatter: area_sqm vs real_price
plt.figure(figsize=(8, 5))
plt.scatter(X_train["area_sqm"], y_train, alpha=0.1, s=5)
plt.xlabel("area_sqm"); plt.ylabel("real_price")
plt.title("area_sqm vs real_price")
plt.tight_layout(); plt.show()


# %% Missing rates של כל הפיצ'רים ב-X
missing = X_train.isna().mean().sort_values(ascending=False)
print(missing[missing > 0])
