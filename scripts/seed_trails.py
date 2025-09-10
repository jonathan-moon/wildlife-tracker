import os
import osmnx as ox
import pandas as pd

# Download Yosemite polygon fresh
print("Downloading Yosemite boundary...")
yosemite = ox.geocode_to_gdf("Yosemite National Park, California, USA")
yosemite = yosemite.to_crs(epsg=4326)
polygon = yosemite.geometry.iloc[0]

# Get trail data
print("Downloading OSM trails...")
tags = {"highway": "path"}
trails = ox.features_from_polygon(polygon, tags=tags)

# Step 3: Handle unnamed trails
unnamed_counter = 1 # used to name unnamed trails in db
def fill_name(name):
    global unnamed_counter
    if pd.isna(name) or str(name).strip() == "":
        result = f"Unnamed trail {unnamed_counter}"
        unnamed_counter += 1
        return result
    return name

trails["name"] = trails["name"].apply(fill_name)

# Create output DataFrame
trails.reset_index(inplace=True)
output_df = pd.DataFrame({
    "id": trails.index + 1,
    "name": trails["name"],
    "surface": trails.get("surface"),
    "bicycle": trails.get("bicycle"),
    "horse": trails.get("horse"),
    "foot": trails.get("foot"),
    "trail_visibility": trails.get("trail_visibility"),
    "geometry": trails.geometry.apply(lambda g: g.wkt if g else None),
    "sighting_count": 0,
    "location_id": 1  # Yosemite
})

# Save to CSV
output_path = "../tables/trails_table.csv"
output_df.to_csv(output_path, index=False)

print(f"✅ Saved to {output_path}")