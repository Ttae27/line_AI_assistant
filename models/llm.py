from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import os

load_dotenv()

llm = ChatOpenAI(
    base_url=os.environ.get("OPENAI_BASE_URL"),
    model='gpt-4o-mini',
    api_key=os.environ["OPENAI_API_KEY"],
    temperature=0
)