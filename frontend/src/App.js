import React, { useState, useEffect, useRef } from 'react';
import './App.css';

function App() {
  const [apiStatus, setApiStatus] = useState('Loading API status...');
  const [statusClass, setStatusClass] = useState('loading');
  const [query, setQuery] = useState('');
  const [pdfPath, setPdfPath] = useState('');
  const [selectedFile, setSelectedFile] = useState(null); // New state for selected file
  const [chatHistory, setChatHistory] = useState([]);
  const [isQuerying, setIsQuerying] = useState(false);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [isGeneratingDocument, setIsGeneratingDocument] = useState(false); // New state for document generation
  const [documentPrompt, setDocumentPrompt] = useState(''); // New state for document generation prompt
  const [documentType, setDocumentType] = useState('notice'); // New state for selected document type (notice/summons)
  const [showTranslateOptions, setShowTranslateOptions] = useState(null); // Stores index of message being translated
  const [selectedLanguage, setSelectedLanguage] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [isListening, setIsListening] = useState(false); // New state for voice input
  const [isSpeechRecognitionSupported, setIsSpeechRecognitionSupported] = useState(true); // New state for SR support
  const recognitionRef = useRef(null);

  // Placeholder for available languages (can be fetched from backend later)
  const availableLanguages = [
    'English', 'Spanish', 'French', 'German', 'Chinese', 'Japanese', 'Korean',
    'Arabic', 'Russian', 'Portuguese', 'Italian', 'Hindi', 'Bengali', 'Punjabi',
    'Telugu', 'Marathi', 'Tamil', 'Urdu', 'Gujarati', 'Kannada', 'Malayalam'
  ];

  useEffect(() => {
    // Speech Recognition API setup
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = 'en-US';

      recognitionRef.current.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setQuery(transcript);
        setIsListening(false);
      };

      recognitionRef.current.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
        let errorMessage = `Speech recognition error: ${event.error}.`;
        if (event.error === 'not-allowed') {
          errorMessage += ' Microphone access was denied. Please allow microphone access in your browser settings.';
        } else if (event.error === 'network') {
          errorMessage += ' A network error occurred. Please check your internet connection and microphone permissions.';
        } else if (event.error === 'no-speech') {
          errorMessage += ' No speech was detected. Please try again and speak clearly.';
        } else if (event.error === 'audio-capture') {
          errorMessage += ' Audio capture failed. Please ensure your microphone is connected and working.';
        }
        alert(errorMessage);
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    } else {
      setIsSpeechRecognitionSupported(false);
      console.warn('Speech recognition is not supported in this browser.');
    }

    // Fetch API status
    fetch('http://127.0.0.1:8001/') // Ensure this matches your Uvicorn port
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        setApiStatus(data.message);
        setStatusClass('success');
      })
      .catch(error => {
        setApiStatus(`Error: ${error.message}. Make sure the backend API is running at http://127.0.0.1:8001/`);
        setStatusClass('error');
        console.error('Error fetching API status:', error);
      });

    // Load chat history from localStorage
    const savedChatHistory = localStorage.getItem('chatHistory');
    if (savedChatHistory) {
      setChatHistory(JSON.parse(savedChatHistory));
    }
  }, []); // Empty dependency array ensures this runs only once on mount

  useEffect(() => {
    // Save chat history to localStorage whenever it changes
    localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
  }, [chatHistory]);

  const handleClearHistory = () => {
    setChatHistory([]);
  };

  const handleGenerateDocument = async () => {
    if (!documentPrompt.trim()) return;

    const userMessage = { sender: 'user', type: 'generate_document_request', text: `Generate ${documentType}: "${documentPrompt}"` };
    setChatHistory(prev => [...prev, userMessage]);
    setDocumentPrompt('');
    setIsGeneratingDocument(true);

    try {
      const response = await fetch('http://127.0.0.1:8001/generate-legal-document', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt: documentPrompt, document_type: documentType }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // The backend returns a PDF, so we need to handle it as a blob
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${documentType}_generated.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      const botMessage = { sender: 'bot', type: 'generate_document_response', text: `Successfully generated and downloaded ${documentType}.` };
      setChatHistory(prev => [...prev, botMessage]);

    } catch (error) {
      const errorMessage = { sender: 'bot', type: 'error', text: `Error: Failed to generate document. ${error.message}` };
      setChatHistory(prev => [...prev, errorMessage]);
      console.error('Error generating legal document:', error);
    } finally {
      setIsGeneratingDocument(false);
    }
  };

  const handleVoiceInput = () => {
    if (recognitionRef.current) {
      if (isListening) {
        recognitionRef.current.stop();
        setIsListening(false);
      } else {
        // Request microphone permission before starting recognition
        navigator.mediaDevices.getUserMedia({ audio: true })
          .then(() => {
            recognitionRef.current.start();
            setIsListening(true);
          })
          .catch(error => {
            console.error('Microphone access denied:', error);
            alert('Microphone access denied. Please allow microphone access to use voice input.');
            setIsListening(false);
          });
      }
    } else {
      alert('Speech recognition is not supported in this browser.');
    }
  };

  const handleQuerySubmit = async () => {
    if (!query.trim()) return;

    const userMessage = { sender: 'user', type: 'query', text: query };
    setChatHistory(prev => [...prev, userMessage]);
    setQuery('');
    setIsQuerying(true);

    try {
      const response = await fetch('http://127.0.0.1:8001/process-query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question: query }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      const botMessage = { sender: 'bot', type: 'query_response', text: data.answer, source_documents: data.source_documents };
      setChatHistory(prev => [...prev, botMessage]);
    } catch (error) {
      const errorMessage = { sender: 'bot', type: 'error', text: `Error: Failed to get response from API. ${error.message}` };
      setChatHistory(prev => [...prev, errorMessage]);
      console.error('Error querying RAG pipeline:', error);
    } finally {
      setIsQuerying(false);
    }
  };

  const handleFileChange = (event) => {
    setSelectedFile(event.target.files[0]);
  };

  const handleSummarizeSubmit = async () => {
    if (!pdfPath.trim() && !selectedFile) return;

    let userMessageText = '';
    let requestBody = new FormData();
    let headers = {};

    if (selectedFile) {
      userMessageText = `Summarize document: ${selectedFile.name}`;
      requestBody.append('file', selectedFile);
      // No Content-Type header needed for FormData, browser sets it
    } else {
      userMessageText = `Summarize document: ${pdfPath}`;
      requestBody = JSON.stringify({ pdf_path: pdfPath });
      headers['Content-Type'] = 'application/json';
    }

    const userMessage = { sender: 'user', type: 'summarize_request', text: userMessageText };
    setChatHistory(prev => [...prev, userMessage]);
    setPdfPath('');
    setSelectedFile(null); // Clear selected file after submission
    setIsSummarizing(true);

    try {
      const response = await fetch('http://127.0.0.1:8001/summarize-document', {
        method: 'POST',
        headers: headers,
        body: requestBody,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      const botMessage = { sender: 'bot', type: 'summarize_response', text: `Summary of ${data.pdf_path || (selectedFile ? selectedFile.name : 'document')}:`, summary: data.summary };
      setChatHistory(prev => [...prev, botMessage]);
    } catch (error) {
      const errorMessage = { sender: 'bot', type: 'error', text: `Error: Failed to summarize document. ${error.message}` };
      setChatHistory(prev => [...prev, errorMessage]);
      console.error('Error summarizing document:', error);
    } finally {
      setIsSummarizing(false);
    }
  };

  const handleKeyPress = (e, type) => {
    if (e.key === 'Enter') {
      if (type === 'query' && !isQuerying) {
        handleQuerySubmit();
      } else if (type === 'summarize' && !isSummarizing) {
        handleSummarizeSubmit();
      } else if (type === 'generate_document' && !isGeneratingDocument) {
        handleGenerateDocument();
      }
    }
  };

  const handleTranslate = (index) => {
    setShowTranslateOptions(showTranslateOptions === index ? null : index);
    setSelectedLanguage(''); // Reset selected language when opening/closing options
    setSearchTerm(''); // Reset search term
  };

  const handleLanguageSelect = async (language, index, originalText) => {
    setSelectedLanguage(language);
    setShowTranslateOptions(null); // Close options after selection

    // Optimistically update chat history with a "Translating..." message
    setChatHistory(prevChatHistory => {
      const newChatHistory = [...prevChatHistory];
      newChatHistory[index] = { ...newChatHistory[index], translatedText: 'Translating...' };
      return newChatHistory;
    });

    try {
      const response = await fetch('http://127.0.0.1:8001/translate', { // Assuming a /translate endpoint
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: originalText, target_language: language }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setChatHistory(prevChatHistory => {
        const newChatHistory = [...prevChatHistory];
        newChatHistory[index] = { ...newChatHistory[index], translatedText: data.translated_text };
        return newChatHistory;
      });
    } catch (error) {
      setChatHistory(prevChatHistory => {
        const newChatHistory = [...prevChatHistory];
        newChatHistory[index] = { ...newChatHistory[index], translatedText: `Translation Error: ${error.message}` };
        return newChatHistory;
      });
      console.error('Error translating text:', error);
    }
  };

  const filteredLanguages = availableLanguages.filter(lang =>
    lang.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="App">
      <header className="App-header">
        <h1>Vakil Buddy Legal Chatbot AI Engine</h1>
        <p className={statusClass}>API Status: {apiStatus}</p>
      </header>

      <div className="main-content">
        <div className="chat-container">
          <div className="chat-header">
            <h2>Open to Questions</h2>
            <button className="clear-history-button" onClick={handleClearHistory}>Clear History</button>
          </div>
          <div className="chat-history">
            {chatHistory.map((msg, index) => (
              <div key={index} className={`chat-message ${msg.sender}`}>
                {msg.type === 'query' && <p><strong>You:</strong> {msg.text}</p>}
                {msg.type === 'summarize_request' && <p><strong>You:</strong> {msg.text}</p>}
                {msg.type === 'generate_document_request' && <p><strong>You:</strong> {msg.text}</p>}
                {msg.type === 'query_response' && (
                  <div className="bot-response-content">
                    <p><strong>Vakil Buddy:</strong></p>
                    <div className="bot-text" dangerouslySetInnerHTML={{ __html: formatBotResponse(msg.translatedText || msg.text) }}></div>
                    {msg.source_documents && msg.source_documents.length > 0 && (
                      <div className="source-documents">
                        <h4>Source Documents:</h4>
                        {msg.source_documents.map((doc, docIndex) => (
                          <p key={docIndex} className="source-doc-item">{doc}</p>
                        ))}
                      </div>
                    )}
                    <button className="translate-button" onClick={() => handleTranslate(index)}>
                      Translate
                    </button>
                    {showTranslateOptions === index && (
                      <div className="translate-options">
                        <input
                          type="text"
                          placeholder="Search language..."
                          value={searchTerm}
                          onChange={(e) => setSearchTerm(e.target.value)}
                        />
                        <div className="language-list">
                          {filteredLanguages.map((lang, langIndex) => (
                            <button
                              key={langIndex}
                              onClick={() => handleLanguageSelect(lang, index, msg.text)}
                              className={selectedLanguage === lang ? 'selected' : ''}
                            >
                              {lang}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
                {msg.type === 'summarize_response' && (
                  <div className="bot-response-content">
                    <p><strong>Vakil Buddy:</strong> {msg.text}</p>
                    <div className="summary-output" dangerouslySetInnerHTML={{ __html: formatBotResponse(msg.summary) }}>
                    </div>
                  </div>
                )}
                {msg.type === 'generate_document_response' && (
                  <div className="bot-response-content">
                    <p><strong>Vakil Buddy:</strong> {msg.text}</p>
                  </div>
                )}
                {msg.type === 'error' && <p className="error-message"><strong>Error:</strong> {msg.text}</p>}
              </div>
            ))}
            {(isQuerying || isSummarizing || isGeneratingDocument) && <div className="chat-message bot loading-message">Vakil Buddy is processing...</div>}
          </div>
          <div className="chat-input-area">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={(e) => handleKeyPress(e, 'query')}
              placeholder="Ask a legal question..."
              disabled={isQuerying || isSummarizing || isGeneratingDocument || isListening}
            />
            <button
              onClick={handleVoiceInput}
              disabled={!isSpeechRecognitionSupported || isQuerying || isSummarizing || isGeneratingDocument}
              className={`voice-button ${isListening ? 'listening' : ''}`}
            >
              {isListening ? '🔴' : '🎤'}
            </button>
            <button onClick={handleQuerySubmit} disabled={isQuerying || isSummarizing || isGeneratingDocument || isListening}>
              {isQuerying ? 'Querying...' : 'Ask'}
            </button>
            {!isSpeechRecognitionSupported && (
              <p className="speech-recognition-warning">
                Speech recognition is not supported in this browser.
              </p>
            )}
          </div>
        </div>

        <div className="feature-panel">
          <h2>Document Tools</h2>
          <div className="tool-section">
            <h3>Summarize Document</h3>
            <div className="pdf-input-group">
              <input
                type="text"
                value={pdfPath}
                onChange={(e) => setPdfPath(e.target.value)}
                onKeyPress={(e) => handleKeyPress(e, 'summarize')}
                placeholder="Enter PDF path (e.g., data/doc.pdf)"
                disabled={isQuerying || isSummarizing || isGeneratingDocument || selectedFile} // Disable if file is selected
              />
              <label htmlFor="file-upload" className="file-upload-label">
                <input
                  id="file-upload"
                  type="file"
                  accept=".pdf"
                  onChange={handleFileChange}
                  disabled={isQuerying || isSummarizing || isGeneratingDocument || pdfPath.trim()} // Disable if path is entered
                />
                <span className="attach-icon">📎</span> {/* Attachment icon */}
              </label>
            </div>
            {selectedFile && <p className="selected-file-name">Selected: {selectedFile.name}</p>}
            <button onClick={handleSummarizeSubmit} disabled={isQuerying || isSummarizing || isGeneratingDocument || (!pdfPath.trim() && !selectedFile)}>
              {isSummarizing ? 'Summarizing...' : 'Summarize PDF'}
            </button>
            <p className="note">Note: Ensure the PDF path is accessible by the backend server, or upload a file.</p>
          </div>

          <div className="tool-section">
            <h3>Generate Legal Document</h3>
            <select
              value={documentType}
              onChange={(e) => setDocumentType(e.target.value)}
              disabled={isQuerying || isSummarizing || isGeneratingDocument}
            >
              <option value="notice">Notice</option>
              <option value="summons">Summons</option>
            </select>
            <textarea
              value={documentPrompt}
              onChange={(e) => setDocumentPrompt(e.target.value)}
              onKeyPress={(e) => handleKeyPress(e, 'generate_document')}
              placeholder={`Enter details for the ${documentType} (e.g., "Draft a notice for unpaid rent for John Doe at 123 Main St, due on 2023-01-01").`}
              rows="5"
              disabled={isQuerying || isSummarizing || isGeneratingDocument}
            ></textarea>
            <button onClick={handleGenerateDocument} disabled={isQuerying || isSummarizing || isGeneratingDocument || !documentPrompt.trim()}>
              {isGeneratingDocument ? 'Generating...' : `Generate ${documentType} PDF`}
            </button>
            <p className="note">Note: The generated document will be downloaded as a PDF.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

  // Helper function to format bot responses (e.g., handle newlines)
  const formatBotResponse = (text) => {
    if (!text) return '';
    // Replace newlines with <br /> for proper rendering
    return text.replace(/\n/g, '<br />');
  };

export default App;
