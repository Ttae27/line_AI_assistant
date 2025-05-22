from linebot.v3.messaging import TextMessage
from tools import call_langchain_with_history, save_conversation

def response_message(event):
    request_message = event.message.text
    group_id, user_id = event.source.group_id, event.source.user_id

    if "casper" in request_message or "Casper" in request_message or "แคสเปอร์" in request_message:
        result = call_langchain_with_history(request_message, group_id, user_id)
        return TextMessage(text=result)
    else:
        save_conversation(request_message, group_id)
        return None



