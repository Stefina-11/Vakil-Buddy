# Vakil Buddy Legal Chatbot AI Engine

This project implements the core AI engine for the "Legal Chatbot for Summons & Notices" as per the intern assignment. It leverages a Retrieval-Augmented Generation (RAG) pipeline to analyze legal documents and generate accurate, context-aware answers to user queries. The engine is exposed as a standalone microservice via a FastAPI.

## Project Structure

```
legal_chatbot_engine/
├── api.py                  # FastAPI application to expose the RAG pipeline and other features
├── document_processor.py   # Scripts for ingesting, cleaning, and chunking legal documents
├── rag_pipeline.py         # Implements the RAG logic and summarization using LangChain
├── vector_store.py         # Handles vector embedding and storage (ChromaDB)
├── requirements.txt        # Python dependencies
└── README.md               # This README file
└── chroma_db/              # Directory for ChromaDB persistence (created on first run)
```

## Core Technology Stack

*   **Programming Language**: Python
*   **AI/LLM Framework**: LangChain
*   **Vector Database**: ChromaDB
*   **Core Libraries**: PyMuPDF (for PDF text extraction), `sentence-transformers` (for embeddings)
*   **API Framework**: FastAPI
*   **Version Control**: Git (assumed external)

## Setup and Installation

1.  **Clone the repository**:
    ```bash
    git clone <your-repo-url>
    cd legal_chatbot_engine
    ```

2.  **Create a virtual environment** (recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: `venv\Scripts\activate`
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install Tesseract-OCR** (for image-based PDFs, if needed):
    *   **Linux**: `sudo apt-get install tesseract-ocr`
    *   **macOS**: `brew install tesseract`
    *   **Windows**: Download installer from [Tesseract-OCR GitHub](https://tesseract-ocr.github.io/tessdoc/Downloads.html)
    *   Ensure `pytesseract` is uncommented in `document_processor.py` if you plan to use OCR.

## Usage

### 1. Prepare Legal Documents

Place your Indian legal documents (PDFs) in a designated directory. For example, you can create a `data/legal_docs/` directory inside `legal_chatbot_engine/`.

### 2. Ingest Documents and Populate Vector Store

You can ingest documents via the API.

**Example using `curl`:**

First, ensure your PDF documents are accessible from where the API is running. For example, if you have `doc1.pdf` and `doc2.pdf` in a `data` directory within `legal_chatbot_engine`:

```bash
# Start the FastAPI application (if not already running)
uvicorn api:app --reload --port 8000

# In a new terminal, send an ingestion request
curl -X POST "http://localhost:8000/ingest-documents" \
     -H "Content-Type: application/json" \
     -d '{
           "pdf_paths": [
             "legal_chatbot_engine/data/doc1.pdf",
             "legal_chatbot_engine/data/doc2.pdf"
           ]
         }'
```
*Note: For demonstration purposes, `document_processor.py` and `vector_store.py` contain `if __name__ == "__main__":` blocks that can be run directly to create a dummy vector store with sample text.*

### 3. Query the Chatbot

Once the vector store is populated, you can send queries to the `/process-query` endpoint.

**Example using `curl`:**

```bash
curl -X POST "http://localhost:8000/process-query" \
     -H "Content-Type: application/json" \
     -d '{
           "question": "What is the Code of Civil Procedure, 1908 about?"
         }'
```

### 4. Summarize Documents

A new endpoint `/summarize-document` has been added to provide summaries of legal documents.

**Example using `curl`:**

```bash
curl -X POST "http://localhost:8000/summarize-document" \
     -H "Content-Type: application/json" \
     -d '{
           "pdf_path": "legal_chatbot_engine/data/my_legal_doc_to_summarize.pdf"
         }'
```

### 5. Extract Entities from Documents

A new endpoint `/extract-entities` has been added to extract key entities from legal documents.

**Example using `curl`:**

```bash
curl -X POST "http://localhost:8000/extract-entities" \
     -H "Content-Type: application/json" \
     -d '{
           "pdf_path": "legal_chatbot_engine/data/my_legal_doc_for_entities.pdf"
         }'
```

### 6. Compare Documents

A new endpoint `/compare-documents` has been added to compare two legal documents.

**Example using `curl`:**

```bash
curl -X POST "http://localhost:8000/compare-documents" \
     -H "Content-Type: application/json" \
     -d '{
           "pdf_path1": "legal_chatbot_engine/data/doc_version_1.pdf",
           "pdf_path2": "legal_chatbot_engine/data/doc_version_2.pdf"
         }'
```

### 7. Run the FastAPI Application

To start the API server:

```bash
cd legal_chatbot_engine
uvicorn api:app --reload --port 8000
```

The API will be accessible at `http://localhost:8000`. You can visit `http://localhost:8000/docs` for the interactive OpenAPI (Swagger UI) documentation.

## LLM Integration

The `rag_pipeline.py` currently uses a `DummyLLM` for demonstration. For a functional chatbot, you need to integrate a real Large Language Model.

**Options:**

*   **Local LLM (e.g., Ollama)**:
    *   Install [Ollama](https://ollama.ai/).
    *   Download a model (e.g., `ollama pull llama2`).
    *   Modify `rag_pipeline.py`'s `get_llm()` function to use `Ollama`:
        ```python
        from langchain.llms import Ollama
        def get_llm():
            return Ollama(model="llama2")
        ```
*   **Cloud-based LLM (e.g., OpenAI, Google Gemini)**:
    *   Install the respective LangChain integration library (e.g., `pip install openai`).
    *   Set up API keys as environment variables.
    *   Modify `rag_pipeline.py`'s `get_llm()` function:
        ```python
        # from langchain.chat_models import ChatOpenAI
        # def get_llm():
        #     return ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
        ```

## Future Enhancements

*   **Error Handling**: More robust error handling and logging.
*   **Asynchronous Processing**: Implement background tasks for document ingestion to avoid blocking the API.
*   **Scalability**: Consider distributed vector databases and LLM serving solutions for production.
*   **Advanced RAG**: Implement techniques like HyDE, RAG-Fusion, or more sophisticated prompt engineering.
*   **User Interface**: Integrate with the main Vakil Buddy web application.
*   **OCR Improvement**: Integrate more advanced OCR solutions if `pytesseract` is insufficient for complex image-based documents.
*   **Legal Entity Extraction**: Add functionality to extract key entities (e.g., dates, parties, case numbers) from legal documents.
*   **Document Comparison**: Implement a feature to compare two legal documents and highlight differences.
*   **Automated Drafting (Template-based)**: Provide basic automated drafting capabilities for common legal documents based on templates and extracted information.
