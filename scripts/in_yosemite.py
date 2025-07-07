# used to investigate details of iNaturalist observation endpoint (e.g. schema, # of observations, valid/emtpy fields)

import requests
import datetime
import csv
import json

NE_LAT = 38.1851
NE_LNG = -119.1964
SW_LAT = 37.4927
SW_LNG = -119.8864

def main():
    base_url = "https://api.inaturalist.org/v1/observations"

    two_years_ago = datetime.date.today() - datetime.timedelta(days=730)

    params = {
        "nelat": 38.1851,
        "nelng": -119.1964,
        "swlat": 37.4947,
        "swlng": -119.8864,
        "verifiable": "true",
        "per_page": 100,
        "page": 1,
        "d1" : two_years_ago.isoformat(),
        "order_by": "observed_on",
        "order": "desc"
    }

    print("Querying iNaturalist API for sightings in Yosemite area...")

    response = requests.get(base_url, params=params)

    if response.status_code != 200:
        print(f"Failed to fetch data. Status code: {response.status_code}")

    json_data = response.json()
    observations = json_data.get("results", []) # a dictionary of results (dictionaries)

    for obs in observations: # for each dictionary in the outer dictionary
        species_guess = obs.get("species_guess", "N/a")
        species_common = obs.get("species_common_name", "N/a")
        taxon = obs.get("taxon", {})
        if not taxon:
            continue
        taxon_id = taxon.get("id", "N/a")
        sci_name = taxon.get("name", "N/a")
        common_name = taxon.get("preferred_common_name", "N/a")
        kingdom = taxon.get("iconic_taxon_name", "Unknown")

        animals = [
            "Animalia", "Mammalia", "Aves", "Reptilia", "Amphibia",
            "Actinopterygii", "Insecta", "Arachnida", "Mollusca"
        ]

        if kingdom in animals:
            print(f"Kingdom: {kingdom}")
            print(f"    taxon_id: {taxon_id}")
            print(f"    species_guess: {species_guess}")
            print(f"    species_common_name: {species_common}")
            print(f"    sci_name: {sci_name}")
            print(f"    preferred_common_name: {common_name}")
            print("--------------------------------")



if __name__ == "__main__":
    main()