from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

class TimestampedMongoDBChatMessageHistory(MongoDBChatMessageHistory):
    def __init__(self, session_id):
        super().__init__(connection_string=os.getenv('MONGODB_CONN_STRING'), session_id=session_id, database_name='historyDB_2', collection_name='chat')
        self.session_id = session_id

    def add_user_message(self, message: str):
        self.collection.insert_one({
            "session_id": self.session_id,
            "type": "human",
            "content": message,
            "created_at": datetime.now(timezone(timedelta(hours = 7))).isoformat()
        })

    def add_ai_message(self, message: str):
        self.collection.insert_one({
            "session_id": self.session_id,
            "type": "ai",
            "content":  message,
            "created_at": datetime.now(timezone(timedelta(hours = 7))).isoformat()
        })

    def get_history(self):
        return self.collection.find({"session_id": self.session_id})