import io
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from langchain_core.tools import tool
from mongo import db, fs

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'line-chat-bot-softnix-ff77b1c1d463.json'

credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

service = build('drive', 'v3', credentials=credentials)

def upload_file_drive(file: bytearray, file_name: str, about: str):
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
        }
        mimetype = 'application/' + file_name.split('.')[1]
        media = MediaIoBaseUpload(io.BytesIO(file), mimetype)
        
        file = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )

    except HttpError as error:
        print(f"An error occurred: {error}")
        file = None

    return file.get("id")

@tool
def upload_file_tool(filename: str):
    """
        Upload just one file from user query 

        Args:
        filename: name of file
    """
    data = db.files.files.find_one({"filename": filename})
    fs_id = data['_id']
    out_data = fs.get(fs_id).read()
    file_id = upload_file_drive(bytearray(out_data), filename, data['about'])
    if file_id:
        return "เซฟไฟล์เรียบร้อย"
    return 'error'

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
def show_files_tool():
    """
        โชว์ไฟล์ใน google drive ไม่ต้องให้ลิ้งค์

        return id name mimeType createdTime and description
    """
    results = service.files().list(
        q=None,
        pageSize=1000,
        fields="nextPageToken, files(id, name, mimeType, createdTime, description, properties)"
    ).execute()
    items = results.get('files', [])

    return items
    # items = []
    # for item in results.get('files', []):
    #     if item['properties']['group_id'] == group_id:
    #         items.append(item)

    # return items

@tool
def delete_file_google(file_id):
    """
        Delete file from google drive by id
    
        Args:
            file_id: string of file ID
    """
    test = service.files().delete(fileId=file_id).execute()
    print(test)

    return 'delete successfully'

def show_files():
    results = service.files().list(
        q=None,
        pageSize=1000,
        fields="nextPageToken, files(id, name, mimeType, createdTime, description)"
    ).execute()
    items = results.get('files', [])

    return items