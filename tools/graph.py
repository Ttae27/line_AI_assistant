from typing import TypedDict, List, Union, Sequence, Annotated
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from models.mongo import TimestampedMongoDBChatMessageHistory
from models.llm import llm
from tools.google_drive import sharing_file_google, upload_file_tool, delete_file_google, show_files
from tools.google_calendar import get_calendar_event, create_calendar_event, delete_calendar_event
from tools.mongo import get_files_data_tool
from rag.query_rag import query_rag
from rag.embeded import get_summary

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    query: str
    group_id: str
    history_message: List[Union[HumanMessage, AIMessage]]
    chat_history: TimestampedMongoDBChatMessageHistory

tools = [sharing_file_google, upload_file_tool, delete_file_google, show_files, get_files_data_tool, get_calendar_event, create_calendar_event, delete_calendar_event, query_rag]
llm_with_tools = llm.bind_tools(tools)

def load_history(state: AgentState) -> AgentState:
    chat_history = TimestampedMongoDBChatMessageHistory(state['group_id'])

    history_messages = []
    if chat_history.get_history():
        for msg in chat_history.get_history():
            if msg['type'] == 'human':
                history_messages.append(HumanMessage(content=f'[history] at time {msg['created_at']} by user: {msg['content']}'))
            elif msg['type'] == 'ai':
                history_messages.append(AIMessage(content=f'[history] at time {msg['created_at']} by ai: {msg['content']}'))
            else:
                continue
    user_msg = HumanMessage(content="[current] by user: " + state['query'])
    state['messages'] = [user_msg]
    state['history_message'] = history_messages
    state['chat_history'] = chat_history
    return state

def agent(state: AgentState) -> AgentState:
    system_msg = SystemMessage(content=(
    f"Your name is Casper (in Thai they call you 'แคสเปอร์'). You are a helpful assistant.\n\n"

    "[Usage Instruction]\n"
    "- You will see past messages labeled as [history]. Focus only on the message labeled [current] to determine your response.\n"
    "- Do NOT perform any tool calls unless the [current] message clearly requests an action such as: `upload`, `delete`, `share`, or `list` files.\n"
    f"- For tool calls that require a `group_id`, always use this default group_id: {state['group_id']}\n"
    "- When uploading files (e.g., 'ฝากไฟล์', 'อัปโหลด', 'upload this'), you MUST first call `get_files_data_tool(group_id)` to fetch file metadata.\n"
    "- Then call `upload_file_tool`, passing ALL file names in one list. Do NOT split into multiple calls.\n"
    "- When sharing or deleting files, you MUST first call `show_files(group_id)` to get the latest Drive file metadata before proceeding.\n"
    "- When the user requests file deletion (e.g., 'ลบไฟล์', 'delete this file', 'remove this'), you MUST follow these steps:\n \
    1. Call `show_files(group_id)` to list files and match the name. \n \
    2. Respond with the matched file(s) and ask the user to confirm exactly which file(s) to delete.\n \
    3. DO NOT call `delete_file_tool` unless the user replies with clear and specific confirmation (e.g., 'yes, delete [filename]').\n"
    "- When users ask to view files (e.g., 'list files', 'show all files'), call `show_files(group_id)` only.\n"
    "- When a user asks to share a file or request a link (e.g., 'ขอลิ้งไฟล์นี้หน่อย', 'ขอแชร์ไฟล์', 'ขอ link', 'แชร์ไฟล์นี้ให้หน่อย'), call `show_files(group_id)` first to fetch the file list, then match the user’s target file name.\n"
    "- If a matching file is found, call `sharing_file_google_tool([file_id])` with that file’s ID.\n"
    "- NEVER mention MongoDB, databases, or internal systems in your response — focus only on user-facing actions and Google Drive.\n"
    "- If the user asks a general question (not related to uploading, deleting, listing, or sharing files), just respond naturally and do NOT call any tools.\n"
    "- When the user asks to see a schedule, calendar, meeting time, or timetable (e.g., 'what's my schedule', 'show my calendar', 'มีประชุมเมื่อไหร่'), call `get_calendar_event_tool(group_id)` using the default group_id.\n"
    "- Respond naturally based on the returned event list. If no events are found, say 'No events found for your group.'\n"
    "- When the user wants to add or create an event (e.g., 'add meeting', 'create appointment'), call `create_calendar_event_tool` with the required event details and the default group_id.\n"
    "- When the user asks to delete a calendar event (e.g., 'ลบการนัดหมาย', 'cancel meeting', 'delete event'), you MUST first call `get_calendar_event_tool(group_id)` to retrieve event metadata.\n"
    "- After showing a list of upcoming events with their id, names and times, ask the user to confirm which one to delete.\n"
    "- Only after clear confirmation and a matching event is selected, first call `get_calendar_event_tool(group_id)` to retrieve event metadata then call `delete_calendar_event_tool(event_id)` using the correct `id`.\n"
    "- When the user asks anything relate to this context:\n"
    f"{get_summary()}" 
    "If No Data in RAG don't call `query_rag_tool(query_text)`\n"
    "call `query_rag_tool(query_text)` to retrieve the most relevant information and respond naturally based on the result.\n"

    "[Response Rules]\n"
    "- For uploads, acknowledge each file individually: 'Successfully uploaded X', 'Failed to upload Y'.\n"
    "- For share requests, include the file name and summary (from its description).\n"
    "- If the current message requests file deletion, do not act immediately. First list the file(s) the user wants to delete, explain that deletion is irreversible, and explicitly ask the user to confirm."
    "- If a file name is not found in the metadata from `show_files`, politely inform the user.\n"
    "- Do not infer or reuse data from history. Always get fresh metadata using the tools.\n"
    "- When listing calendar events, include event name, date/time, and any description if available.\n"
    "- If no events are returned, respond with a polite message indicating no scheduled events.\n"
    "- When an event is successfully created, confirm with a message like: 'Your event has been added to the calendar.' Optionally include the summary and time.\n"
    "- When an event is successfully deleted, confirm with a message like: 'The event has been removed from the calendar.'"

))
    
    messages = [system_msg] + state['history_message'] + state['messages']
    ai_message = llm_with_tools.invoke(messages)
    state['messages'].append(ai_message)

    return state

def update_history(state: AgentState) -> AgentState:
    state["chat_history"].add_user_message(state["query"])
    state["chat_history"].add_ai_message(state["messages"][-1].content)

    return state

def should_continue(state: AgentState):
    message = state["messages"][-1]
    
    if not message.tool_calls:
        print("Content: ", state["messages"][-2].content)
        return "end"
    else:
        print("Content: ", state["messages"][-2].content)
        print("Tools: ", message.tool_calls)
        print("-"*100)
        return "continue"

def call_tool(state: AgentState):
    tools_by_name = {tool.name: tool for tool in tools}
    for tool_call in state["messages"][-1].tool_calls:
        tool = tools_by_name[tool_call["name"]]
        result = tool.invoke(tool_call["args"]) 

        state["messages"].append(ToolMessage(
            content=str(result),
            tool_call_id=tool_call["id"],
            name=tool_call["name"]
        ))

    return state

graph = StateGraph(AgentState)

graph.add_node("load_history", load_history)
graph.add_node("agent", agent)
graph.add_node("update_history", update_history)
graph.add_node("tools", call_tool)

graph.add_edge(START, "load_history")
graph.add_edge("load_history", "agent")
graph.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "tools",
        "end": "update_history"
    }
)
graph.add_edge("tools", "agent")
graph.add_edge("update_history", END)

def run_graph(query: str, group_id: str):
    app = graph.compile()
    result = app.invoke({"query": query, "group_id": group_id})

    return result['messages'][-1].content
