"""Smoke test: every available model returns a finite price for the default
playground payload via the real serving path (serve._predict_one).

    cd prediction_service && python scripts/check_all_models.py

Exit code 0 iff all models return a finite, positive price.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import serve  # noqa: E402

FEATURES = {
    "area_sqm": 100, "rooms": 4, "floor": 3, "building_floors": 8,
    "year_built": 2010, "property_age": 15, "year": 2024, "month": 6,
    "quarter": 2, "log_area_sqm": 4.605,
}


def main() -> int:
    models = [m.id for m in serve._list_available_models()]
    failures = []
    for mid in sorted(models):
        try:
            price = math.exp(serve._predict_one(mid, FEATURES))
            assert math.isfinite(price) and price > 0, f"non-finite price {price}"
            print(f"[OK ] {mid:24s} -> {price:,.0f}")
        except Exception as exc:  # noqa: BLE001 — report, don't abort
            failures.append((mid, exc))
            print(f"[ERR] {mid:24s} -> {type(exc).__name__}: {exc}")
    print(f"\n{len(models) - len(failures)}/{len(models)} OK")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
