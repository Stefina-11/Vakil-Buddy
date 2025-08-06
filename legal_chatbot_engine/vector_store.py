from langchain.vectorstores import Chroma
from langchain.embeddings import SentenceTransformerEmbeddings
from typing import List
import os
from config import CHROMA_DB_DIR, EMBEDDING_MODEL_NAME, DOCUMENTS_DIR

def get_embedding_function():
    """
    Initializes and returns the Sentence Transformer embedding function,
    using the model name from configuration.
    """
    return SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL_NAME)

def create_vector_store(chunks: List[str]):
    """
    Creates a new ChromaDB vector store from a list of text chunks.
    If the directory exists, it will be overwritten.
    """
    # Ensure the directory exists
    os.makedirs(CHROMA_DB_DIR, exist_ok=True)

    embeddings = get_embedding_function()
    print(f"Creating ChromaDB at {CHROMA_DB_DIR} with {len(chunks)} chunks using {EMBEDDING_MODEL_NAME}.")
    db = Chroma.from_texts(
        texts=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DB_DIR
    )
    db.persist()
    print("ChromaDB created and persisted successfully.")
    return db

def load_vector_store():
    """
    Loads an existing ChromaDB vector store.
    """
    if not os.path.exists(CHROMA_DB_DIR):
        print(f"ChromaDB directory not found at {CHROMA_DB_DIR}. Please create the vector store first.")
        return None
    
    embeddings = get_embedding_function()
    print(f"Loading ChromaDB from {CHROMA_DB_DIR}.")
    db = Chroma(
        persist_directory=CHROMA_DB_DIR,
        embedding_function=embeddings
    )
    print("ChromaDB loaded successfully.")
    return db

if __name__ == "__main__":
    # Example usage:
    # This would typically be called after document processing.
    # For a full test, you would run document_processor.py first to get actual chunks.
    
    # Create a dummy PDF file for testing if it doesn't exist
    dummy_pdf_path = os.path.join(DOCUMENTS_DIR, "dummy_legal_doc.pdf")
    os.makedirs(DOCUMENTS_DIR, exist_ok=True)
    if not os.path.exists(dummy_pdf_path):
        print(f"Creating a dummy PDF at {dummy_pdf_path} for testing vector store.")
        # In a real scenario, you'd have actual PDF files.
        # For simplicity, we'll just use sample text directly.
        sample_text = """
        The Code of Civil Procedure, 1908 is a procedural law related to the administration of civil proceedings in India.
        The Code of Criminal Procedure, 1973 is the main legislation on procedure for administration of criminal law in India.
        It provides the machinery for the investigation of crime, apprehension of suspected criminals, collection of evidence,
        determination of guilt or innocence of the accused person and the determination of punishment of the guilty.
        """
        from document_processor import clean_text, chunk_text
        sample_chunks = chunk_text(clean_text(sample_text))
    else:
        from document_processor import process_document
        sample_chunks = process_document(dummy_pdf_path)
        if not sample_chunks:
            print(f"Could not process {dummy_pdf_path}. Using default sample chunks.")
            sample_chunks = [
                "The Code of Civil Procedure, 1908 is a procedural law related to the administration of civil proceedings in India.",
                "The Code of Criminal Procedure, 1973 is the main legislation on procedure for administration of criminal law in India.",
                "It provides the machinery for the investigation of crime, apprehension of suspected criminals, collection of evidence, determination of guilt or innocence of the accused person and the determination of punishment of the guilty."
            ]


    print("--- Creating Vector Store ---")
    db = create_vector_store(sample_chunks)
    if db:
        print("\n--- Testing Retrieval from Created Store ---")
        query = "What is the purpose of the Code of Criminal Procedure?"
        results = db.similarity_search(query, k=2)
        for i, doc in enumerate(results):
            print(f"\n--- Retrieved Document {i+1} ---")
            print(doc.page_content)

    print("\n--- Loading Existing Vector Store ---")
    loaded_db = load_vector_store()
    if loaded_db:
        print("\n--- Testing Retrieval from Loaded Store ---")
        query = "What is the Code of Civil Procedure about?"
        results = loaded_db.similarity_search(query, k=1)
        for i, doc in enumerate(results):
            print(f"\n--- Retrieved Document {i+1} ---")
            print(doc.page_content)
