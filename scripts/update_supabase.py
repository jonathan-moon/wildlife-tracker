# This file:
#   - Fetches the most recent sighting stored in Supabase sightings table
#   - Fetches all sightings from observation API following a given date
#   - Uploads most recent sightings into Supabase sightings table

import os # Gives codebase access to OS tools (e.g. get environment variables)
from supabase import create_client, Client # to connect to supabase
from dotenv import load_dotenv # to load .env variables into environment
import requests


load_dotenv()

# fetching variables from environment
SUPABASE_URL = os.getenv("SUPABASE_URL") 
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# make sure env variables were loaded
if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("MIssing Supabase credentials, check .env file")

# connect to Supabase (client is a tool that allows calls to Supabase backend)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# fetches most recent entry in sightings table (Supabase), returns datetime_string of most recent sightings
def fetch_most_recent_sighting_from_supabase():
    try:
        response = supabase.table("sightings") \
            .select("*") \
            .order("observed_on", desc=True) \
            .limit(1) \
            .execute()

        results = response.data
        if results:
            most_recent = results[0]
            print(f"Most recent result in database: {most_recent}")
            return most_recent["datetime_string"]
    except Exception as e:
        print(f"Error fetching most recent sighting from Supabase: {str(e)}")
        return None

# fetch sightings from input date on from iNaturalist, returns list of new sightings
def fetch_new_sightings(since: str, max_pages: int = 5):
    observations = []
    NE_LAT = 38.1851
    NE_LNG = -119.1964
    SW_LAT = 37.4927
    SW_LNG = -119.8864
    base_url = "https://api.inaturalist.org/v1/observations"
    params = {
        "nelat": NE_LAT,
        "nelng": NE_LNG,
        "swlat": SW_LAT,
        "swlng": SW_LNG,
        "verifiable": "true",
        "d1": since,
        "order_by": "observed_on",
        "order": "asc",
        "per_page": 100,
        "page": 1
    }

    for page in range(1, max_pages + 1):
        params["page"] = page
        response = requests.get(base_url, params)

        if response.status_code != 200:
            print(f"Error in fetch_new_sightings() getting response from iNaturalist: {response.status_code}")
            break

        data = response.json()
        results = data.get("results", [])

        if not results:
            print("No results found in fetch_new_sightings()")
            break

        for obs in results: # for each observation in results (an array of returned objects)

            taxon = obs.get("taxon", {})
            if not taxon:
                    continue

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
                "datetime_string": datetime_str,
                "place_guess": obs.get("place_guess"),
                "latitude": obs.get("geojson", {}).get("coordinates", [None, None])[1],
                "longitude": obs.get("geojson", {}).get("coordinates", [None, None])[0],
                "taxon_id": taxon.get("id"),
                "scientific_name": taxon.get("name"),
                "preferred_common_name": taxon.get("preferred_common_name"),
                "iconic_taxon_name": taxon.get("iconic_taxon_name"),
                "image_urls": image_url_string
            })

    print(f"Retrieved {len(observations)} new observations.")
    return observations

# checks if there are new taxon from new sightings, fetches new taxon and uploads to Supabase
def ensure_taxa_exist(sightings):
    unique_taxon_ids = list({s["taxon_id"] for s in sightings if s.get("taxon_id")}) # list of all taxon_ids in sightings list
    print(f"Checking {len(unique_taxon_ids)} unique taxon IDs...")

    existing_ids = set()
    CHUNK_SIZE = 100

    for i in range(0, len(unique_taxon_ids), CHUNK_SIZE): # fetch all taxon ids in Supabase
        chunk = unique_taxon_ids[i:i+CHUNK_SIZE]
        response = supabase.table("taxa").select("id").in_("id", chunk).execute()
        ids_in_db = {row["id"] for row in response.data}
        existing_ids.update(ids_in_db)

    missing_ids = set(unique_taxon_ids) - existing_ids # subtract all taxon_ids in new sightings from existing ids in supabase to get missing ids
    print(f"{len(missing_ids)} taxa missing from Supabase")

    from seed_taxa_w_sightings import fetch_taxon_data  # reuse existing function for fetching taxon data

    for taxon_id in missing_ids: # for each missing taxa id, get taxon data and insert into supabase table
        taxon = fetch_taxon_data(taxon_id)
        if not taxon:
            continue  # skip on failure

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
            print(f"Inserted taxon {taxon_id}")
        except Exception as e:
            print(f"Failed to insert taxon {taxon_id}: {str(e)}")

# uploads all new sightings to Supabase
def insert_new_sightings(sightings):
    for sighting in sightings:
        try:
            supabase.table("sightings").insert(sighting).execute()
            print(f"Inserted sighting {sighting['id']} with date {sighting['observed_on']}")
        except Exception as e:
            print(f"Failed to insert sighting {sighting['id']}: {e}")



if __name__ == "__main__":
    most_recent = fetch_most_recent_sighting_from_supabase()
    print("Just got date of most recent sighting in Supabase... Now fetching all new sightings. ")
    new_sightings = fetch_new_sightings(most_recent)
    if new_sightings:
        print("Just got all new sightings from iNaturalist, time to process for new taxon")
        ensure_taxa_exist(new_sightings)
        print("Inserted all new taxa, now uploading sightings")
        insert_new_sightings(new_sightings)
    else:
        print("No new sightings to process.")
