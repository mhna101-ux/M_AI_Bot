import os
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

def get_chroma_store() -> Chroma:
    # Directory for persistent storage
    persist_directory = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")
    
    # Use standard HuggingFace local sentence transformer embeddings
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # Create or load the persistent Chroma DB vector store directly
    vectorstore = Chroma(
        collection_name="m_ai_memory",
        embedding_function=embeddings,
        persist_directory=persist_directory
    )
    
    return vectorstore
