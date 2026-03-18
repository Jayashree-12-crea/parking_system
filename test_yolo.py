from ultralytics import YOLO
import urllib.request
import os

os.makedirs('images', exist_ok=True)

print("Downloading test image...")
urllib.request.urlretrieve(
    'https://ultralytics.com/images/bus.jpg',
    'images/test.jpg'
)
print("Downloaded!")

model = YOLO('yolov8s.pt')
results = model('images/test.jpg', conf=0.35, verbose=False)
vehicles = [b for b in results[0].boxes if int(b.cls[0]) in {2, 5, 7}]
print(f'Detected {len(vehicles)} vehicles in test image')