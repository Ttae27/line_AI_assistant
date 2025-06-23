from tools.google_calendar import get_calendar_next_hour
from models.llm import llm
from langchain_core.messages import HumanMessage
from apscheduler.schedulers.background import BlockingScheduler
from main import get_access_token
import requests

def split_group(events: list):
    if events:
        split = {}
        for event in events:
            group_id = event['groupid']
            if group_id not in split.keys():
                split[group_id] = []
            event.pop('groupid')
            split[group_id].append(event)
        return split
    return None

def send_line_notification():
    events = split_group(get_calendar_next_hour())
    if events:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {get_access_token}',
        }
        for k, v in events.items():
            query = HumanMessage(content=("\n".join([
                "You are a helpful assistant.",
                "I will give you a list of events from Google Calendar.",
                "Each event includes:",
                "- summary: event title",
                "- start.dateTime: start time in ISO 8601 format",
                "- end.dateTime: end time in ISO 8601 format",
                "Your task is to generate a Thai notification message for each event in the following format:",
                "",
                "แจ้งเตือนจาก Google Calendar",
                "หัวข้อ: *[summary]*",
                "เวลา: [start time - end time] น.",
                "วันที่: [weekday DD Month YYYY]",
                "Formatting rules:",
                "- Time should be shown as HH:MM - HH:MM น.",
                "- Date should be human-readable (e.g., วันจันทร์ที่ 16 มิถุนายน 2025)",
                "- Assume all times are already in Asia/Bangkok timezone",
                "- If there are multiple events, separate each message with a line of five dashes (`-----`)",
                "Here is the list of events:"
                f"{v}"
            ])))
            result = llm.invoke([query])
            message = result.content
            payload = {
                'to': k,
                'messages': [{
                    'type': 'text',
                    'text': message,
                }]
            }
            response = requests.post('https://api.line.me/v2/bot/message/push', headers=headers, json=payload)
            print('Line sent:', response.status_code)

scheduler = BlockingScheduler()
scheduler.add_job(send_line_notification, 'interval', minutes = 15)
scheduler.start()