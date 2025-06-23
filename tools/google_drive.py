import io
import os
from typing import List, Union
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from langchain_core.tools import tool
from dotenv import load_dotenv
from service.mongo import db, fs

load_dotenv(override=True)
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')

credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

service = build('drive', 'v3', credentials=credentials)

def upload_file_drive(file: bytearray, file_name: str, about: str, group_id):
    try:
        file_metadata = {
            "name": file_name,
            "description": about,
            "properties": {
                "group_id": group_id
            }
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
def upload_file_tool(filename: Union[str, List[str]], group_id: str):
    """
    Upload one or more files from MongoDB to Google Drive using the given group_id.

    Args:
        filename (Union[str, List[str]]): A single file name or list of file names to upload.
        group_id (str): Group identifier for organizing the files.

    Returns:
        List[str]: Upload result messages for each file.

    Note:
        - Always pass all filenames in a single tool call.
    """
    if isinstance(filename, str):
        filename = [filename]
    result = []
    for fname in filename:
        try:
            data = db.files.files.find_one({"filename": fname})
            fs_id = data['_id']
            out_data = fs.get(fs_id).read()
            upload_file_drive(bytearray(out_data), fname, data['about'], group_id)
            result.append(f"Successfully upload file: {fname}")
        except Exception as e:
            result.append(f"Failure to upload file: {fname} - {e}")
    print("result of upload file: ", result)
    return result


@tool
def sharing_file_google(file_id: List[str]):
    """
    Share a Google Drive file with public view access.

    ภาษาไทย: ใช้สำหรับแชร์ลิ้งก์ไฟล์ Google Drive ให้คนอื่นดูได้ (read-only)
    ผู้ใช้มักจะพิมพ์ว่า 'ขอลิ้ง', 'ขอ link', 'แชร์ไฟล์'

    Args:
        file_id (str): ไอดีของไฟล์ที่ต้องการแชร์

    Returns:
        str: ลิ้งก์สำหรับเปิดดูไฟล์บน Google Drive
    """
    request_body = {
        'role': 'reader',
        'type': 'anyone'
    }
    link = []
    
    for f_id in file_id:
        service.permissions().create(
            fileId=f_id,
            body=request_body
        ).execute()
        
        response_share_link = service.files().get(
            fileId=f_id,
            fields='webViewLink'
        ).execute()
        link.append(response_share_link['webViewLink'])

    return link

@tool
def delete_file_google(file_id: List[str]):
    """
    Permanently deletes one or more files from Google Drive by their file ID(s).

    Args:
        file_ids List[str]:  list of file IDs. (NOT file names!)

    Returns:
        List[str]: Summary of success/failure for each file.
    """
    result = []
    for f_id in file_id:
        try:
            service.files().delete(fileId=f_id).execute()
            result.append(f"Succesfully delete: {f_id}")
        except Exception as e:
            result.append(f"Failure to delete: {f_id} - {e}")
    
    return result

@tool
def show_files(group_id):
    """
    Retrieve a list of files from Google Drive that match the specified group ID.
    
    Args:
        group_id (str): The group identifier used to filter files stored in Google Drive.
                        Only files with a matching 'group_id' in their custom properties will be returned.
    """
    results = service.files().list(
        q=None,
        pageSize=1000,
        fields="nextPageToken, files(id, name, mimeType, createdTime, description, properties)"
    ).execute()
    items = []
    for item in results.get('files', []):
        if item['properties']['group_id'] == group_id:
            items.append(item)

    return items
