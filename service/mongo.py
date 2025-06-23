from pymongo import MongoClient
from dotenv import load_dotenv
from models.mongo import TimestampedMongoDBChatMessageHistory
import gridfs
import os

load_dotenv(override=True)
conn_string = os.getenv('MONGODB_CONN_STRING')

def mongo_conn():
    try:
        conn = MongoClient(conn_string)
        return conn.historyDB_2
    except Exception as err:
        print(f"Error in connection : {err}")

def get_files_data(group_id):
    query = db.files.files.find({"groupid": group_id})
    files_data = []
    for file_data in query:
        files_data.append(file_data)
    return files_data

def upload_file(file: bytearray, file_name: str, metadata: dict):
    fs.put(file, filename=file_name, **metadata)

def save_conversation(query, group_id):
    chat_history = TimestampedMongoDBChatMessageHistory(session_id=group_id)
    chat_history.add_user_message(query)

db = mongo_conn()

fs = gridfs.GridFS(db, collection='files')
