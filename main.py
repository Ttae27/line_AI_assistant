import os
import uvicorn
from pathlib import Path

from dotenv import load_dotenv

from fastapi import FastAPI, Request, HTTPException, Header

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent, FileMessageContent 
from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory
from tools import TimestampedMongoDBChatMessageHistory
from langchain_core.messages import HumanMessage

from linebot.v3.messaging import (
    ApiClient, 
    MessagingApi, 
    Configuration, 
    ReplyMessageRequest, 
    TextMessage, 
    MessagingApiBlob
)

from sum_docs import summarized
from response_message import response_message
from mongo import db, fs, upload_file, get_file_data


app = FastAPI()

load_dotenv(override=True)

get_access_token = os.getenv('ACCESS_TOKEN')
configuration = Configuration(access_token=get_access_token)

get_channel_secret = os.getenv('CHANNEL_SECRET')
handler = WebhookHandler(channel_secret=get_channel_secret)

@app.post("/callback")
async def callback(request: Request, x_line_signature: str = Header(None)):
    body = await request.body()
    body_str = body.decode('utf-8')
    try:
        handler.handle(body_str, x_line_signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        raise HTTPException(status_code=400, detail="Invalid signature.")

    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event: MessageEvent):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        
        reply_message = response_message(event)
        if reply_message:
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[reply_message]
                )
            )

@handler.add(MessageEvent, message= FileMessageContent)
def handle_file(event: MessageEvent):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApiBlob(api_client)
        message_id = event.message.id

        content_response = line_bot_api.get_message_content(message_id)

        file_name = getattr(event.message, "file_name", f"{message_id}.bin")
        ext = file_name.split('.')[1]

        metadata = {"groupid": event.source.group_id, "userid": event.source.user_id, "about": summarized(content_response, ext)}
        upload_file(content_response, file_name, metadata, fs)
        chat_history = TimestampedMongoDBChatMessageHistory(
            session_id=event.source.group_id,
            connection_string="mongodb://localhost:27017/",
            database_name="historyDB_2",
            collection_name="chat"
        )
        chat_history.add_user_message(f'เซฟไฟล์ {file_name} แล้ว วันที่ {get_file_data(file_name)['uploadDate']}')

        messaging_api = MessagingApi(api_client)
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=f"save leaw")]
            )
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0")