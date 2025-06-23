from mistralai import Mistral
from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chains.summarize import load_summarize_chain
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from chromadb.api.client import SharedSystemClient
from service.mongo import mongo_conn
from models.llm import llm
from dotenv import load_dotenv
import torch
import shutil
import base64
import os

load_dotenv()
MISTRAL_API_KEY = os.getenv('MISTRAL_KEY')

def encode_byte(file):
    try:
        return base64.b64encode(file).decode('utf-8')
    except:
        return None

def pdf_to_markdown_MistralOCR(file_data) -> str:
    client = Mistral(api_key=MISTRAL_API_KEY)
    base64_pdf = encode_byte(file_data)
    ocr_response = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": f"data:application/pdf;base64,{base64_pdf}" 
        },
        include_image_base64=True
    )
    all_page = [page.markdown for page in ocr_response.pages]
    return  all_page

def to_document(markdowns: list[str]):
    docs = []
    for i, md in enumerate(markdowns):
        docs.append(Document(
            page_content=md,
            page=i+1
        ))
    return docs

def split_text(documents: list[Document]):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,  
        chunk_overlap=100, 
        length_function=len,
    )
    print(f"text splitter: {text_splitter}")

    chunks = text_splitter.split_documents(documents)
    print(f"Split {len(documents)} documents into {len(chunks)} chunks.")

    return chunks  

def embeded_to_chroma(file_data):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    try:
        embed_model = HuggingFaceEmbeddings(
            model_name="BAAI/bge-m3",
            model_kwargs={"device": device},
            encode_kwargs={"normalize_embeddings": True},
        )

        if os.path.exists('./chroma'):
            shutil.rmtree('./chroma')
        vector_store = Chroma(
                collection_name="CEcur",
                embedding_function=embed_model,
                persist_directory=f"./chroma", 
        )
        markdown = pdf_to_markdown_MistralOCR(file_data)
        docs = to_document(markdown) 
        split = split_text(docs)

        split_mongo = []
        for s in split:
            split_mongo.append({"content": s.page_content})
        mongo = mongo_conn()
        mongo_rag = mongo.rag
        mongo_rag.delete_many({})
        mongo_rag.insert_many(split_mongo)

        chain = load_summarize_chain(llm, chain_type="map_reduce")
        summary = chain.invoke(split)
        query = f"You are an expert document summarizer.\nSummarize the following text into 1–2 sentences. Focus only on the core ideas and important concepts.\n[Start of text]\n{summary}\n[End of text]\n Summary: "
        sumarize = llm.invoke([HumanMessage(query)])
        mongo_rag.insert_one({'summarize': sumarize.content})

        vector_store.add_documents(split)
        vector_store._client._system.stop()
        SharedSystemClient._identifier_to_system.pop(vector_store._client._identifier, None)
        vector_store = None
        return 'Successfully embeded'
    except Exception as e:
        return f'Failed to embeded: {e}'

def get_summary():
    client = mongo_conn().rag
    result = client.find_one({ "summarize" : { "$exists" : True } })
    if result:
        return result['summarize']
    return 'No Data in RAG'