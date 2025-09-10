import os
from supabase import create_client, Client
from dotenv import load_dotenv
import requests
import shapely.wkt
from shapely.geometry import Point, LineString, Polygon
from typing import List, Dict, Optional

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Missing Supabase credentials, check .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
MAX_TRAIL_DISTANCE_M = 50

# Returns list of location ids
def fetch_all_location_ids() -> List[int]:
    response = supabase.table("locations").select("id").execute()
    return [row["id"] for row in response.data]

# Returns geometry of location given location_id
def fetch_location_geometry(location_id: int):
    response = supabase.table("locations") \
        .select("geometry") \
        .eq("id", location_id) \
        .single() \
        .execute()
    geom = response.data.get("geometry")
    return shapely.wkt.loads(geom) if geom else None

# fetches most datetime string of most recent sighting
def fetch_most_recent_datetime(location_id):
    response = (
        supabase.table("sightings")
        .select("datetime_str")
        .eq("location_id", location_id)
        .order("datetime_str", desc=True)
        .limit(1)
        .execute()
    )
    return response.data[0]["datetime_str"] if response.data else None


# Returns list of trails (id, geometry)
def load_trails_from_supabase():
    response = supabase.table("trails").select("id, geometry").execute()
    trails = []
    for row in response.data:
        try:
            geom = shapely.wkt.loads(row["geometry"])
            trails.append((row["id"], geom))
        except Exception as e:
            print(f"Skipping trail {row['id']} due to error: {e}")
    return trails

# returns id of closest trail
def find_nearest_trail(lat: float, lon: float, trails: List, max_distance_m=50) -> Optional[int]:
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


def fetch_new_sightings(since: str, polygon: Polygon, max_pages: int = 5):
    observations = []
    base_url = "https://api.inaturalist.org/v1/observations"

    # Expand the polygon bounds to ensure we capture nearby edge cases
    minx, miny, maxx, maxy = polygon.bounds
    padding = 0.05  # ~5.5 km buffer
    swlat = miny - padding
    swlng = minx - padding
    nelat = maxy + padding
    nelng = maxx + padding

    for page in range(1, max_pages + 1):
        params = {
            "swlat": swlat,
            "swlng": swlng,
            "nelat": nelat,
            "nelng": nelng,
            "verifiable": "true",
            "d1": since,
            "order_by": "observed_on",
            "order": "asc",
            "per_page": 100,
            "page": page
        }

        response = requests.get(base_url, params)
        if response.status_code != 200:
            print(f"Error fetching page {page}: {response.status_code}")
            break

        data = response.json()
        results = data.get("results", [])
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
            if not polygon.contains(point):
                continue  # Filter to only include points inside polygon

            datetime_str = obs.get("time_observed_at")
            if not datetime_str:
                details = obs.get("observed_on_details", {})
                date = details.get("date")
                hour = details.get("hour")
                if date and hour is not None:
                    datetime_str = f"{date}T{hour:02d}:00:00"

            photos = obs.get("photos", [])
            image_urls = [photo.get("url") for photo in photos if photo.get("url")]
            image_url_string = "|".join(image_urls)

            observations.append({
                "id": obs.get("id"),
                "observed_on": obs.get("observed_on"),
                "datetime_str": datetime_str,
                "place_guess": obs.get("place_guess"),
                "latitude": lat,
                "longitude": lon,
                "taxon_id": taxon.get("id"),
                "scientific_name": taxon.get("name"),
                "preferred_common_name": taxon.get("preferred_common_name"),
                "iconic_taxon_name": taxon.get("iconic_taxon_name"),
                "image_urls": image_url_string
            })

    print(f"Retrieved {len(observations)} new observations.")
    return observations


def ensure_taxa_exist(sightings):
    from seed_taxa_w_sightings import fetch_taxon_data

    taxon_ids = list({s["taxon_id"] for s in sightings if s.get("taxon_id")})
    existing_ids = set()
    CHUNK_SIZE = 100
    for i in range(0, len(taxon_ids), CHUNK_SIZE):
        chunk = taxon_ids[i:i+CHUNK_SIZE]
        resp = supabase.table("taxa").select("id").in_("id", chunk).execute()
        existing_ids.update({row["id"] for row in resp.data})

    missing = set(taxon_ids) - existing_ids
    for taxon_id in missing:
        taxon = fetch_taxon_data(taxon_id)
        if not taxon:
            continue
        try:
            supabase.table("taxa").insert({
                "id": taxon.get("id"),
                "name": taxon.get("name"),
                "preferred_common_name": taxon.get("preferred_common_name", ""),
                "rank": taxon.get("rank", ""),
                "iconic_taxon_name": taxon.get("iconic_taxon_name", ""),
                "ancestor_ids": ",".join(str(aid) for aid in taxon.get("ancestor_ids", [])),
                "photo_url": taxon.get("default_photo", {}).get("medium_url", "")
            }).execute()
        except Exception as e:
            print(f"Failed to insert taxon {taxon_id}: {e}")


def insert_sightings(sightings, location_id, trails, sightings_per_trail):
    for sighting in sightings:
        trail_id = find_nearest_trail(sighting["latitude"], sighting["longitude"], trails)
        sighting["location_id"] = location_id
        sighting["trail_id"] = trail_id

        if trail_id is not None:
            sightings_per_trail[trail_id] = sightings_per_trail.get(trail_id, 0)+1

        try:
            supabase.table("sightings").insert(sighting).execute()
            print(f"Inserted sighting {sighting['id']} for location {location_id}")
        except Exception as e:
            print(f"Failed to insert sighting {sighting['id']}: {e}")

# Reads current sighting count for location, then updates with added sightings
def update_sighting_count_for_location(location_id, sighting_count):
    try:
        response = (
            supabase.table("locations")
            .select("sighting_count")
            .eq("id", location_id)
            .single()  # <- ensures response.data is a dict, not list
            .execute()
        )
        old_count = response.data.get("sighting_count", 0)
        new_count = old_count + sighting_count

        response = (
            supabase.table("locations")
            .update({"sighting_count": new_count})
            .eq("id", location_id)
            .execute()
        )
        print(f"Updated location {location_id} count to {new_count}")
    except Exception as e:
        print(f"Error updating sighting count for location {location_id}: {e}")


if __name__ == "__main__":
    trails = load_trails_from_supabase() # loads all trails
    location_ids = fetch_all_location_ids() # loads all locations

    for loc_id in location_ids: # for each location
        sightings_per_trail = {} # for each trail, save number of new sightings

        print(f"\nProcessing location {loc_id}")
        polygon = fetch_location_geometry(loc_id) # get location geometry

        if not polygon:
            print(f"Skipping location {loc_id}, invalid geometry.")
            continue

        recent = fetch_most_recent_datetime(loc_id) # get most recent sightings from that location
        print(f"Most recent sighting for location {loc_id}: {recent}")

        sightings = fetch_new_sightings(since=recent, polygon=polygon) # fetch new sightings within the shape of current location

        if not sightings:
            print("No new sightings found.")
            continue

        print(f"Ensuring taxa from new sightings exist in Supaabse")
        ensure_taxa_exist(sightings) # For each sigthing, make sure taxa exists
        insert_sightings(sightings, loc_id, trails, sightings_per_trail) # Insert new sightings and update new sighting count for each trail
       
        print(f"Updating sighting count for each trail in location {loc_id}")

        # loop through all sightings_per_trail and read sigthings_count from supabase, update with value in dictionary, then write
        for trail_id, trail_s_count in sightings_per_trail.items():
            print(f"This is the trail id: {trail_id} and this is the number of sightings for this trail: {trail_s_count}")

            # First read current sighting_count
            response1 = (
                supabase.table("trails")
                .select("sighting_count")
                .eq("id", trail_id)
                .eq("location_id", loc_id)
                .execute()
            )
            new_count = response1.data[0].get("sighting_count", 0) + trail_s_count

            # Then update it
            response = (
                supabase.table("trails")
                .update({
                    "sighting_count": new_count
                })
                .eq("id", trail_id)
                .eq("location_id", loc_id)
                .execute()
            )


        update_sighting_count_for_location(loc_id, len(sightings))  # Fetch current sighting count for the location, add len(sightings) and write