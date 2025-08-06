import fitz  # PyMuPDF
from langchain.text_splitter import RecursiveCharacterTextSplitter
import re
import os
from PIL import Image
import pytesseract
from config import CHUNK_SIZE, CHUNK_OVERLAP, ENABLE_OCR, TESSERACT_CMD, DOCUMENTS_DIR

# Configure pytesseract command if OCR is enabled
if ENABLE_OCR:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extracts text from a PDF document using PyMuPDF.
    If OCR is enabled and text extraction is poor, it attempts OCR.
    """
    text = ""
    try:
        document = fitz.open(pdf_path)
        for page_num in range(document.page_count):
            page = document.load_page(page_num)
            page_text = page.get_text()
            
            # If text is sparse and OCR is enabled, try OCR
            if ENABLE_OCR and len(page_text.strip()) < 50: # Heuristic for sparse text
                print(f"Attempting OCR for page {page_num + 1} of {pdf_path} due to sparse text.")
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                ocr_text = pytesseract.image_to_string(img)
                text += ocr_text
            else:
                text += page_text
        document.close()
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
        if ENABLE_OCR:
            print("Ensure Tesseract-OCR is installed and configured correctly.")
    return text

def clean_text(text: str) -> str:
    """
    Cleans the extracted text by removing extra whitespace and standardizing.
    """
    text = re.sub(r'\s+', ' ', text)  # Replace multiple whitespaces with a single space
    text = text.strip()  # Remove leading/trailing whitespace
    return text

def chunk_text(text: str) -> list[str]:
    """
    Splits the text into semantically relevant chunks using LangChain's
    RecursiveCharacterTextSplitter, using configured chunk size and overlap.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        add_start_index=True,
    )
    chunks = text_splitter.split_text(text)
    return chunks

def process_document(pdf_path: str) -> list[str]:
    """
    Orchestrates the document processing pipeline: extraction, cleaning, and chunking.
    """
    print(f"Processing document: {pdf_path}")
    raw_text = extract_text_from_pdf(pdf_path)
    if not raw_text:
        print(f"No text extracted from {pdf_path}. Skipping.")
        return []

    cleaned_text = clean_text(raw_text)
    chunks = chunk_text(cleaned_text)
    print(f"Extracted {len(chunks)} chunks from {pdf_path}")
    return chunks

if __name__ == "__main__":
    # Example usage:
    # Create a dummy PDF file for testing
    # For a real scenario, you'd place your legal PDFs in the DOCUMENTS_DIR.
    dummy_pdf_path = os.path.join(DOCUMENTS_DIR, "dummy_legal_doc.pdf")
    
    # Ensure the DOCUMENTS_DIR exists
    os.makedirs(DOCUMENTS_DIR, exist_ok=True)

    if not os.path.exists(dummy_pdf_path):
        print(f"Please place your legal PDF documents in '{DOCUMENTS_DIR}'.")
        print("For now, simulating processing with a placeholder.")
        # Simulate some text
        sample_text = """
        The Code of Civil Procedure, 1908 is a procedural law related to the administration of civil proceedings in India.
        The Code of Criminal Procedure, 1973 is the main legislation on procedure for administration of criminal law in India.
        It provides the machinery for the investigation of crime, apprehension of suspected criminals, collection of evidence,
        determination of guilt or innocence of the accused person and the determination of punishment of the guilty.
        """
        print("Simulating PDF text extraction with sample data.")
        chunks = chunk_text(clean_text(sample_text))
        for i, chunk in enumerate(chunks):
            print(f"\n--- Chunk {i+1} ---")
            print(chunk)
    else:
        # If a dummy PDF exists, process it
        processed_chunks = process_document(dummy_pdf_path)
        for i, chunk in enumerate(processed_chunks):
            print(f"\n--- Chunk {i+1} ---")
            print(chunk)
