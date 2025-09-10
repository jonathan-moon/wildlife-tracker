import csv
import datetime
import requests
import shapely.wkt
from shapely.geometry import Point
from supabase import create_client, Client
from dotenv import load_dotenv
import os

# Load environment variables 
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Config Yosemite
YOSEMITE_LOCATION_ID = 1
MAX_TRAIL_DISTANCE_M = 50
OUTPUT_CSV = "yosemite_observations.csv"

NE_LAT = 38.1851
NE_LNG = -119.1964
SW_LAT = 37.4927
SW_LNG = -119.8864
two_years_ago = datetime.date.today() - datetime.timedelta(days=730)

# iNaturalist API config
base_url = "https://api.inaturalist.org/v1/observations"
params = {
    "nelat": NE_LAT,
    "nelng": NE_LNG,
    "swlat": SW_LAT,
    "swlng": SW_LNG,
    "verifiable": "true",
    "d1": two_years_ago.isoformat(),
    "order_by": "observed_on",
    "order": "desc",
    "per_page": 100,
    "page": 1
}

# helper functions

# load yosemite boundry from supabase
def fetch_yosemite_boundary():
    response = supabase.table("locations").select("geometry").eq("id", YOSEMITE_LOCATION_ID).single().execute()
    if "geometry" not in response.data:
        raise ValueError("Could not fetch Yosemite polygon.")
    return shapely.wkt.loads(response.data["geometry"])

# load trails from supabase
def load_trails_from_supabase():
    response = supabase.table("trails").select("id, geometry").execute()
    if not response.data:
        raise ValueError("Could not fetch trails.")
    trail_geoms = []
    for row in response.data:
        try:
            geom = shapely.wkt.loads(row["geometry"])
            trail_geoms.append((row["id"], geom))
        except Exception as e:
            print(f"Failed to parse geometry for trail {row['id']}: {e}")
    return trail_geoms

# function to map sighting to nearest trail
def find_nearest_trail(lat, lon, trails, max_distance_m=50):
    point = Point(lon, lat)
    closest_id = None
    closest_dist = float("inf")
    for trail_id, line in trails:
        dist_deg = point.distance(line)
        dist_m = dist_deg * 111139  # degrees to meters
        if dist_m < closest_dist and dist_m <= max_distance_m:
            closest_dist = dist_m
            closest_id = trail_id
    return closest_id

# main fetch function retreives sightings from supabase
def fetch_obs_to_csv(filename="../tables/yosemite_observations.csv", max_pages=10):
    trails = load_trails_from_supabase()
    yosemite_poly = fetch_yosemite_boundary()

    total = 0
    assigned = 0
    unassigned = 0

    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            "id", "observed_on", "datetime_str", "place_guess", "latitude", "longitude",
            "taxon_id", "scientific_name", "preferred_common_name", "iconic_taxon_name",
            "image_urls", "trail_id", "location_id"
        ])

        for page in range(1, max_pages + 1):
            params["page"] = page
            response = requests.get(base_url, params)
            if response.status_code != 200:
                print(f"Failed to fetch page {page}")
                break

            results = response.json().get("results", [])
            if not results:
                break

            for obs in results:
                
                taxon = obs.get("taxon", {})
                if not taxon:
                    continue

                coords = obs.get("geojson", {}).get("coordinates", [None, None])
                lat, lon = coords[1], coords[0]
                if lat is None or lon is None:
                    continue

                point = Point(lon, lat)
                if not yosemite_poly.contains(point):
                    continue  # outside park

                total += 1
                trail_id = find_nearest_trail(lat, lon, trails, MAX_TRAIL_DISTANCE_M)
                if trail_id:
                    assigned += 1
                else:
                    unassigned += 1

                datetime_str = obs.get("time_observed_at")
                if not datetime_str:
                    details = obs.get("observed_on_details", {})
                    date = details.get("date")
                    hour = details.get("hour")
                    if date and hour is not None:
                        datetime_str = f"{date}T{hour:02d}:00:00"

                photos = obs.get("photos", [])
                image_urls = [p.get("url") for p in photos if p.get("url")]
                image_url_string = "|".join(image_urls)

                writer.writerow([
                    obs.get("id"),
                    obs.get("observed_on"),
                    datetime_str,
                    obs.get("place_guess"),
                    lat,
                    lon,
                    taxon.get("id"),
                    taxon.get("name"),
                    taxon.get("preferred_common_name"),
                    taxon.get("iconic_taxon_name"),
                    image_url_string,
                    trail_id,
                    YOSEMITE_LOCATION_ID
                ])

            print(f"Page {page} complete...")

    print(f"\n=== SUMMARY ===")
    print(f"Total sightings inside park: {total}")
    print(f"Assigned to trail: {assigned}")
    print(f"Unassigned: {unassigned}")
    print(f"Data written to {filename}")


if __name__ == "__main__":
    fetch_obs_to_csv()