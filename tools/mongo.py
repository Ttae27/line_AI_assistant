from service.mongo import db
from langchain_core.tools import tool

@tool
def get_files_data_tool(group_id):
    """
    Retrieve file metadata from the database for a specific group ID.

    Args:
        group_id (str): The group identifier used to filter files stored in the database.
    """
    query = db.files.files.find({"groupid": group_id})
    files_data = []
    for file_data in query:
        files_data.append(file_data)
    return files_data