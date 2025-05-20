import os
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from dotenv import load_dotenv
from google_drive import show_files, sharing_file_google, delete_file_google, show_files_tool
from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory
from mongo import get_files_data, download_file
from datetime import datetime, timezone

class TimestampedMongoDBChatMessageHistory(MongoDBChatMessageHistory):
    def add_user_message(self, message: str):
        self.collection.insert_one({
            "session_id": self.session_id,
            "type": "human",
            "content": message,
            "created_at": datetime.now(timezone.utc)
        })

    def add_ai_message(self, message: str):
        self.collection.insert_one({
            "session_id": self.session_id,
            "type": "ai",
            "content":  message,
            "created_at": datetime.now(timezone.utc)
        })

    def get_history(self):
        return self.collection.find()


load_dotenv()

llm = ChatOpenAI(
    base_url=os.environ.get("OPENAI_BASE_URL"),
    model='gpt-4o-mini',
    api_key=os.environ["OPENAI_API_KEY"],
    temperature=0
)

@tool
def upload_file(query, session_id):
    """
        Upload file from MongoDB to Google drive 

        Args:
            query: string of user query
            session_id: session_id
    """
    upload_tools = [download_file]
    llm_with_upload_tools = llm.bind_tools(upload_tools)

    file_data = get_files_data()
    messages = [HumanMessage(query + ' this is a list of metadata of file' + str(file_data))]
    # print(messages)
    ai_message =  llm_with_upload_tools.invoke(messages)
    # print(ai_message.tool_calls)
    messages.append(ai_message)

    if ai_message.tool_calls:
        selected_tool = download_file
        # print('selected call --------> ',  selected_tool)
        tool_msg = selected_tool.invoke(ai_message.tool_calls[-1])
        # print('tool msg --------> ', tool_msg.content)
        return tool_msg
        # result = llm_with_upload_tools.invoke(messages)
        # print(result)

@tool
def delete_file(query, session_id):
    """
        ลบไฟล์ใน google drive 

        Args:
            query: คำสั่งจากผู้ใช้ เช่น "ลบไฟล์ล่าสุด"
            session_id: session_id
    """
    delete_tools = [delete_file_google]
    llm_with_delete_tools = llm.bind_tools(delete_tools)

    file_data = show_files()
    messages = [HumanMessage(query + ' this is a list of metadata of file' + str(file_data))]
    # print(messages)
    ai_message =  llm_with_delete_tools.invoke(messages)
    # print("ai_message "+ai_message.tool_calls)
    # messages.append(ai_message)
    tool_message = []

    if ai_message.tool_calls:
        for tool_call in ai_message.tool_calls:
            tool_name = tool_call['name'].lower()
            selected_tool = {
                # "sharing_file": sharing_file,
                "delete_file_google": delete_file_google
            }.get(tool_name)
            # print('selected call --------> ',  selected_tool)
            tool_msg = selected_tool.invoke(tool_call)
            
            tool_message.append(tool_msg)
            # messages.append(tool_msg)
            print('tool msg --------> ', tool_msg.content)
        return tool_message

@tool
def sharing_file(query, session_id):
    """
        ให้ลิ้งของไฟล์เมื่อขอลิ้งใน google drive 

        Args:
            query: คำสั่งจากผู้ใช้ เช่น "ขอลิ้งไฟล์ล่าสุด"
            session_id: session_id
    """
    sharing_tools = [sharing_file_google]
    llm_with_sharing_tools = llm.bind_tools(sharing_tools)

    file_data = show_files()
    messages = [HumanMessage(query + ' this is a list of metadata of file' + str(file_data))]
    ai_message =  llm_with_sharing_tools.invoke(messages)
    tool_message = []

    if ai_message.tool_calls:
        for tool_call in ai_message.tool_calls:
            tool_name = tool_call['name'].lower()
            selected_tool = {
                "sharing_file_google": sharing_file_google
            }.get(tool_name)
            # print('selected call --------> ',  selected_tool)
            tool_msg = selected_tool.invoke(tool_call)
            
            tool_message.append(tool_msg)
            # messages.append(tool_msg)
            print('tool msg --------> ', tool_msg.content)
        return tool_message

def call_langchain_with_history(query, session_id):
    main_tools = [show_files_tool, delete_file, upload_file, sharing_file]
    llm_with_tools = llm.bind_tools(main_tools)

    chat_history = TimestampedMongoDBChatMessageHistory(
        session_id=session_id,
        connection_string="mongodb://localhost:27017/",
        database_name="historyDB_2",
        collection_name="chat"
    )

    history_message = []
    if chat_history.get_history():
        for msg in chat_history.get_history():
            if msg['type'] == 'human':
                history_message.append(HumanMessage(content=f'[history] at time {msg['created_at']} by user: {msg['content']}'))
            elif msg['type'] == 'ai':
                history_message.append(AIMessage(content=f'[history] at time {msg['created_at']} by ai: {msg['content']}'))
            else:
                continue

    system_msg = SystemMessage(content=(
            "You are a helpful assistant. You will see past messages labeled as [history]. "
            "Focus only on the message labeled [current] to determine your response. "
            "Do NOT perform tool calls unless the [current] message clearly requests an action like upload, delete, or list files." 
            "If tool calls have parameter session_id use this: " + session_id
        ))

    user_msg = HumanMessage(content="[current] by user: " + query)
    messages = [system_msg] + history_message + [user_msg]
    chat_history.add_user_message(query)

    ai_message = llm_with_tools.invoke(messages)
    messages.append(ai_message)

    if ai_message.tool_calls:
        for tool_call in ai_message.tool_calls:
            print(tool_call)
            tool_name = tool_call["name"].lower()
            selected_tool = {
                "show_files_tool": show_files_tool,
                "delete_file": delete_file,
                "upload_file": upload_file,
                "sharing_file": sharing_file
            }.get(tool_name)

            if selected_tool:
                tool_response = selected_tool.invoke(tool_call)
                tool_msg = ToolMessage(
                    tool_call_id=tool_call["id"],
                    content=str(tool_response)
                )
                messages.append(tool_msg)
        final_response = llm_with_tools.invoke(messages)
        messages.append(final_response)
        chat_history.add_ai_message(final_response.content)
        return final_response.content
    
    chat_history.add_ai_message(ai_message.content)
    return ai_message.content


# result = call_langchain_with_history('ดูไฟล์ใน google drive', "Cdb64c7273beeb53116ca68976a25209fU0b41d104a18791af412f0e36fbdb084a")
# result = call_langchain('ขอดูไฟล์ใน google drive บอก id ด้วย')
# upload_file('อัพโหลดไฟล์อันล่าสุด', "Cdb64c7273beeb53116ca68976a25209fU0b41d104a18791af412f0e36fbdb084a")
# print(result)