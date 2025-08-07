import os

# --- General Configuration ---
PROJECT_NAME = "Vakil Buddy Legal Chatbot AI Engine"
PROJECT_VERSION = "1.2.0"
CHROMA_DB_DIR = "legal_chatbot_engine/chroma_db"
DOCUMENTS_DIR = "legal_chatbot_engine/data/legal_docs" # Directory where legal PDFs will be stored

# --- LLM Configuration ---
# Options: "dummy", "openai", "ollama"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "dummy") 

# OpenAI Configuration (if LLM_PROVIDER is "openai")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-3.5-turbo")
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", 0.0))

# Ollama Configuration (if LLM_PROVIDER is "ollama")
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "llama2")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# --- Embedding Model Configuration ---
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")

# --- Document Processing Configuration ---
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1000))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 200))

# SpaCy Configuration
# If using spaCy for advanced text processing/NER, ensure the model is downloaded:
# python -m spacy download en_core_web_sm

# OCR Configuration (for image-based PDFs)
# Set to True to enable OCR using pytesseract. Requires Tesseract-OCR installation.
ENABLE_OCR = os.getenv("ENABLE_OCR", "False").lower() == "true"
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "/usr/bin/tesseract") # Path to tesseract executable

# --- Logging Configuration ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO") # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Ensure directories exist
os.makedirs(CHROMA_DB_DIR, exist_ok=True)
os.makedirs(DOCUMENTS_DIR, exist_ok=True)

# Example of how to use these settings in your application:
# from config import LLM_PROVIDER, OPENAI_API_KEY, CHROMA_DB_DIR
# if LLM_PROVIDER == "openai":
#     llm = ChatOpenAI(api_key=OPENAI_API_KEY)
