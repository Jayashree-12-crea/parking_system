import urllib.request
import os

os.makedirs('images', exist_ok=True)

# Add browser header to avoid 403 blocked error
opener = urllib.request.build_opener()
opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
urllib.request.install_opener(opener)

urls = [
    "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/Car_park.jpg/1280px-Car_park.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Parking_lot_-_The_Rideau_Carleton_Raceway%2C_Ottawa%2C_ON.jpg/1280px-Parking_lot_-_The_Rideau_Carleton_Raceway%2C_Ottawa%2C_ON.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/9/9c/Goldengate-Bridge_parking.jpg",
]

downloaded = False
for i, url in enumerate(urls):
    try:
        print(f"Trying URL {i+1}...")
        urllib.request.urlretrieve(url, 'images/parking.jpg')
        print(f"✅ Downloaded successfully!")
        downloaded = True
        break
    except Exception as e:
        print(f"❌ Failed: {e}")

if not downloaded:
    print("\n⚠️  All URLs failed.")
    print("Please manually download any parking lot image")
    print("and save it as:  images/parking.jpg")