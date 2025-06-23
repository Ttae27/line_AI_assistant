from linebot.v3.messaging import TextMessage
from tools.graph import run_graph
from service.mongo import save_conversation

def response_message(event):
    request_message = event.message.text
    group_id = event.source.group_id

    if "casper" in request_message or "Casper" in request_message or "แคสเปอร์" in request_message:
        result = run_graph(request_message, group_id)
        return TextMessage(text=result)
    else:
        save_conversation(request_message, group_id)
        return None