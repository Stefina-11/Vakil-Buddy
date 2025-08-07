import spacy
from langchain.chains import RetrievalQA, create_extraction_chain
from langchain.chains.summarize import load_summarize_chain
from langchain_community.chat_models import ChatOpenAI
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.docstore.document import Document
from vector_store import load_vector_store
import os
from typing import List, Dict, Any
from config import LLM_PROVIDER, OPENAI_API_KEY, OPENAI_MODEL_NAME, OPENAI_TEMPERATURE, OLLAMA_MODEL_NAME, OLLAMA_BASE_URL

# Load spaCy model
# Ensure you have downloaded the model, e.g., by running: python -m spacy download en_core_web_sm
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("SpaCy model 'en_core_web_sm' not found. Please run 'python -m spacy download en_core_web_sm'")
    nlp = None

class DummyLLM:
    def __init__(self):
        pass

    def __call__(self, prompt: str) -> str:
        if "Code of Civil Procedure" in prompt and "purpose" in prompt:
            return "The Code of Civil Procedure, 1908 is a procedural law related to the administration of civil proceedings in India."
        elif "Code of Criminal Procedure" in prompt and "purpose" in prompt:
            return "The Code of Criminal Procedure, 1973 is the main legislation on procedure for administration of criminal law in India. It provides machinery for investigation of crime, apprehension of suspected criminals, collection of evidence, determination of guilt or innocence, and punishment."
        elif "summarize" in prompt.lower():
            return "This is a summary of the provided legal text, focusing on key procedural aspects and definitions."
        elif "extract entities" in prompt.lower():
            return '{"case_name": "Simulated Case", "parties": ["Party A", "Party B"], "date": "2023-01-01", "sections_cited": ["Section 1", "Section 2"]}'
        elif "compare documents" in prompt.lower():
            return "Simulated comparison: Documents are broadly similar but have minor differences in phrasing."
        else:
            return "I am a dummy LLM and cannot answer complex legal queries without a real model. Please provide a real LLM integration."

def get_llm():
    """
    Initializes and returns the Large Language Model based on configuration.
    """
    if LLM_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set in environment variables or config.py")
        print(f"Using OpenAI LLM: {OPENAI_MODEL_NAME}")
        return ChatOpenAI(model_name=OPENAI_MODEL_NAME, temperature=OPENAI_TEMPERATURE, openai_api_key=OPENAI_API_KEY)
    elif LLM_PROVIDER == "ollama":
        print(f"Using Ollama LLM: {OLLAMA_MODEL_NAME} at {OLLAMA_BASE_URL}")
        return Ollama(model=OLLAMA_MODEL_NAME, base_url=OLLAMA_BASE_URL)
    else: # Default to dummy
        print("Using DummyLLM. Please configure a real LLM for production.")
        return DummyLLM()

def setup_rag_pipeline():
    """
    Sets up the Retrieval-Augmented Generation (RAG) pipeline.
    """
    vector_store = load_vector_store()
    if not vector_store:
        print("Vector store not found. Please create it first by running document ingestion.")
        return None

    llm = get_llm()

    template = """Use the following pieces of context to answer the question at the end.
    If you don't know the answer, just say that you don't know, don't try to make up an answer.
    Keep the answer as concise as possible.

    {context}

    Question: {question}
    Concise Answer:"""
    PROMPT = PromptTemplate(
        template=template, input_variables=["context", "question"]
    )

    retriever = vector_store.as_retriever()

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": PROMPT}
    )
    print("RAG pipeline setup complete.")
    return qa_chain

def query_rag_pipeline(query: str):
    """
    Queries the RAG pipeline with a given question.
    """
    qa_chain = setup_rag_pipeline()
    if not qa_chain:
        return "Error: RAG pipeline could not be set up."
    
    print(f"Querying RAG pipeline with: '{query}'")
    response = qa_chain({"query": query})
    return response

def summarize_document_chunks(chunks: List[str]) -> str:
    """
    Summarizes a list of text chunks using LangChain's summarization chain.
    """
    llm = get_llm()
    if isinstance(llm, DummyLLM):
        return "This is a simulated summary from the DummyLLM. Please integrate a real LLM for actual summarization."

    docs = [Document(page_content=t) for t in chunks]
    
    chain = load_summarize_chain(llm, chain_type="map_reduce")
    
    print(f"Summarizing {len(chunks)} chunks.")
    summary = chain.run(docs)
    return summary

def extract_entities_from_text(text: str) -> Dict[str, Any]:
    """
    Extracts key entities from legal text using an LLM.
    """
    llm = get_llm()
    if isinstance(llm, DummyLLM):
        return {"message": "Simulated entity extraction. Integrate a real LLM for actual extraction.", "entities": {}}

    extracted_data = {}
    if nlp:
        doc = nlp(text)
        # Example of extracting common entities using spaCy
        # You can customize this based on the types of legal entities you need
        extracted_data["persons"] = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
        extracted_data["organizations"] = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
        extracted_data["dates"] = [ent.text for ent in doc.ents if ent.label_ == "DATE"]
        extracted_data["gpes"] = [ent.text for ent in doc.ents if ent.label_ == "GPE"] # Geo-political entity

        # You can also use the LLM for more complex or specific entity extraction
        # based on a schema, as was done previously. Combining both approaches
        # can yield better results.
        schema = {
            "properties": {
                "case_name": {"type": "string", "description": "The name of the legal case."},
                "parties": {"type": "array", "items": {"type": "string"}, "description": "List of parties involved in the case."},
                "date_of_judgment": {"type": "string", "format": "date", "description": "The date of the judgment or order."},
                "sections_cited": {"type": "array", "items": {"type": "string"}, "description": "List of legal sections or acts cited."},
                "court": {"type": "string", "description": "The court where the case was heard."},
                "judge": {"type": "string", "description": "The name of the presiding judge(s)."}
            },
            "required": ["case_name", "parties"],
        }
        try:
            chain = create_extraction_chain(schema, llm)
            llm_extracted_data = chain.run(text)
            # Merge LLM extracted data with spaCy extracted data
            extracted_data.update(llm_extracted_data)
        except Exception as e:
            print(f"Warning: LLM-based entity extraction failed: {e}")
            extracted_data["llm_extraction_error"] = str(e)

    else:
        extracted_data["message"] = "SpaCy model not loaded. Falling back to LLM-only extraction if configured."
        # Fallback to LLM-only extraction if spaCy is not available
        schema = {
            "properties": {
                "case_name": {"type": "string", "description": "The name of the legal case."},
                "parties": {"type": "array", "items": {"type": "string"}, "description": "List of parties involved in the case."},
                "date_of_judgment": {"type": "string", "format": "date", "description": "The date of the judgment or order."},
                "sections_cited": {"type": "array", "items": {"type": "string"}, "description": "List of legal sections or acts cited."},
                "court": {"type": "string", "description": "The court where the case was heard."},
                "judge": {"type": "string", "description": "The name of the presiding judge(s)."}
            },
            "required": ["case_name", "parties"],
        }
        try:
            chain = create_extraction_chain(schema, llm)
            llm_extracted_data = chain.run(text)
            extracted_data.update(llm_extracted_data)
        except Exception as e:
            print(f"Error during LLM-only entity extraction: {str(e)}")
            extracted_data["llm_extraction_error"] = str(e)


    return {"message": "Extracted entities.", "entities": extracted_data}

def compare_documents(doc1_chunks: List[str], doc2_chunks: List[str]) -> Dict[str, Any]:
    """
    Compares two legal documents using an LLM to highlight differences.
    This is a simplified approach; for robust comparison, more advanced NLP might be needed.
    """
    llm = get_llm()
    if isinstance(llm, DummyLLM):
        return {"message": "Simulated document comparison. Integrate a real LLM for actual comparison.", "differences": "Differences would be highlighted here."}

    # Combine chunks into single strings for comparison
    doc1_full_text = " ".join(doc1_chunks)
    doc2_full_text = " ".join(doc2_chunks)

    # Create a prompt for comparison
    prompt_template = """Compare the following two legal documents and identify key differences,
    especially focusing on changes in clauses, facts, or legal interpretations.
    Document 1:
    {doc1_text}

    Document 2:
    {doc2_text}

    Provide a concise summary of the differences:"""

    prompt = prompt_template.format(doc1_text=doc1_full_text[:2000], doc2_text=doc2_full_text[:2000]) # Limit text to avoid token limits

    try:
        comparison_result = llm(prompt)
        return {"message": "Document comparison completed.", "differences": comparison_result}
    except Exception as e:
        return {"message": f"Error during document comparison: {str(e)}", "differences": {}}

def extract_citations_from_text(text: str) -> List[str]:
    """
    Extracts common Indian legal citations from the given text using regex.
    This is a basic implementation and can be expanded for more complex patterns.
    """
    citations = []
    # Regex for common Indian legal citations (e.g., "Section X of Y Act", "Article Z")
    # This is a simplified example; real-world legal citation regex can be very complex.
    # Examples:
    # - Section 302 of the Indian Penal Code
    # - Article 21 of the Constitution
    # - Order XXI Rule 10 CPC
    # - (2023) 1 SCC 123
    
    # Pattern for "Section X of Y Act" or "Article X of Y"
    section_pattern = r"(?:Section|Article|Rule|Order)\s+\d+(?:[A-Za-z])?\s+(?:of\s+the\s+)?(?:[A-Z][a-zA-Z\s]+(?:Act|Code|Constitution|Rules|Regulation),?\s+\d{4})?"
    
    # Pattern for common law reports (e.g., (YEAR) VOLUME REPORTER PAGE)
    # This is highly simplified and would need to be much more robust for real cases.
    case_pattern = r"\(\d{4}\)\s+\d+\s+[A-Z]+\s+\d+"

    # Find all matches
    citations.extend(re.findall(section_pattern, text, re.IGNORECASE))
    citations.extend(re.findall(case_pattern, text, re.IGNORECASE))

    # Remove duplicates and clean up whitespace
    citations = list(set([re.sub(r'\s+', ' ', c).strip() for c in citations]))
    
    return citations


if __name__ == "__main__":
    # Example usage:
    # This part assumes you have already created and populated the vector store
    # by running document_processor.py and vector_store.py examples.
    # For a full test, you would run:
    # 1. python legal_chatbot_engine/document_processor.py (to get chunks)
    # 2. python legal_chatbot_engine/vector_store.py (to create/load DB)
    # 3. Then run this script.

    # Simulate a query
    test_query = "What is the Code of Criminal Procedure, 1973 about?"
    result = query_rag_pipeline(test_query)
    print("\n--- RAG Pipeline Response ---")
    print(f"Question: {test_query}")
    print(f"Answer: {result.get('result', 'No answer found.')}")
    if 'source_documents' in result:
        print("\n--- Source Documents ---")
        for i, doc in enumerate(result['source_documents']):
            print(f"Document {i+1}:")
            print(doc.page_content)
            print("-" * 20)

    # Example for summarization (requires actual chunks)
    # from document_processor import process_document
    # from config import DOCUMENTS_DIR
    # dummy_pdf_path = os.path.join(DOCUMENTS_DIR, "dummy_legal_doc.pdf") # Ensure this file exists or create one
    # if os.path.exists(dummy_pdf_path):
    #     print("\n--- Testing Summarization ---")
    #     doc_chunks = process_document(dummy_pdf_path)
    #     if doc_chunks:
    #         summary_result = summarize_document_chunks(doc_chunks)
    #         print(f"Summary: {summary_result}")
    # else:
    #     print("\nSkipping summarization test: dummy_legal_doc.pdf not found.")

    # Example for entity extraction (requires actual text)
    # sample_legal_text = """
    # In the case of R. v. Smith, heard on 2023-01-15, the parties involved were the Crown and Mr. John Smith.
    # The judgment referred to Section 302 of the Indian Penal Code. The court was the High Court of Delhi. Judge was Justice A.K. Sharma.
    # """
    # print("\n--- Testing Entity Extraction ---")
    # extracted_info = extract_entities_from_text(sample_legal_text)
    # print(f"Extracted Entities: {extracted_info}")

    # Example for document comparison (requires actual chunks from two documents)
    # doc1_sample_chunks = ["This is the first part of document one.", "This is the second part of document one."]
    # doc2_sample_chunks = ["This is the first part of document two.", "This is the second part of document two, with a slight change."]
    # print("\n--- Testing Document Comparison ---")
    # comparison_info = compare_documents(doc1_sample_chunks, doc2_sample_chunks)
    # print(f"Comparison Result: {comparison_info}")
