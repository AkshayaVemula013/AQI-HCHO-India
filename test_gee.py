import ee

# 1. Paste your exact Project ID between the quotes below:
PROJECT_ID = 'aqi-hcho-1901' 

try:
    # We now pass the project name directly to Google
    ee.Initialize(project=PROJECT_ID)
    print("🚀 Google Earth Engine successfully initialized!")
    
    # 2. Run the quick test: Get the elevation of Mount Everest
    dem = ee.Image('USGS/SRTMGL1_003')
    everest_coords = ee.Geometry.Point([86.9250, 27.9881])
    
    # Sample the data at those coordinates
    elevation_data = dem.sample(everest_coords, 30).first().get('elevation').getInfo()
    print(f"🏔️ Test Success! Mount Everest Elevation: {elevation_data} meters")

except Exception as e:
    print(f"❌ Initialization failed. Error: {e}")