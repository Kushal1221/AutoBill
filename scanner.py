import cv2
from pyzbar.pyzbar import decode
from pymongo import MongoClient
import datetime
import time
from flask import Flask, jsonify
from threading import Thread
import requests  # Import requests to make HTTP calls to the frontend

# MongoDB Configuration
try:
    client = MongoClient("mongodb://localhost:27017/")  # MongoDB connection
    db = client.shopping  # Database name
    collection = db.bills  # Collection name
    print("Connected to MongoDB successfully!")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    exit()

# Items and Pricing
items = {
    "SWCFP100106264": {"name": "Watch", "price": 4000},
    "SFQDYRHXVGWTJ": {"name": "Apple Pencil", "price": 8000},
    "9780241470046": {"name": "The Practice", "price": 500},
    "9781847941831": {"name": "Atomic Habits", "price": 500},
    "8904304526001": {"name": "Book", "price": 50},
    "8904336805655": {"name": "Junction Box", "price": 500},
    "9788194944447": {"name": "iPad", "price": 10000},
}

# Initialize bill
total_bill = 0
bill = []
recently_scanned = {}  # Dictionary to track recently scanned barcodes
scan_cooldown = 60  # Cooldown period in seconds

# Replace with your IP webcam URL or local camera index
ip_webcam_url = "http://192.168.1.4:8080/video"

# Initialize Flask app
app = Flask(__name__)

@app.route('/get_bill', methods=['GET'])
def get_bill():
    """API to fetch the latest bill from MongoDB."""
    try:
        latest_bill = collection.find_one({}, sort=[('date', -1)])  # Fetch the most recent bill
        if latest_bill:
            return jsonify(latest_bill)
        else:
            return jsonify({"items": [], "total": 0})
    except Exception as e:
        return jsonify({"error": str(e)})

def process_barcode(barcode_data):
    """
    Processes a scanned barcode, updates the bill, and saves to MongoDB.
    """
    global total_bill, bill
    current_time = time.time()

    # Skip barcode if recently scanned
    if barcode_data in recently_scanned and current_time - recently_scanned[barcode_data] < scan_cooldown:
        print(f"Skipped: {barcode_data} (scanned too recently)")
        return

    recently_scanned[barcode_data] = current_time  # Update the last scan time

    if barcode_data in items:
        item = items[barcode_data]
        print(f"Scanned: {item['name']} | Price: Rs. {item['price']}")
        total_bill += item['price']
        bill.append({"name": item['name'], "price": item['price']})

        # Update MongoDB with the current bill
        bill_document = {
            "date": datetime.datetime.now(),
            "items": bill,
            "total": total_bill
        }
        try:
            # Upsert the document to keep the latest bill
            collection.update_one(
                {},  # Match any document (we assume only one bill is stored at a time)
                {"$set": bill_document},
                upsert=True  # Insert if no document exists
            )
            print("Bill updated in MongoDB.")
        except Exception as e:
            print(f"Error updating bill in MongoDB: {e}")

        # Trigger frontend update (to fetch the latest bill)
        try:
            response = requests.get("http://localhost:5000/get_bill")
            if response.status_code == 200:
                print("Frontend bill updated successfully.")
            else:
                print("Error: Could not notify frontend.")
        except Exception as e:
            print(f"Error notifying frontend: {e}")

    else:
        print(f"Unknown Item: {barcode_data}")

def start_flask():
    """Function to run the Flask app in a separate thread."""
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    # Start Flask API in a separate thread so it doesn't block barcode scanning
    flask_thread = Thread(target=start_flask)
    flask_thread.start()

    # Open the webcam feed
    cap = cv2.VideoCapture(ip_webcam_url)
    if not cap.isOpened():
        print("Error: Could not access the phone's camera or webcam.")
        exit()

    print("Scanning started. Point the barcode at the camera. Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            print("Error: Failed to read from the camera feed.")
            continue

        try:
            barcodes = decode(frame)
        except Exception as e:
            print(f"Decoding Error: {e}")
            continue

        for barcode in barcodes:
            barcode_data = barcode.data.decode('utf-8')  # Decode the barcode data
            process_barcode(barcode_data)

        # Display the frame with detected barcodes
        cv2.imshow("Barcode Scanner", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Exiting the application.")
            cap.release()
            cv2.destroyAllWindows()
            break
