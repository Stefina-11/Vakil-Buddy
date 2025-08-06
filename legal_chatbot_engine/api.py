from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from rag_pipeline import query_rag_pipeline, summarize_document_chunks
from document_processor import process_document
from vector_store import create_vector_store, load_vector_store
import os
from typing import List
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Vakil Buddy Legal Chatbot AI Engine",
    description="API for the Legal Chatbot's RAG pipeline, capable of analyzing legal documents and generating context-aware answers, providing summarization, and future capabilities like entity extraction and document comparison.",
    version="1.2.0" # Updated version for new features
)

origins = [
    "http://localhost",
    "http://localhost:3000",  # React app runs on port 3000 by default
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model for incoming query requests
class QueryRequest(BaseModel):
    question: str

# Pydantic model for document ingestion requests
class IngestRequest(BaseModel):
    pdf_paths: list[str]

# Pydantic model for summarization requests
class SummarizeRequest(BaseModel):
    pdf_path: str

# Pydantic model for entity extraction requests
class ExtractEntitiesRequest(BaseModel):
    pdf_path: str

# Pydantic model for document comparison requests
class CompareDocumentsRequest(BaseModel):
    pdf_path1: str
    pdf_path2: str

# API endpoint to process a legal query
@app.post("/process-query")
async def process_query(request: QueryRequest):
    """
    Receives a legal query and returns a generated answer using the RAG pipeline.
    """
    try:
        response = query_rag_pipeline(request.question)
        if response:
            return {
                "question": request.question,
                "answer": response.get("result", "No answer found."),
                "source_documents": [doc.page_content for doc in response.get("source_documents", [])]
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to get response from RAG pipeline.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# API endpoint to ingest documents and populate the vector store
@app.post("/ingest-documents")
async def ingest_documents(request: IngestRequest):
    """
    Ingests new legal documents, processes them, and updates the vector store.
    """
    all_chunks = []
    for pdf_path in request.pdf_paths:
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail=f"File not found: {pdf_path}")
        
        chunks = process_document(pdf_path)
        all_chunks.extend(chunks)
    
    if not all_chunks:
        raise HTTPException(status_code=400, detail="No text extracted from provided documents.")

    try:
        # For simplicity, this example overwrites the vector store.
        # In a production system, you might want to append or manage updates more granularly.
        create_vector_store(all_chunks)
        return {"message": f"Successfully ingested {len(request.pdf_paths)} documents and updated vector store."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during document ingestion or vector store creation: {str(e)}")

# New API endpoint for document summarization
@app.post("/summarize-document")
async def summarize_document(request: SummarizeRequest):
    """
    Extracts text from a specified PDF document and provides a summary.
    """
    if not os.path.exists(request.pdf_path):
        raise HTTPException(status_code=404, detail=f"File not found: {request.pdf_path}")
    
    try:
        chunks = process_document(request.pdf_path)
        if not chunks:
            raise HTTPException(status_code=400, detail="No text extracted from the document for summarization.")
        
        summary = summarize_document_chunks(chunks)
        return {
            "pdf_path": request.pdf_path,
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during summarization: {str(e)}")

# New API endpoint for legal entity extraction
@app.post("/extract-entities")
async def extract_entities(request: ExtractEntitiesRequest):
    """
    Extracts key entities (e.g., case name, parties, dates) from a specified PDF document.
    """
    if not os.path.exists(request.pdf_path):
        raise HTTPException(status_code=404, detail=f"File not found: {request.pdf_path}")
    
    try:
        # For entity extraction, we might want the full text, not chunks
        full_text = process_document(request.pdf_path) # process_document returns chunks, but we can join them
        if not full_text:
            raise HTTPException(status_code=400, detail="No text extracted from the document for entity extraction.")
        
        # Join chunks to form full text for extraction
        joined_text = " ".join(full_text)
        
        extracted_info = extract_entities_from_text(joined_text)
        return {
            "pdf_path": request.pdf_path,
            "extracted_entities": extracted_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during entity extraction: {str(e)}")

# New API endpoint for document comparison
@app.post("/compare-documents")
async def compare_documents_api(request: CompareDocumentsRequest):
    """
    Compares two specified PDF documents and highlights key differences.
    """
    if not os.path.exists(request.pdf_path1):
        raise HTTPException(status_code=404, detail=f"File not found: {request.pdf_path1}")
    if not os.path.exists(request.pdf_path2):
        raise HTTPException(status_code=404, detail=f"File not found: {request.pdf_path2}")
    
    try:
        chunks1 = process_document(request.pdf_path1)
        chunks2 = process_document(request.pdf_path2)

        if not chunks1 or not chunks2:
            raise HTTPException(status_code=400, detail="Could not extract text from one or both documents for comparison.")
        
        comparison_result = compare_documents(chunks1, chunks2)
        return {
            "pdf_path1": request.pdf_path1,
            "pdf_path2": request.pdf_path2,
            "comparison_result": comparison_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during document comparison: {str(e)}")

# Root endpoint for basic health check
@app.get("/")
async def read_root():
    return {"message": "Vakil Buddy Legal Chatbot AI Engine is running!"}

if __name__ == "__main__":
    import uvicorn
    # To run the API: uvicorn api:app --reload --port 8000
    # This will run the FastAPI application.
    # Before running, ensure you have run document_processor.py and vector_store.py
    # to populate the ChromaDB, or use the /ingest-documents endpoint.
    print("To run the API, execute: uvicorn api:app --reload --port 8000")
    print("Ensure you have populated the vector store using /ingest-documents or by running document_processor.py and vector_store.py examples.")
    # uvicorn.run(app, host="0.0.0.0", port=8000) # Uncomment to run directly from this script
