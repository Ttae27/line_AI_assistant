from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.tools import tool
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from chromadb.api.client import SharedSystemClient
from dotenv import load_dotenv  
from service.mongo import mongo_conn
import os  
import cohere
import torch

load_dotenv()

cohere_client = cohere.Client(os.environ.get("COHERE_KEY"))

device = "cuda" if torch.cuda.is_available() else "cpu"

embed_model = HuggingFaceEmbeddings(
    model_name="BAAI/bge-m3",
    model_kwargs={"device": device},
    encode_kwargs={"normalize_embeddings": True},
)

PROMPT_TEMPLATE = """
Answer the question based only on the following context:
{context}
- -
Answer the question based on the above context: {question}
"""

@tool
def query_rag(query_text):
    """
    Retrieve documents using RAG (Retrieval-Augmented Generation)
    and generate a formatted prompt containing the most relevant content.

    Args:
        query_text (str): The user's question or search related to the documents.

    Returns:
        str: A fully formatted prompt containing top-ranked context documents and the original question.
            This prompt can be passed to an LLM for final answer generation.
    """
    db = Chroma(
        collection_name="CEcur",
        embedding_function=embed_model,
        persist_directory=f"./chroma",  
    )

    mongo = mongo_conn().rag
    result = mongo.find({"content": {"$exists": True}})

    mongo_doc = []
    for res in result:
        mongo_doc.append(Document(
            page_content=res['content']
        ))
    retriever = BM25Retriever.from_documents(mongo_doc)
    retriever.k = 2
    results_bm25 = retriever.invoke(query_text)
    results = db.similarity_search_with_relevance_scores(query_text, k=4)
    

    doc = []
    for res, _score in results:
        doc.append(res.page_content)
    for res in results_bm25:
        doc.append(res.page_content)

    response = cohere_client.rerank(
        model="rerank-v3.5",
        query=query_text,
        documents=doc,
        top_n=4,
        return_documents=True
    )

    for result in response.results:
        print('-'*100)
        print(f"* [score={result.relevance_score}]: {result.document}")

    context_text = "\n\n - -\n\n".join([str(doc.document) for doc in response.results])

    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=context_text, question=query_text)

    db._client._system.stop()
    SharedSystemClient._identifier_to_system.pop(db._client._identifier, None)
    db = None

    return prompt