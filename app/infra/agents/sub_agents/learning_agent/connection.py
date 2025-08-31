from pymongo import MongoClient
from dotenv import load_dotenv
import os
from google import genai
from google.genai import types


load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def connect_to_mongo() -> MongoClient:
    """
    Kết nối đến MongoDB
    """
    client = MongoClient(os.getenv("MONGO_URI_LEARNING"))
    return client


mongo_client = connect_to_mongo()

