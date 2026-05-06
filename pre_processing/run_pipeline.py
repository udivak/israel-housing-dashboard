import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def _is_truthy(val: str | None) -> bool:
    if val is None:
        return False
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}


def _run_step(name: str, argv: list[str]) -> None:
    print(f"\n{'='*60}\n▶ {name}\n{'='*60}")
    subprocess.run(argv, cwd=str(ROOT), check=True)


def main() -> int:
    skip_profiler = _is_truthy(os.getenv("PIPELINE_SKIP_PROFILER"))
    skip_geom = _is_truthy(os.getenv("PIPELINE_SKIP_GEOM"))
    skip_normalize = _is_truthy(os.getenv("PIPELINE_SKIP_NORMALIZE"))
    skip_osm = _is_truthy(os.getenv("PIPELINE_SKIP_OSM"))
    skip_temporal = _is_truthy(os.getenv("PIPELINE_SKIP_TEMPORAL"))
    skip_load = _is_truthy(os.getenv("PIPELINE_SKIP_LOAD_TO_MONGO"))

    python = sys.executable

    if not skip_profiler:
        _run_step("Profiling raw records", [python, "-m", "pre_processing.pipelines.data_profiler"])

    if not skip_geom:
        _run_step("Backfill geometry from parcels", [python, "-m", "pre_processing.pipelines.get_geom_by_block"])

    if not skip_normalize:
        _run_step("Normalize raw_records -> normalized_records", [python, str(ROOT / "normalize_data.py")])

    if not skip_osm:
        _run_step("OSM feature engineering -> CSV", [python, "-m", "pre_processing.pipelines.feature_pipeline"])

    if not skip_temporal:
        _run_step("Temporal+macro features -> XLSX", [python, "-m", "pre_processing.pipelines.temporal_macro_feature_pipeline"])

    if not skip_load:
        _run_step("Load enriched features to Mongo", [python, "-m", "pre_processing.pipelines.load_to_mongo"])

    print("\n✅ Pipeline completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

