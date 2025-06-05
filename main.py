from fastapi import FastAPI
import httpx

app = FastAPI() # init FastAPI

@app.get("/inat-test") # create GET endpoint at /inat-test
async def get_inaturalist_data(): # creates async function
    url = "https://api.inaturalist.org/v1/observations?lat=40.7&lng=-74.0&radius=5" # def url of API endpoint being accessed
    async with httpx.AsyncClient() as client: # async function, client allows us to access API easily
        response = await client.get(url) # client accesses API endpoint
        data = response.json() # response in JSON form
    if not data["results"]:
        return {"Message" : "No results found"}
    first = data["results"][0]
    return {
        "species_common_name": first.get("taxon", {}).get("preferred_common_name"),
        "scientific_name": first.get("taxon", {}).get("name"),
        "observation_id": first.get("id"),
        "url": first.get("uri"),
        "latitude": first.get("geojson", {}).get("coordinates", [None, None])[1],
        "longitude": first.get("geojson", {}).get("coordinates", [None, None])[0],
        "observed_on": first.get("observed_on_details", {}).get("date"),
        "description": first.get("description"),
        "observer": first.get("user", {}).get("login"),
        "observer_icon": first.get("user", {}).get("icon_url"),
        "image": first.get("taxon", {}).get("default_photo", {}).get("square_url") or (
            first.get("photos", [{}])[0].get("url")
        ),
        "location_name": first.get("place_guess")
    }