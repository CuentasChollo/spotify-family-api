import random
import os
from opencage.geocoder import OpenCageGeocode
import googlemaps

# Initialize the geocoders
opencage_key = os.environ.get('OPENCAGE_KEY')
opencage_geocoder = OpenCageGeocode(opencage_key)

gmaps_key = os.environ.get('GMAPS_KEY')
gmaps = googlemaps.Client(key=gmaps_key)

def get_random_address():
    # Define a bounding box for Sydney
    bbox = (-33.929865, 150.877718, -33.653675, 151.300455)
    
    lat = random.uniform(bbox[0], bbox[2])
    lng = random.uniform(bbox[1], bbox[3])
    
    # Reverse geocode to get an address
    results = opencage_geocoder.reverse_geocode(lat, lng)
    
    if results and len(results):
        return results[0]['formatted']
    return None

def get_place_id(address):
    # Use Google's Places API to get the Place ID
    result = gmaps.find_place(address, 'textquery')
    
    if result['candidates']:
        return result['candidates'][0]['place_id']
    return None

# Generate a random address and get its Place ID
address = get_random_address()
if address:
    place_id = get_place_id(address)
    print(f"Address: {address}")
    print(f"Place ID: {place_id}")
else:
    print("Failed to generate a valid address")