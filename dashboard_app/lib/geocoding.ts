const PHOTON_API = "https://photon.komoot.io/api";

// Israel bounding box — keeps results within the country.
const ISRAEL_BBOX = "34.2,29.5,35.9,33.3"; // lon1,lat1,lon2,lat2
// Centroid of Israel's populated area (used as location bias).
const ISRAEL_LAT = 31.7;
const ISRAEL_LON = 34.9;

export interface PhotonFeature {
  type: "Feature";
  geometry: { type: "Point"; coordinates: [number, number] };
  properties: {
    osm_id?: number;
    osm_type?: string;
    name?: string;
    street?: string;
    housenumber?: string;
    postcode?: string;
    district?: string;
    county?: string;
    state?: string;
    country?: string;
    countrycode?: string;
    type?: string;
  };
}

export interface PhotonResponse {
  type: "FeatureCollection";
  features: PhotonFeature[];
}

export async function searchPlaces(
  query: string,
  options?: { limit?: number; lat?: number; lon?: number }
): Promise<PhotonFeature[]> {
  if (!query.trim()) return [];

  const params = new URLSearchParams({
    q: query.trim(),
    limit: String(options?.limit ?? 8),
    lang: "he",
    bbox: ISRAEL_BBOX,
    // Location bias defaults to centre of Israel; caller can override.
    lat: String(options?.lat ?? ISRAEL_LAT),
    lon: String(options?.lon ?? ISRAEL_LON),
  });

  const res = await fetch(`${PHOTON_API}/?${params}`);
  if (!res.ok) throw new Error("Geocoding failed");
  const data: PhotonResponse = await res.json();
  return data.features ?? [];
}

export function formatAddress(f: PhotonFeature): string {
  const p = f.properties;
  const parts = [p.name, p.street, p.district, p.county, p.state, p.country].filter(Boolean);
  return parts.join(", ") || "Unknown";
}
