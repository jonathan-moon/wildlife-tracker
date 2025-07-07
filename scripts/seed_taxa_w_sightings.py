import csv
import requests
import time

# get all unique taxon ids from the observations table (yoesmite_observations.csv)
def get_unique_taxon_ids(input_file="yosemite_observations.csv"):
    taxon_ids = set() #create a set to put all ids
    with open(input_file, mode="r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile) # what does this do? I think it opens a reader object (of csv file) that puts it into a dictionary?
        for row in reader:
            taxon_id = row.get("taxon_id", "").strip() # strip()? removes spaces?
            if taxon_id.isdigit():
                taxon_ids.add(taxon_id)
    print(f"Number of taxon id's: {len(taxon_ids)}")
    return taxon_ids

# use input taxon_id to fetch taxon data for that entry
def fetch_taxon_data(taxon_id, retries=3, delay=2):
    url = f"https://api.inaturalist.org/v1/taxa/{taxon_id}"
    for attempt in range(retries):
        response = requests.get(url)
        if response.status_code == 429:
            print(f"Rate limit hit for taxon {taxon_id}. Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 2  # exponential backoff
            continue
        if response.status_code != 200:
            print(f"Error fetching taxon {taxon_id}: {response.status_code}")
            return None
        try:
            data = response.json().get("results", [])
            return data[0] if data else None
        except requests.exceptions.JSONDecodeError:
            print(f"Could not decode JSON for taxon {taxon_id}")
            return None
    print(f"Failed to fetch taxon {taxon_id} after {retries} retries.")
    return None


# use fetched taxon_data to seed db
def seed_db(output_file= "taxa.csv", limit = 600):
    taxon_ids = get_unique_taxon_ids()
    print(f"Fetching data for up to {limit} taxon ids")

    with open(output_file, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["id", "name", "preferred_common_name",
            "rank", "iconic_taxon_name", "ancestor_ids", "photo_url"]
        )
        count = 0

        for taxon_id in taxon_ids:
            taxon = fetch_taxon_data(taxon_id)
            if not taxon:
                continue

            photo_url = taxon.get("default_photo", {}).get("medium_url", {})

            
            writer.writerow([
                taxon.get("id"),
                taxon.get("name"),
                taxon.get("preferred_common_name", ""),
                taxon.get("rank", ""),
                taxon.get("iconic_taxon_name", ""),
                ",".join(str(aid) for aid in taxon.get("ancestor_ids", [])),
                photo_url
            ])
            
            count+=1
            if count >= limit:
                break

            if count % 100 == 0:
                print(f"Written another 100 values to taxon.csv of size {count}")
    
    print(f"Saved {count} taxa to output file")

if __name__ == "__main__":
    seed_db()