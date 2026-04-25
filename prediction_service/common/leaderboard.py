"""
ניהול leaderboard — קובץ JSON יחיד + רינדור ל-markdown.

run.py הוא היחיד שקורא ל-add_result().
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEADERBOARD_JSON = ROOT / "leaderboard.json"
LEADERBOARD_MD = ROOT / "leaderboard.md"

PRIMARY_METRIC = "mape"  # המטריקה שעל-פיה ממיינים (נמוך = טוב)


def _load() -> dict:
    if LEADERBOARD_JSON.exists():
        return json.loads(LEADERBOARD_JSON.read_text())
    return {"runs": []}


def _save(data: dict) -> None:
    LEADERBOARD_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def add_result(submission: str, metrics: dict, metadata: dict) -> None:
    """submission = 'moses/lightgbm_v1', metrics = dict מ-compute_metrics."""
    data = _load()
    data["runs"].append({
        "submission": submission,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "metrics": metrics,
        "metadata": metadata,
    })
    _save(data)
    regenerate_md()


def regenerate_md() -> None:
    data = _load()
    runs = sorted(data["runs"], key=lambda r: r["metrics"].get(PRIMARY_METRIC, float("inf")))

    lines = ["# Leaderboard\n", f"_ממוין לפי {PRIMARY_METRIC} (נמוך = טוב)_\n"]

    lines.append("\n## Overall\n")
    lines.append("| # | Submission | MAPE | MAE | RMSE | R² | N | Date |")
    lines.append("|---|------------|------|-----|------|-----|---|------|")
    for i, r in enumerate(runs, 1):
        m = r["metrics"]
        lines.append(
            f"| {i} | `{r['submission']}` | {m.get('mape', float('nan')):.4f} | "
            f"{m.get('mae', float('nan')):,.0f} | {m.get('rmse', float('nan')):,.0f} | "
            f"{m.get('r2', float('nan')):.3f} | {m.get('n', 0):,} | {r['timestamp'][:10]} |"
        )

    # הטוב ביותר פר משתתף
    best_per = {}
    for r in runs:
        person = r["submission"].split("/")[0]
        if person not in best_per:
            best_per[person] = r

    lines.append("\n## Best per Person\n")
    lines.append("| Person | Best Submission | MAPE |")
    lines.append("|--------|-----------------|------|")
    for person, r in best_per.items():
        lines.append(f"| {person} | `{r['submission']}` | {r['metrics'].get('mape', float('nan')):.4f} |")

    LEADERBOARD_MD.write_text("\n".join(lines) + "\n")


def show() -> None:
    """הדפסה מהירה לקונסול."""
    data = _load()
    runs = sorted(data["runs"], key=lambda r: r["metrics"].get(PRIMARY_METRIC, float("inf")))
    if not runs:
        print("(leaderboard ריק)")
        return
    for i, r in enumerate(runs, 1):
        m = r["metrics"]
        print(f"{i:2}. {r['submission']:<35} "
              f"mape={m.get('mape', float('nan')):.4f}  "
              f"mae={m.get('mae', float('nan')):>10,.0f}  "
              f"r2={m.get('r2', float('nan')):.3f}  "
              f"n={m.get('n', 0):,}")
