import os
import base64
import io
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from langchain_core.tools import tool

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'line-chat-bot-softnix-ff77b1c1d463.json'

credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

service = build('drive', 'v3', credentials=credentials)

def get_file_id():
    pass

def to_bytes(path): 
    with open(path, 'rb') as file: 
        byte_array = file.read() 
    return byte_array 

def upload_file_drive(file: bytearray, file_name: str, about: str, session_id: str, user_id: str):
    """Upload file 

    Args:
        file: bytearray of file
        file_name: string of file name 
        about: string of summarized of this file 
    """
    try:
        file_metadata = {
            "name": file_name,
            "description": about,
            "properties": {
                "sesion_id": session_id,
                "user_id": user_id
            }
        }
        mimetype = 'application/' + file_name.split('.')[1]
        # print(mimetype)
        media = MediaIoBaseUpload(io.BytesIO(file), mimetype)
        
        file = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        # print(f'File ID: {file.get("id")}')

    except HttpError as error:
        print(f"An error occurred: {error}")
        file = None

    return file.get("id")

@tool
def sharing_file_google(file_id: str):
    """ให้ลิ้งของไฟล์เมื่อขอลิ้ง

    Args:
        file_id: string of file ID
    """
    request_body = {
    'role': 'reader',
    'type': 'anyone'
    }

    service.permissions().create(
        fileId=file_id,
        body=request_body
    ).execute()

    response_share_link = service.files().get(
        fileId=file_id,
        fields='webViewLink'
    ).execute()
    return response_share_link ['webViewLink']

@tool
def show_files_tool(session_id):
    """
        โชว์ไฟล์ใน google drive

        return id name mimeType createdTime and description
    """
    results = service.files().list(
        # q=f"'{parent_folder_id}' in parents and trashed=false" if parent_folder_id else None,
        q=None,
        pageSize=1000,
        fields="nextPageToken, files(id, name, mimeType, createdTime, description, properties)"
    ).execute()
    items = []
    for item in results.get('files', []):
        if item['properties']['group_id'] == session_id:
            items.append(item)

    return items

@tool
def delete_file_google(file_id):
    """
        Delete file from google drive by id
    
        Args:
            file_id: string of file ID
    """
    service.files().delete(fileId=file_id).execute()

    return 'delete successfully'

def show_files(parent_folder_id=None):
    results = service.files().list(
        # q=f"'{parent_folder_id}' in parents and trashed=false" if parent_folder_id else None,
        q=None,
        pageSize=1000,
        fields="nextPageToken, files(id, name, mimeType, createdTime, description)"
    ).execute()
    items = results.get('files', [])

    return items

def update_file():
    pass

# sharing_file('1HlhOqPjWv5oEx82YZHmNkFaoVWJG5Xkg')
# a = show_files()
# print(a)

# upload_file(to_bytes('received_files/Security Law.docx'), 'Security Law.docx', 'test')

# delete_file('1JaNU5rwWEKdjx43xOPQjP3t0n-PGss2K')
