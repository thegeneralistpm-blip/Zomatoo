import requests
try:
    print("Connecting to http://127.0.0.1:5000/api/metadata ...")
    r = requests.get('http://127.0.0.1:5000/api/metadata', timeout=5)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"Locations count: {len(data.get('locations', []))}")
        print(f"Cuisines count: {len(data.get('cuisines', []))}")
    else:
        print(f"Response: {r.text}")
except Exception as e:
    print(f"Error: {e}")
