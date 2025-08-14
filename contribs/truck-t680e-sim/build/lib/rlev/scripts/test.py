from pyproj import Transformer

# Define transformation from EPSG:3857 to EPSG:4326
transformer = Transformer.from_crs("EPSG:9822", "EPSG:4326", always_xy=True)

# Given coordinates in EPSG:3857
coordinates = [
    (-1.4385916123686317E7, 3967923.589828896),
    (-1.4385888191577816E7, 3967903.1373500545),
    (-1.4436919373613337E7, 3986161.361263343),
    (-1.439194842050553E7, 3981505.4243721925),
    (-1.4391983605234532E7, 3981557.858821303),
    (-1.4456556615145957E7, 4015419.666829371)
]

# For a location in Utah, the coordinates should have:

# Latitude: between roughly 37° and 42° North
# Longitude: between roughly -114° and -109° West

# Transform coordinates
for x, y in coordinates:
    x = float(x)
    y = float(y)
    lon, lat = transformer.transform(x, y)

    print(f"Latitude: {lat}, Longitude: {lon}")

# Format for Open Elevation API
location_param = f"{lat},{lon}"
api_url = f"https://api.open-elevation.com/api/v1/lookup?locations={location_param}"
print(f"API URL: {api_url}")