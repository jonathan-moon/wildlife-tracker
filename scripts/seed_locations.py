import os
import pandas as pd
import geopandas as gpd
import osmnx as ox
import uuid
from shapely.geometry import Polygon

# Generate a stable UUID for Yosemite (optional: hardcoded ID)
YOSEMITE_ID = str(uuid.uuid4())

print("Downloading Yosemite boundary...")
boundary_gdf = ox.geocode_to_gdf("Yosemite National Park, California, USA")

# Make sure we have a polygon
if not isinstance(boundary_gdf.geometry.iloc[0], Polygon):
    raise ValueError("Geometry is not a polygon")

# Convert to WKT for CSV compatibility
boundary_gdf["geometry"] = boundary_gdf["geometry"].apply(lambda geom: geom.wkt)

# Create the final dataframe for CSV export
locations_df = pd.DataFrame({
    "id": [YOSEMITE_ID],
    "name": ["Yosemite"],
    "geometry": boundary_gdf["geometry"],
    "sighting_count": [0],
    "trail_count": [0]
})

# Save to CSV in the 'tables' folder
output_file = os.path.join("../tables", "locations_seed.csv")
locations_df.to_csv(output_file, index=False)
print(f"Exported Yosemite location to {output_file}")