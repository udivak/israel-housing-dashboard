import os
import math
import logging
from typing import Dict, Optional, Any, List
from dotenv import load_dotenv

import geopandas as gpd
import pandas as pd
from pymongo import MongoClient, UpdateOne
from shapely.geometry import Point
from shapely.ops import nearest_points
from pyproj import Transformer
from tqdm import tqdm
import pandas as pd


# =========================================================
# CONFIG
# =========================================================

load_dotenv()

MONGO_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("MONGODB_DB_NAME", "your_db")
RAW_COLLECTION = os.getenv("MONGODB_RAW_COLLECTION", "raw_records")
FEATURES_COLLECTION = os.getenv("MONGODB_FEATURES_COLLECTION", "features_osm")

DATA_DIR = os.getenv("OSM_DATA_DIR", "/Users/moses/Desktop/israel-and-palestine-260310-free.shp")

BATCH_SIZE = int(os.getenv("FEATURE_BATCH_SIZE", "500"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

TARGET_CRS = "EPSG:3857"
SOURCE_CRS = "EPSG:4326"


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


# =========================================================
# CONSTANTS / TAXONOMY
# =========================================================

MAIN_ROADS = ["motorway", "trunk", "primary", "motorway_link", "trunk_link", "primary_link"]
SECONDARY_ROADS = ["secondary", "tertiary", "secondary_link", "tertiary_link"]
LOCAL_ROADS = ["residential", "service", "living_street", "unclassified"]

GREEN_LANDUSE = ["park", "forest", "meadow", "nature_reserve", "grass", "recreation_ground", "scrub"]
INDUSTRIAL_LANDUSE = ["industrial", "quarry", "military"]
COMMERCIAL_LANDUSE = ["commercial", "retail"]
RESIDENTIAL_LANDUSE = ["residential"]

PARK_CLASSES = ["park"]
WATER_CLASSES = ["water", "reservoir", "riverbank", "wetland"]
BEACH_CLASSES = ["beach"]
RIVER_CLASSES = ["river", "stream", "canal"]

RESTAURANT_CLASSES = ["restaurant", "cafe", "fast_food"]
SHOP_CLASSES = ["supermarket", "convenience", "mall"]
SCHOOL_CLASSES = ["school"]
KINDERGARTEN_CLASSES = ["kindergarten"]
PLAYGROUND_CLASSES = ["playground"]
PHARMACY_CLASSES = ["pharmacy"]
PUBLIC_BUILDING_CLASSES = ["public_building"]
ATTRACTION_CLASSES = ["attraction", "viewpoint", "archaeological", "memorial"]

TRANSPORT_BUS_STOP = ["bus_stop"]
TRANSPORT_RAIL_STATION = ["railway_station", "tram_stop"]
TRANSPORT_BUS_STATION = ["bus_station"]

TRAFFIC_PARKING = ["parking", "parking_underground", "parking_multistorey", "parking_bicycle"]
TRAFFIC_SIGNALS = ["traffic_signals"]
FUEL_CLASSES = ["fuel"]

POFW_JEWISH = ["jewish"]

BUILDING_RESIDENTIAL_TYPES = ["house", "apartments", "detached", "residential", "semidetached_house", "terrace"]
BUILDING_PUBLIC_TYPES = ["school", "kindergarten", "university", "office", "commercial", "retail"]


# =========================================================
# VALIDATION
# =========================================================

if not MONGO_URI:
    raise ValueError("Missing MONGODB_URI environment variable")

if not os.path.isdir(DATA_DIR):
    raise ValueError(f"OSM_DATA_DIR does not exist or is not a directory: {DATA_DIR}")


# =========================================================
# MONGO
# =========================================================

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
raw_col = db[RAW_COLLECTION]
features_col = db[FEATURES_COLLECTION]


# =========================================================
# GEO HELPERS
# =========================================================

transformer = Transformer.from_crs(SOURCE_CRS, TARGET_CRS, always_xy=True)


GRID_SIZE = 20  # מטרים (אפשר לשנות ל-50 / 200)


from pyproj import Transformer

transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

def to_3857(point):
    x, y = transformer.transform(point.x, point.y)
    return Point(x, y)

def get_point(doc):
    coords = doc.get("geometry", {}).get("coordinates")
    if not coords:
        return None
    return Point(coords)

def grid_key(point):
    x = int(point.x // GRID_SIZE)
    y = int(point.y // GRID_SIZE)
    return f"{x}_{y}"


feature_cache = {}


def safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def safe_log1p(x: float) -> float:
    return math.log1p(max(0.0, x))


def point_from_doc(doc: Dict[str, Any]) -> Optional[Point]:
    geometry = doc.get("geometry")
    if not geometry:
        return None

    coords = geometry.get("coordinates")
    if not coords or len(coords) != 2:
        return None

    lon, lat = coords[0], coords[1]
    if lon is None or lat is None:
        return None

    try:
        x, y = transformer.transform(lon, lat)
        return Point(x, y)
    except Exception:
        return None


def load_layer(filename: str) -> gpd.GeoDataFrame:
    path = os.path.join(DATA_DIR, filename)
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        gdf = gdf.set_crs(SOURCE_CRS)
    gdf = gdf.to_crs(TARGET_CRS)
    gdf = gdf[gdf.geometry.notnull()].copy()
    return gdf


def filter_fclass(gdf: gpd.GeoDataFrame, values: List[str]) -> gpd.GeoDataFrame:
    if "fclass" not in gdf.columns:
        return gdf.iloc[0:0].copy()
    return gdf[gdf["fclass"].isin(values)].copy()


def filter_type(gdf: gpd.GeoDataFrame, values: List[str]) -> gpd.GeoDataFrame:
    if "type" not in gdf.columns:
        return gdf.iloc[0:0].copy()
    return gdf[gdf["type"].isin(values)].copy()


def prepare_gdf(gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
    gdf = gdf[gdf.geometry.notnull()].copy()
    return {
        "gdf": gdf,
        "sindex": gdf.sindex if len(gdf) else None,
        "union": gdf.geometry.union_all() if len(gdf) else None,
    }


def subset_by_buffer(prepared: Dict[str, Any], point: Point, radius: float) -> gpd.GeoDataFrame:
    if prepared["sindex"] is None or prepared["gdf"].empty:
        return prepared["gdf"].iloc[0:0].copy()

    bounds = point.buffer(radius).bounds
    idx = list(prepared["sindex"].intersection(bounds))
    if not idx:
        return prepared["gdf"].iloc[0:0].copy()

    return prepared["gdf"].iloc[idx]


def distance_to(point: Point, prepared: Dict[str, Any]) -> Optional[float]:
    if prepared["union"] is None:
        return None
    try:
        nearest = nearest_points(point, prepared["union"])[1]
        return float(point.distance(nearest))
    except Exception:
        return None


def count_nearby(point: Point, prepared: Dict[str, Any], radius: float) -> int:
    subset = subset_by_buffer(prepared, point, radius)
    if subset.empty:
        return 0
    return int((subset.geometry.distance(point) < radius).sum())


def total_length_within(point: Point, prepared: Dict[str, Any], radius: float) -> float:
    subset = subset_by_buffer(prepared, point, radius)
    if subset.empty:
        return 0.0

    buf = point.buffer(radius)
    total = 0.0
    for geom in subset.geometry:
        inter = geom.intersection(buf)
        if not inter.is_empty:
            total += inter.length
    return float(total)


def total_area_within(point: Point, prepared: Dict[str, Any], radius: float) -> float:
    subset = subset_by_buffer(prepared, point, radius)
    if subset.empty:
        return 0.0

    buf = point.buffer(radius)
    total = 0.0
    for geom in subset.geometry:
        inter = geom.intersection(buf)
        if not inter.is_empty:
            total += inter.area
    return float(total)


def area_ratio_within(point: Point, prepared: Dict[str, Any], radius: float) -> float:
    buf = point.buffer(radius)
    area = total_area_within(point, prepared, radius)
    return safe_div(area, buf.area)


def intersects_buffer(point: Point, prepared: Dict[str, Any], radius: float) -> int:
    subset = subset_by_buffer(prepared, point, radius)
    if subset.empty:
        return 0
    buf = point.buffer(radius)
    return int(subset.intersects(buf).any())


def count_unique_values_nearby(
    point: Point,
    prepared: Dict[str, Any],
    radius: float,
    column: str
) -> int:
    subset = subset_by_buffer(prepared, point, radius)
    if subset.empty or column not in subset.columns:
        return 0
    subset = subset[subset.geometry.distance(point) < radius]
    return int(subset[column].dropna().nunique())


# =========================================================
# LOAD BASE LAYERS
# =========================================================

logger.info("Loading OSM layers...")

layers = {
    "roads": load_layer("gis_osm_roads_free_1.shp"),
    "water": load_layer("gis_osm_water_a_free_1.shp"),
    "natural_a": load_layer("gis_osm_natural_a_free_1.shp"),
    "natural": load_layer("gis_osm_natural_free_1.shp"),
    "pois": load_layer("gis_osm_pois_free_1.shp"),
    "pois_a": load_layer("gis_osm_pois_a_free_1.shp"),
    "buildings": load_layer("gis_osm_buildings_a_free_1.shp"),
    "transport": load_layer("gis_osm_transport_free_1.shp"),
    "transport_a": load_layer("gis_osm_transport_a_free_1.shp"),
    "landuse": load_layer("gis_osm_landuse_a_free_1.shp"),
    "railways": load_layer("gis_osm_railways_free_1.shp"),
    "traffic": load_layer("gis_osm_traffic_free_1.shp"),
    "traffic_a": load_layer("gis_osm_traffic_a_free_1.shp"),
    "waterways": load_layer("gis_osm_waterways_free_1.shp"),
    "pofw": load_layer("gis_osm_pofw_free_1.shp"),
    "pofw_a": load_layer("gis_osm_pofw_a_free_1.shp"),
    "places": load_layer("gis_osm_places_free_1.shp"),
    "places_a": load_layer("gis_osm_places_a_free_1.shp"),
}

logger.info("Loaded all layers.")


# =========================================================
# PREPARE FILTERED LAYERS ONCE
# =========================================================

logger.info("Preparing filtered layers...")

prepared = {
    # base
    "roads_all": prepare_gdf(layers["roads"]),
    "water_all": prepare_gdf(layers["water"]),
    "natural_a_all": prepare_gdf(layers["natural_a"]),
    "natural_all": prepare_gdf(layers["natural"]),
    "pois_all": prepare_gdf(layers["pois"]),
    "pois_a_all": prepare_gdf(layers["pois_a"]),
    "buildings_all": prepare_gdf(layers["buildings"]),
    "transport_all": prepare_gdf(layers["transport"]),
    "transport_a_all": prepare_gdf(layers["transport_a"]),
    "landuse_all": prepare_gdf(layers["landuse"]),
    "railways_all": prepare_gdf(layers["railways"]),
    "traffic_all": prepare_gdf(layers["traffic"]),
    "traffic_a_all": prepare_gdf(layers["traffic_a"]),
    "waterways_all": prepare_gdf(layers["waterways"]),
    "pofw_all": prepare_gdf(layers["pofw"]),
    "pofw_a_all": prepare_gdf(layers["pofw_a"]),
    "places_all": prepare_gdf(layers["places"]),
    "places_a_all": prepare_gdf(layers["places_a"]),

    # roads
    "roads_main": prepare_gdf(filter_fclass(layers["roads"], MAIN_ROADS)),
    "roads_secondary": prepare_gdf(filter_fclass(layers["roads"], SECONDARY_ROADS)),
    "roads_local": prepare_gdf(filter_fclass(layers["roads"], LOCAL_ROADS)),

    # nature / water
    "beaches": prepare_gdf(filter_fclass(layers["natural_a"], BEACH_CLASSES)),
    "water_polygons": prepare_gdf(filter_fclass(layers["water"], WATER_CLASSES)),
    "rivers_streams": prepare_gdf(filter_fclass(layers["waterways"], RIVER_CLASSES)),

    # POI
    "parks": prepare_gdf(filter_fclass(layers["pois_a"], PARK_CLASSES)),
    "restaurants": prepare_gdf(filter_fclass(layers["pois"], RESTAURANT_CLASSES)),
    "shops": prepare_gdf(filter_fclass(layers["pois"], SHOP_CLASSES)),
    "schools": prepare_gdf(filter_fclass(layers["pois"], SCHOOL_CLASSES)),
    "kindergartens": prepare_gdf(filter_fclass(layers["pois"], KINDERGARTEN_CLASSES)),
    "playgrounds": prepare_gdf(filter_fclass(layers["pois"], PLAYGROUND_CLASSES)),
    "pharmacies": prepare_gdf(filter_fclass(layers["pois"], PHARMACY_CLASSES)),
    "public_buildings": prepare_gdf(filter_fclass(layers["pois"], PUBLIC_BUILDING_CLASSES)),
    "attractions": prepare_gdf(filter_fclass(layers["pois"], ATTRACTION_CLASSES)),

    # transport
    "bus_stops": prepare_gdf(filter_fclass(layers["transport"], TRANSPORT_BUS_STOP)),
    "rail_stations": prepare_gdf(filter_fclass(layers["transport"], TRANSPORT_RAIL_STATION)),
    "bus_stations": prepare_gdf(filter_fclass(layers["transport_a"], TRANSPORT_BUS_STATION)),

    # landuse
    "green_landuse": prepare_gdf(filter_fclass(layers["landuse"], GREEN_LANDUSE)),
    "industrial_landuse": prepare_gdf(filter_fclass(layers["landuse"], INDUSTRIAL_LANDUSE)),
    "commercial_landuse": prepare_gdf(filter_fclass(layers["landuse"], COMMERCIAL_LANDUSE)),
    "residential_landuse": prepare_gdf(filter_fclass(layers["landuse"], RESIDENTIAL_LANDUSE)),

    # traffic
    "parking_points": prepare_gdf(filter_fclass(layers["traffic"], TRAFFIC_PARKING)),
    "parking_areas": prepare_gdf(filter_fclass(layers["traffic_a"], TRAFFIC_PARKING)),
    "traffic_signals": prepare_gdf(filter_fclass(layers["traffic"], TRAFFIC_SIGNALS)),
    "fuel_points": prepare_gdf(filter_fclass(layers["traffic"], FUEL_CLASSES)),

    # religion/community
    "pofw_jewish_points": prepare_gdf(filter_fclass(layers["pofw"], POFW_JEWISH)),
    "pofw_jewish_polygons": prepare_gdf(filter_fclass(layers["pofw_a"], POFW_JEWISH)),

    # buildings
    "building_residential_types": prepare_gdf(filter_type(layers["buildings"], BUILDING_RESIDENTIAL_TYPES)),
    "building_public_types": prepare_gdf(filter_type(layers["buildings"], BUILDING_PUBLIC_TYPES)),
}

logger.info("Prepared filtered layers.")


# =========================================================
# FEATURE EXTRACTION
# =========================================================




def extract_features_cached(doc):
    point = get_point(doc)
    if not point:
        return None

    point = to_3857(point)

    key = grid_key(point)

    if key in feature_cache:
        cached = feature_cache[key].copy()
        cached["_id"] = doc["_id"]
        return cached

    # חישוב רגיל
    features = extract_features(doc)

    if features:
        feature_cache[key] = features.copy()

    return features


def extract_features(doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    point = point_from_doc(doc)
    if point is None:
        return None

    # -------------------------
    # Distance features
    # -------------------------
    dist_to_water = distance_to(point, prepared["water_polygons"])
    dist_to_beach = distance_to(point, prepared["beaches"])
    dist_to_river = distance_to(point, prepared["rivers_streams"])
    dist_to_main_road = distance_to(point, prepared["roads_main"])
    dist_to_secondary_road = distance_to(point, prepared["roads_secondary"])
    dist_to_local_road = distance_to(point, prepared["roads_local"])
    dist_to_bus_stop = distance_to(point, prepared["bus_stops"])
    dist_to_rail_station = distance_to(point, prepared["rail_stations"])
    dist_to_railway_line = distance_to(point, prepared["railways_all"])
    dist_to_park = distance_to(point, prepared["parks"])
    dist_to_school = distance_to(point, prepared["schools"])
    dist_to_kindergarten = distance_to(point, prepared["kindergartens"])
    dist_to_supermarket = distance_to(point, prepared["shops"])
    dist_to_bus_station = distance_to(point, prepared["bus_stations"])

    # -------------------------
    # Radius/count features
    # -------------------------
    num_pois_300m = count_nearby(point, prepared["pois_all"], 300)
    num_pois_1km = count_nearby(point, prepared["pois_all"], 1000)
    num_restaurants_500m = count_nearby(point, prepared["restaurants"], 500)
    num_shops_500m = count_nearby(point, prepared["shops"], 500)
    num_schools_1km = count_nearby(point, prepared["schools"], 1000)
    num_kindergartens_1km = count_nearby(point, prepared["kindergartens"], 1000)
    num_parks_1km = count_nearby(point, prepared["parks"], 1000)
    num_playgrounds_500m = count_nearby(point, prepared["playgrounds"], 500)
    num_pharmacies_1km = count_nearby(point, prepared["pharmacies"], 1000)
    num_attractions_1km = count_nearby(point, prepared["attractions"], 1000)
    num_bus_stops_500m = count_nearby(point, prepared["bus_stops"], 500)
    num_traffic_signals_300m = count_nearby(point, prepared["traffic_signals"], 300)
    num_parking_points_500m = count_nearby(point, prepared["parking_points"], 500)
    num_fuel_1km = count_nearby(point, prepared["fuel_points"], 1000)
    num_synagogues_1km = (
        count_nearby(point, prepared["pofw_jewish_points"], 1000) +
        count_nearby(point, prepared["pofw_jewish_polygons"], 1000)
    )

    # -------------------------
    # Spatial / area features
    # -------------------------
    green_ratio_1km = area_ratio_within(point, prepared["green_landuse"], 1000)
    building_density_200m = area_ratio_within(point, prepared["buildings_all"], 200)
    parking_area_ratio_500m = area_ratio_within(point, prepared["parking_areas"], 500)
    industrial_ratio_1km = area_ratio_within(point, prepared["industrial_landuse"], 1000)
    commercial_ratio_1km = area_ratio_within(point, prepared["commercial_landuse"], 1000)
    residential_ratio_1km = area_ratio_within(point, prepared["residential_landuse"], 1000)
    water_ratio_1km = area_ratio_within(point, prepared["water_polygons"], 1000)

    # -------------------------
    # Boolean/proxy features
    # -------------------------
    is_industrial_near_500m = intersects_buffer(point, prepared["industrial_landuse"], 500)
    is_commercial_near_300m = intersects_buffer(point, prepared["commercial_landuse"], 300)
    is_residential_near_100m = intersects_buffer(point, prepared["residential_landuse"], 100)
    is_park_near_300m = intersects_buffer(point, prepared["parks"], 300)
    is_water_near_300m = intersects_buffer(point, prepared["water_polygons"], 300)

    # -------------------------
    # Urban form / network proxies
    # -------------------------
    road_length_main_1km = total_length_within(point, prepared["roads_main"], 1000)
    road_length_all_1km = total_length_within(point, prepared["roads_all"], 1000)
    rail_length_1km = total_length_within(point, prepared["railways_all"], 1000)
    waterway_length_1km = total_length_within(point, prepared["rivers_streams"], 1000)

    num_buildings_300m = count_nearby(point, prepared["buildings_all"], 300)
    num_residential_buildings_300m = count_nearby(point, prepared["building_residential_types"], 300)
    num_public_buildings_500m = count_nearby(point, prepared["building_public_types"], 500)

    unique_poi_types_1km = count_unique_values_nearby(point, prepared["pois_all"], 1000, "fclass")

    # -------------------------
    # Composite scores
    # -------------------------
    walkability_score = num_restaurants_500m + num_shops_500m + num_pharmacies_1km + num_playgrounds_500m
    education_score = num_schools_1km + num_kindergartens_1km
    accessibility_score = (
        safe_div(1.0, (dist_to_bus_stop or 1.0) + 1.0) +
        safe_div(1.0, (dist_to_main_road or 1.0) + 1.0) +
        safe_div(1.0, (dist_to_rail_station or 1.0) + 1.0)
    )
    amenity_diversity_score = unique_poi_types_1km
    green_score = (green_ratio_1km * 100.0) + num_parks_1km + (1 if is_park_near_300m else 0)

    # -------------------------
    # Optional transforms
    # -------------------------
    log_dist_to_beach = safe_log1p(dist_to_beach) if dist_to_beach is not None else None
    log_dist_to_main_road = safe_log1p(dist_to_main_road) if dist_to_main_road is not None else None
    log_num_buildings_300m = safe_log1p(num_buildings_300m)

    return {
        "_id": doc["_id"],

        # distance
        "dist_to_water": dist_to_water,
        "dist_to_beach": dist_to_beach,
        "dist_to_river": dist_to_river,
        "dist_to_main_road": dist_to_main_road,
        "dist_to_secondary_road": dist_to_secondary_road,
        "dist_to_local_road": dist_to_local_road,
        "dist_to_bus_stop": dist_to_bus_stop,
        "dist_to_rail_station": dist_to_rail_station,
        "dist_to_railway_line": dist_to_railway_line,
        "dist_to_park": dist_to_park,
        "dist_to_school": dist_to_school,
        "dist_to_kindergarten": dist_to_kindergarten,
        "dist_to_supermarket": dist_to_supermarket,
        "dist_to_bus_station": dist_to_bus_station,

        # counts
        "num_pois_300m": num_pois_300m,
        "num_pois_1km": num_pois_1km,
        "num_restaurants_500m": num_restaurants_500m,
        "num_shops_500m": num_shops_500m,
        "num_schools_1km": num_schools_1km,
        "num_kindergartens_1km": num_kindergartens_1km,
        "num_parks_1km": num_parks_1km,
        "num_playgrounds_500m": num_playgrounds_500m,
        "num_pharmacies_1km": num_pharmacies_1km,
        "num_attractions_1km": num_attractions_1km,
        "num_bus_stops_500m": num_bus_stops_500m,
        "num_traffic_signals_300m": num_traffic_signals_300m,
        "num_parking_points_500m": num_parking_points_500m,
        "num_fuel_1km": num_fuel_1km,
        "num_synagogues_1km": num_synagogues_1km,

        # area / ratios
        "green_ratio_1km": green_ratio_1km,
        "building_density_200m": building_density_200m,
        "parking_area_ratio_500m": parking_area_ratio_500m,
        "industrial_ratio_1km": industrial_ratio_1km,
        "commercial_ratio_1km": commercial_ratio_1km,
        "residential_ratio_1km": residential_ratio_1km,
        "water_ratio_1km": water_ratio_1km,

        # booleans
        "is_industrial_near_500m": is_industrial_near_500m,
        "is_commercial_near_300m": is_commercial_near_300m,
        "is_residential_near_100m": is_residential_near_100m,
        "is_park_near_300m": is_park_near_300m,
        "is_water_near_300m": is_water_near_300m,

        # urban/network
        "road_length_main_1km": road_length_main_1km,
        "road_length_all_1km": road_length_all_1km,
        "rail_length_1km": rail_length_1km,
        "waterway_length_1km": waterway_length_1km,
        "num_buildings_300m": num_buildings_300m,
        "num_residential_buildings_300m": num_residential_buildings_300m,
        "num_public_buildings_500m": num_public_buildings_500m,
        "unique_poi_types_1km": unique_poi_types_1km,

        # composite
        "walkability_score": walkability_score,
        "education_score": education_score,
        "accessibility_score": accessibility_score,
        "amenity_diversity_score": amenity_diversity_score,
        "green_score": green_score,

        # transformed
        "log_dist_to_beach": log_dist_to_beach,
        "log_dist_to_main_road": log_dist_to_main_road,
        "log_num_buildings_300m": log_num_buildings_300m,

        # metadata
        "feature_source": "osm",
        "feature_version": "v1"
    }


# =========================================================
# INDEXES
# =========================================================

def ensure_indexes() -> None:
    features_col.create_index("feature_version")
    logger.info("Ensured indexes on features collection.")


# =========================================================
# MAIN
# =========================================================

def run():

    all_features = []
    ensure_indexes()

    total = raw_col.count_documents({})
    batch_size = 50_000

    print(f"Total docs: {total}")

    for offset in range(0, total, batch_size):
        print(f"\nProcessing batch {offset} - {offset + batch_size}")

        docs = list(
            raw_col.find(
                {},
                {"_id": 1, "geometry": 1}
            ).skip(offset).limit(batch_size)
        )

        ops = []

        for doc in tqdm(docs, desc=f"Batch {offset}"):
            try:
                features = extract_features_cached(doc)
                if not features:
                    continue

                all_features.append(features)

            except Exception as e:
                print(f"Error on {doc.get('_id')}: {e}")

    df = pd.DataFrame(all_features)

    df.to_csv("features_osm.csv", index=False)

    print("✅ Saved features to CSV")


if __name__ == "__main__":
    run()