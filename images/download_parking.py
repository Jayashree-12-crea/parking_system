import urllib.request
import os

os.makedirs('images', exist_ok=True)

url = "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/Car_park.jpg/1280px-Car_park.jpg"

print("Downloading parking lot image...")
urllib.request.urlretrieve(url, 'images/parking.jpg')
print("Done! Saved to images/parking.jpg")