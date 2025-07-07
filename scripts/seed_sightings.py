# to fetch observations from iNaturalist to seed database; initially for just within Yosemite bounding box

import csv
import datetime
import requests
import json

NE_LAT = 38.1851
NE_LNG = -119.1964
SW_LAT = 37.4927
SW_LNG = -119.8864

two_years_ago = datetime.date.today() - datetime.timedelta(days=730)


base_url = "https://api.inaturalist.org/v1/observations"
params = {
    "nelat": NE_LAT,
    "nelng": NE_LNG,
    "swlat": SW_LAT,
    "swlng": SW_LNG,
    "verifiable": "true",
    "d1": two_years_ago.isoformat(),  # ISO date string
    "order_by": "observed_on",
    "order": "desc",
    "per_page": 100,
    "page": 1
}

def fetch_obs_to_csv(filename="yosemite_observations.csv", max_pages=10):
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            "id", "observed_on", "datetime_string", "place_guess", "latitude", "longitude",
            "taxon_id", "scientific_name", "preferred_common_name", "iconic_taxon_name", "image_urls"
        ])

        for page in range(1, max_pages+1): # for each page from 1 to max_page
            params["page"] = page # set query param page to current page

            response = requests.get(base_url, params) # make request from iNaturalist

            if response.status_code != 200:
                print(f"Failed to fetch page {page}")
                break

            data = response.json() # put response in json format
            results = data.get("results", []) # actual results are nested in "results" json parent

            if not results:
                break

            for obs in results:
                taxon = obs.get("taxon", {})
                if not taxon:
                    continue

                # observed_on = obs.get("observed_on_details", {})
                datetime_str = obs.get("time_observed_at")
                if not datetime_str:
                    details = obs.get("observed_on_details", {})
                    date = details.get("date")
                    hour = details.get("hour")
                    if date and hour is not None:
                        datetime_str = f"{date}T{hour:02d}:00:00"
                
                # print(observed_on)

                # print(datetime_str)
 
                photos = obs.get("photos", [])

                # if photos:
                    # print(photos[0])
                image_urls = [photo.get("url") for photo in photos if photo.get("url")]
                image_url_string = "|".join(image_urls)

                
                writer.writerow([
                    obs.get("id"),
                    obs.get("observed_on"),
                    datetime_str,
                    obs.get("place_guess"),
                    obs.get("geojson", {}).get("coordinates", [None, None])[1],
                    obs.get("geojson", {}).get("coordinates", [None, None])[0],
                    taxon.get("id"),
                    taxon.get("name"),
                    taxon.get("preferred_common_name"),
                    taxon.get("iconic_taxon_name"),
                    image_url_string
                ])

            
            print(f"Page {page} complete...")
    print(f"Data written to {filename}")

if __name__ == "__main__":
    fetch_obs_to_csv()