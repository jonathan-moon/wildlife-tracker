import csv
import requests
import time
from requests.exceptions import ReadTimeout, RequestException

# Get unique taxon IDs from the sightings CSV
def get_unique_taxon_ids(input_file="../tables/yosemite_observations.csv"):
    taxon_ids = set()
    with open(input_file, mode="r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            taxon_id = row.get("taxon_id", "").strip()
            if taxon_id.isdigit():
                taxon_ids.add(taxon_id)
    print(f"Found {len(taxon_ids)} unique taxon IDs.")
    return taxon_ids

# Fetch taxon data from iNaturalist API
def fetch_taxon_data(taxon_id, retries=3, delay=2):
    url = f"https://api.inaturalist.org/v1/taxa/{taxon_id}"
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=10)

            if response.status_code == 429:
                print(f"⚠️ Rate limit hit for taxon {taxon_id}. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
                continue

            if response.status_code != 200:
                print(f"Error fetching taxon {taxon_id}: HTTP {response.status_code}")
                return None

            data = response.json().get("results", [])
            return data[0] if data else None

        except ReadTimeout:
            print(f"Timeout fetching taxon {taxon_id}. Retrying in {delay}s...")
            time.sleep(delay)
            delay *= 2
        except RequestException as e:
            print(f"Request failed for taxon {taxon_id}: {e}")
            return None

    print(f"Failed to fetch taxon {taxon_id} after {retries} retries.")
    return None

#  Save taxa info into a CSV
def seed_db(output_file="../tables/taxa.csv", limit=600):
    taxon_ids = get_unique_taxon_ids()
    print(f"Fetching data for up to {limit} taxon IDs...")

    with open(output_file, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            "id", "name", "preferred_common_name",
            "rank", "iconic_taxon_name", "ancestor_ids", "photo_url"
        ])

        count = 0
        for taxon_id in taxon_ids:
            taxon = fetch_taxon_data(taxon_id)

            if not taxon or taxon is None:
                continue
            
            
            # print(f"This is the taxon data: {taxon.}")
            photo_url = taxon.get("default_photo", {}).get("medium_url", "")

            writer.writerow([
                taxon.get("id"),
                taxon.get("name"),
                taxon.get("preferred_common_name", ""),
                taxon.get("rank", ""),
                taxon.get("iconic_taxon_name", ""),
                ",".join(str(aid) for aid in taxon.get("ancestor_ids", [])),
                photo_url
            ])

            count += 1
            if count >= limit:
                break
            if count % 100 == 0:
                print(f"Fetched {count} taxa...")

    print(f"\nSaved {count} taxa to '{output_file}'.")


if __name__ == "__main__":
    seed_db()