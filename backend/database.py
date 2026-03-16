import os
from pymongo import MongoClient

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://localhost:27017/pythonapp"
)

client = MongoClient(MONGO_URI)
db = client.get_database()

users_collection = db["users"]
tasks_collection = db["tasks"]