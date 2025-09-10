# Problem: Seeding skips sighting_count and trail_count for locations and sighting_count for trails
# Solution: Backfill all missing data with all data now uploaded to Supabase

# For each location, query all trails with that location id
#   write size of return to trail_count for that location
#   for each trail with matching location ID fetch # sigthings with matching trail and location id
#       write sighting count to that trail and location id
#   add sighting count to sum (for location)
#   after all trails have been queried, add sum of sightings to location for sighting_count

import os
from supabase import create_client, Client
from dotenv import load_dotenv
# import requests
# import shapely.wkt
# from shapely.geometry import Point, LineString, Polygon
from typing import List, Dict, Optional

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Returns list of all location id's
def fetch_locations():
    response = supabase.table("locations").select("id").execute()
    ids = []
    for entry in response.data:
        ids.append(entry["id"])
    return ids

    
# Returns number of trails for that location id
def fetch_trail_count(location_id):
    response = supabase.table("trails").select("id", count="exact").eq("location_id", location_id).execute()
    return response.count


# returns list of trail id's for that location_id
def fetch_trails(location_id):
    response = supabase.table("trails").select("id").eq("location_id", location_id).execute()
    trail_ids = []
    for entry in response.data:
        trail_ids.append(entry["id"])
    return trail_ids


# returns number of sightings for the matching location id and trial id
def fetch_sightings_count(location_id, trail_id):
    response = supabase.table("sightings").select("id", count="exact").eq("location_id", location_id).eq("trail_id", trail_id).execute()
    return response.count

# returns the number of sightings in a given location (unassigned or assigned)
def fetch_sightings_in_loc(location_id):
    response = supabase.table("sightings").select("id", count="exact").eq("location_id", location_id).execute()
    return response.count

def update_location(location_id, sighting_count, trail_count):
    response = supabase.table("locations").update({
            "sighting_count": sighting_count,
            "trail_count": trail_count
        }).eq("id", location_id).execute()
    print(f"location {location_id} has been updated")

def update_trail(location_id, trail_id, sighting_count):
    response = supabase.table("trails").update({
            "sighting_count": sighting_count
        }).eq("location_id", location_id).eq("id", trail_id).execute()
    print(f"Trail {trail_id} in location {location_id} has been updated")


if __name__ == "__main__":
    location_ids = fetch_locations() # fetches all location ids
    print(f"These are the location_ids: {location_ids}")
    for loc_id in location_ids: # for each location
        trail_count = fetch_trail_count(loc_id) # fetch the number of trails
        print(f"This is the number of trails for location {loc_id}: {trail_count}")
        trail_ids = fetch_trails(loc_id) # fetch all trail ids
        for trail_id in trail_ids: # for each trail id
            num_sightings = fetch_sightings_count(loc_id, trail_id) # get the number of sightings on that trail
            update_trail(loc_id, trail_id, num_sightings) # update each trail with the number of sightings
        num_sightings_in_loc = fetch_sightings_in_loc(loc_id) # get number of sightings in the location
        print(f"This is the total number of sightings in location {loc_id}: {num_sightings_in_loc}")
        update_location(loc_id, num_sightings_in_loc, trail_count) # update the number of trails and sightings in that location

