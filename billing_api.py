from flask import Flask, jsonify
from flask_cors import CORS  # Import the CORS package
import pymongo
from bson.json_util import dumps

app = Flask(__name__)
CORS(app, origins=["http://localhost:5500"])


# MongoDB connection code
client = pymongo.MongoClient('mongodb://localhost:27017/')
db = client['billing_db']
collection = db['bill_items']

@app.route('/get_bill', methods=['GET'])
def get_bill():
    try:
        bill_items = list(collection.find())
        return dumps(bill_items)  # Use bson.json_util.dumps to serialize ObjectId
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(debug=True)
