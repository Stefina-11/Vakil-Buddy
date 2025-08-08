from fastapi import FastAPI, HTTPException
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from rag_pipeline import query_rag_pipeline, summarize_document_chunks
from document_processor import process_document
from vector_store import create_vector_store, load_vector_store
import os
from typing import List
from fastapi.middleware.cors import CORSMiddleware
import shutil # Import shutil for file operations
from transformers import pipeline # For translation
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
from fastapi.responses import StreamingResponse

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

# Pydantic model for summarization requests (now handles file upload or path)
# We will modify the endpoint directly to accept UploadFile or a path in the body
# class SummarizeRequest(BaseModel):
#     pdf_path: str

# Pydantic model for entity extraction requests
class ExtractEntitiesRequest(BaseModel):
    pdf_path: str

# Pydantic model for document comparison requests
class CompareDocumentsRequest(BaseModel):
    pdf_path1: str
    pdf_path2: str

# Pydantic model for citation extraction requests
class ExtractCitationsRequest(BaseModel):
    pdf_path: str

class TranslateRequest(BaseModel):
    text: str
    target_language: str

class GenerateDocumentRequest(BaseModel):
    prompt: str
    document_type: str # "notice" or "summons"

# Initialize translation pipeline
# This will download the model the first time it's run.
# Consider using a more lightweight model or a dedicated translation API for production.
try:
    translator = pipeline("translation", model="Helsinki-NLP/opus-mt-en-hi") # Example: English to Hindi
except Exception as e:
    print(f"Could not load translation model: {e}. Translation functionality will be unavailable.")
    translator = None

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
async def summarize_document(file: UploadFile = File(None), pdf_path: str = None):
    """
    Extracts text from a specified PDF document (either uploaded or from a path) and provides a summary.
    """
    temp_file_path = None
    document_path_for_processing = None

    try:
        if file:
            # Save the uploaded file temporarily
            upload_dir = "uploaded_temp_files"
            os.makedirs(upload_dir, exist_ok=True)
            temp_file_path = os.path.join(upload_dir, file.filename)
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            document_path_for_processing = temp_file_path
        elif pdf_path:
            document_path_for_processing = pdf_path
        else:
            raise HTTPException(status_code=400, detail="Either a file must be uploaded or a PDF path must be provided.")

        if not os.path.exists(document_path_for_processing):
            raise HTTPException(status_code=404, detail=f"File not found: {document_path_for_processing}")
        
        chunks = process_document(document_path_for_processing)
        if not chunks:
            raise HTTPException(status_code=400, detail="No text extracted from the document for summarization.")
        
        summary = summarize_document_chunks(chunks)
        return {
            "pdf_path": document_path_for_processing,
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during summarization: {str(e)}")
    finally:
        # Clean up the temporary file if it was uploaded
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

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

# New API endpoint for legal citation extraction
@app.post("/extract-citations")
async def extract_citations(request: ExtractCitationsRequest):
    """
    Extracts legal citations from a specified PDF document.
    """
    if not os.path.exists(request.pdf_path):
        raise HTTPException(status_code=404, detail=f"File not found: {request.pdf_path}")
    
    try:
        # Process the document to get full text for citation extraction
        full_text_chunks = process_document(request.pdf_path)
        if not full_text_chunks:
            raise HTTPException(status_code=400, detail="No text extracted from the document for citation extraction.")
        
        joined_text = " ".join(full_text_chunks)
        
        citations = extract_citations_from_text(joined_text)
        return {
            "pdf_path": request.pdf_path,
            "citations": citations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during citation extraction: {str(e)}")

@app.post("/translate")
async def translate_text(request: TranslateRequest):
    """
    Translates the given text to the target language.
    """
    if not translator:
        raise HTTPException(status_code=500, detail="Translation model not loaded. Please check backend logs.")
    
    # Map common language names to model-specific codes if necessary
    # This is a simplified example; a real system would need a robust mapping
    lang_map = {
        "English": "en", "Spanish": "es", "French": "fr", "German": "de",
        "Chinese": "zh", "Japanese": "ja", "Korean": "ko", "Arabic": "ar",
        "Russian": "ru", "Portuguese": "pt", "Italian": "it", "Hindi": "hi",
        "Bengali": "bn", "Punjabi": "pa", "Telugu": "te", "Marathi": "mr",
        "Tamil": "ta", "Urdu": "ur", "Gujarati": "gu", "Kannada": "kn",
        "Malayalam": "ml"
    }
    
    target_lang_code = lang_map.get(request.target_language)
    if not target_lang_code:
        raise HTTPException(status_code=400, detail=f"Unsupported target language: {request.target_language}")

    try:
        # The Helsinki-NLP models are typically 'src_lang-tgt_lang'
        # For simplicity, assuming English as source for now.
        # A more robust solution would detect source language or use a multilingual model.
        # For 'Helsinki-NLP/opus-mt-en-hi', it translates from English to Hindi.
        # If we need to translate to other languages, we'd need different models or a more generic one.
        # For demonstration, let's assume the model can handle the target_lang_code if it's part of its supported set.
        # For a real multi-language setup, you'd load multiple models or a single large multilingual model.
        
        # For now, let's just use a dummy translation if the model isn't specifically en-hi
        # or if we don't have a dynamic model loading/switching mechanism.
        # For a real solution, you'd need to load the correct model for the target_lang_code.
        
        # As a placeholder, let's just return a mock translation for now.
        # In a real scenario, you'd dynamically load the correct model or use a service.
        
        # For the purpose of this task, let's assume the `translator` pipeline can handle the target language
        # if the model supports it. The `Helsinki-NLP/opus-mt-en-hi` model specifically translates EN to HI.
        # To support other languages, we'd need to load different models or a multilingual model.
        
        # For a quick demo, let's just use the loaded model (en-hi) and return a placeholder for others.
        if target_lang_code == "hi" and translator:
            translated_text = translator(request.text)[0]['translation_text']
        else:
            translated_text = f"Translation to {request.target_language} not fully supported by current model. Original: {request.text}"

        return {
            "original_text": request.text,
            "target_language": request.target_language,
            "translated_text": translated_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")

@app.post("/generate-legal-document")
async def generate_legal_document(request: GenerateDocumentRequest):
    """
    Generates a legal document (notice or summons) based on a prompt and returns it as a PDF.
    """
    if request.document_type.lower() not in ["notice", "summons"]:
        raise HTTPException(status_code=400, detail="Invalid document type. Must be 'notice' or 'summons'.")

    try:
        # Generate the text content using the LLM
        document_content = generate_legal_document_content(request.prompt, request.document_type)
        
        # Create a PDF from the generated content
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        textobject = p.beginText()
        textobject.setTextOrigin(50, 750)
        textobject.setFont("Helvetica", 12)
        
        # Split content into lines and add to PDF
        for line in document_content.split('\n'):
            textobject.textLine(line)
        
        p.drawText(textobject)
        p.showPage()
        p.save()
        
        buffer.seek(0)
        
        filename = f"{request.document_type.lower()}_generated.pdf"
        return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={filename}"})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during document generation: {str(e)}")

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
