import './App.css';

import FileUploader from './components/FileUploader';

function App() {
  return (
        <div className="app-container">
            <div className="app-header">
                <h1 className="app-title">File Upload to RAG</h1>
                <p className="app-subtitle">
                    
                </p>
            </div>
            
            <FileUploader />
            
            <div className="app-footer">
                <p></p>
            </div>
        </div>
    );
}

export default App;