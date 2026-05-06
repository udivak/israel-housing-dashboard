const PHOTON_API = "https://photon.komoot.io/api";

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
  });
  if (options?.lat != null && options?.lon != null) {
    params.set("lat", String(options.lat));
    params.set("lon", String(options.lon));
  }

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
