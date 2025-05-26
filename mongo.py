from pymongo import MongoClient
import gridfs

conn_string = "mongodb://localhost:27017/"

def mongo_conn():
    try:
        conn = MongoClient(conn_string)
        return conn.historyDB_2
    except Exception as err:
        print(f"Error in connection : {err}")

def get_files_data():
    query = db.files.files.find()
    files_data = []
    for file_data in query:
        files_data.append(file_data)
    return files_data

def get_file_data(filename):
    query = db.files.files.find_one({"filename": filename})

    return query

def upload_file(file: bytearray, file_name: str, metadata: dict):
    fs.put(file, filename=file_name, **metadata)

db = mongo_conn()

fs = gridfs.GridFS(db, collection='files')