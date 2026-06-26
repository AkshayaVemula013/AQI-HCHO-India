import ee
import geemap

# 1. Initialize GEE
PROJECT_ID = 'aqi-hcho-1901' 
ee.Initialize(project=PROJECT_ID)

print("🛰️ Generating your first HCHO Pollution Map...")

# 2. Get India's geographic boundary
india_boundary = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017") \
                    .filter(ee.Filter.eq('country_na', 'India'))

# 3. Load and average the Sentinel-5P HCHO data for Nov 2024
hcho_november = ee.ImageCollection('COPERNICUS/S5P/OFFL/L3_HCHO') \
                    .select('tropospheric_HCHO_column_number_density') \
                    .filterBounds(india_boundary) \
                    .filterDate('2024-11-01', '2024-11-30') \
                    .mean() # This averages all 410 images into one clean map
                    
# Clip the map precisely to India's borders
hcho_india = hcho_november.clip(india_boundary)

# 4. Create an interactive Map centered over India
Map = geemap.Map(center=[22.5937, 78.9629], zoom=5)

# Define visual parameters (Blue = Low pollution, Yellow = Medium, Red = High Hotspots)
viz_params = {
    'min': 0.0,
    'max': 0.0003,
    'palette': ['blue', 'teal', 'green', 'yellow', 'orange', 'red']
}

# Add our satellite data layer to the interactive map
Map.addLayer(hcho_india, viz_params, 'Formaldehyde (HCHO) Nov 2024')

# 5. Save the map as a webpage file
output_html = "hcho_map_november_2024.html"
Map.to_html(output_html)

print(f"🎉 Success! The map has been generated and saved locally as: {output_html}")
print("👉 Open your project folder on your computer and double-click that HTML file to see the map!")