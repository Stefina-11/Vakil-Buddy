import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [apiStatus, setApiStatus] = useState('Loading API status...');
  const [statusClass, setStatusClass] = useState('loading');
  const [query, setQuery] = useState('');
  const [pdfPath, setPdfPath] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [isQuerying, setIsQuerying] = useState(false);
  const [isSummarizing, setIsSummarizing] = useState(false);

  useEffect(() => {
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
  }, []);

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

  const handleSummarizeSubmit = async () => {
    if (!pdfPath.trim()) return;

    const userMessage = { sender: 'user', type: 'summarize_request', text: `Summarize document: ${pdfPath}` };
    setChatHistory(prev => [...prev, userMessage]);
    setPdfPath('');
    setIsSummarizing(true);

    try {
      const response = await fetch('http://127.0.0.1:8001/summarize-document', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ pdf_path: pdfPath }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      const botMessage = { sender: 'bot', type: 'summarize_response', text: `Summary of ${data.pdf_path}:`, summary: data.summary };
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
      }
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Vakil Buddy Legal Chatbot AI Engine</h1>
        <p className={statusClass}>API Status: {apiStatus}</p>
      </header>

      <div className="main-content">
        <div className="chat-container">
          <div className="chat-history">
            {chatHistory.map((msg, index) => (
              <div key={index} className={`chat-message ${msg.sender}`}>
                {msg.type === 'query' && <p><strong>You:</strong> {msg.text}</p>}
                {msg.type === 'summarize_request' && <p><strong>You:</strong> {msg.text}</p>}
                {msg.type === 'query_response' && (
                  <>
                    <p><strong>Vakil Buddy:</strong> {msg.text}</p>
                    {msg.source_documents && msg.source_documents.length > 0 && (
                      <div className="source-documents">
                        <h4>Source Documents:</h4>
                        {msg.source_documents.map((doc, docIndex) => (
                          <p key={docIndex} className="source-doc-item">{doc}</p>
                        ))}
                      </div>
                    )}
                  </>
                )}
                {msg.type === 'summarize_response' && (
                  <>
                    <p><strong>Vakil Buddy:</strong> {msg.text}</p>
                    <div className="summary-output">
                      <p>{msg.summary}</p>
                    </div>
                  </>
                )}
                {msg.type === 'error' && <p className="error-message"><strong>Error:</strong> {msg.text}</p>}
              </div>
            ))}
            {(isQuerying || isSummarizing) && <div className="chat-message bot loading-message">Vakil Buddy is processing...</div>}
          </div>
          <div className="chat-input-area">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={(e) => handleKeyPress(e, 'query')}
              placeholder="Ask a legal question..."
              disabled={isQuerying || isSummarizing}
            />
            <button onClick={handleQuerySubmit} disabled={isQuerying || isSummarizing}>
              {isQuerying ? 'Querying...' : 'Ask'}
            </button>
          </div>
        </div>

        <div className="feature-panel">
          <h2>Document Tools</h2>
          <div className="tool-section">
            <h3>Summarize Document</h3>
            <input
              type="text"
              value={pdfPath}
              onChange={(e) => setPdfPath(e.target.value)}
              onKeyPress={(e) => handleKeyPress(e, 'summarize')}
              placeholder="Enter PDF path (e.g., data/doc.pdf)"
              disabled={isQuerying || isSummarizing}
            />
            <button onClick={handleSummarizeSubmit} disabled={isQuerying || isSummarizing}>
              {isSummarizing ? 'Summarizing...' : 'Summarize PDF'}
            </button>
            <p className="note">Note: Ensure the PDF path is accessible by the backend server.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
