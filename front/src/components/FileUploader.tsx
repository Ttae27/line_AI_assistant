import React, { useState } from 'react';
import { Upload, File, CheckCircle, XCircle, Loader2 } from 'lucide-react';

const FileUploader = () => {
    const [file, setFile] = useState<File | null>(null);
    const [status, setStatus] = useState<
        'initial' | 'uploading' | 'success' | 'fail'
    >('initial');
    const [dragActive, setDragActive] = useState(false);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const selectedFile = e.target.files[0];
            if (selectedFile.type === 'application/pdf' || selectedFile.name.toLowerCase().endsWith('.pdf')) {
                setStatus('initial');
                setFile(selectedFile);
            } else {
                alert('Please select a PDF file only.');
                e.target.value = '';
            }
        }
    };

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            const droppedFile = e.dataTransfer.files[0];
            if (droppedFile.type === 'application/pdf' || droppedFile.name.toLowerCase().endsWith('.pdf')) {
                setStatus('initial');
                setFile(droppedFile);
            } else {
                alert('Please select a PDF file only.');
            }
        }
    };

    const handleUpload = async () => {
        if (file) {
            setStatus('uploading');

            const formData = new FormData();
            formData.append('file', file);

            try {
                const result = await fetch('http://127.0.0.1:8000/upload', {
                    method: 'POST',
                    body: formData,
                });

                const data = await result.json();
                console.log(data);
                setStatus('success');
            } catch (error) {
                console.error(error);
                setStatus('fail');
            }
        }
    };

    const formatFileSize = (bytes: number) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const removeFile = () => {
        setFile(null);
        setStatus('initial');
    };

    return (
        <div className="file-uploader-container">
            <div className="file-uploader-header">
                <div className="upload-icon-container">
                    <Upload size={32} />
                </div>
                <h2>Upload Your PDF File</h2>
                <p>Drag and drop your PDF file here, or click to browse</p>
            </div>

            {!file ? (
                <div
                    className={`drop-zone ${dragActive ? 'drag-active' : ''}`}
                    onDragEnter={handleDrag}
                    onDragLeave={handleDrag}
                    onDragOver={handleDrag}
                    onDrop={handleDrop}
                    onClick={() => document.getElementById('file')?.click()}
                >
                    <input
                        id="file"
                        type="file"
                        accept=".pdf,application/pdf"
                        onChange={handleFileChange}
                        className="file-input"
                    />
                    <div className="drop-zone-content">
                        <div className="drop-zone-icon">
                            <Upload size={32} />
                        </div>
                        <div className="drop-zone-text">
                            <p className="drop-zone-title">Drop your PDF file here</p>
                            <p className="drop-zone-subtitle">
                                or <span className="browse-text">browse</span> to choose a PDF file
                            </p>
                        </div>
                    </div>
                </div>
            ) : (
                <div className="file-display">
                    <div className="file-info">
                        <div className="file-icon-container">
                            <File size={24} />
                        </div>
                        <div className="file-details">
                            <div className="file-header">
                                <h3 className="file-name">{file.name}</h3>
                                <button onClick={removeFile} className="remove-file-btn">
                                    <XCircle size={20} />
                                </button>
                            </div>
                            <div className="file-meta">
                                <span className="file-type-badge">
                                    {file.type || 'Unknown type'}
                                </span>
                                <span className="file-size">{formatFileSize(file.size)}</span>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {file && (
                <div className="upload-button-container">
                    <button
                        onClick={handleUpload}
                        disabled={status === 'uploading'}
                        className={`upload-btn ${status === 'uploading' ? 'uploading' : ''}`}
                    >
                        {status === 'uploading' ? (
                            <>
                                <Loader2 size={20} className="spinning" />
                                <span>Uploading...</span>
                            </>
                        ) : (
                            <>
                                <Upload size={20} />
                                <span>Upload File</span>
                            </>
                        )}
                    </button>
                </div>
            )}

            <Result status={status} />
        </div>
    );
};

const Result = ({ status }: { status: string }) => {
    if (status === 'success') {
        return (
            <div className="result-message success">
                <CheckCircle size={24} />
                <div className="result-text">
                    <p className="result-title">Upload Successful!</p>
                    <p className="result-subtitle">Your file has been uploaded successfully.</p>
                </div>
            </div>
        );
    } else if (status === 'fail') {
        return (
            <div className="result-message error">
                <XCircle size={24} />
                <div className="result-text">
                    <p className="result-title">Upload Failed</p>
                    <p className="result-subtitle">There was an error uploading your file. Please try again.</p>
                </div>
            </div>
        );
    } else if (status === 'uploading') {
        return (
            <div className="result-message uploading">
                <Loader2 size={24} className="spinning" />
                <div className="result-text">
                    <p className="result-title">Uploading...</p>
                    <p className="result-subtitle">Please wait while your file is being uploaded.</p>
                </div>
            </div>
        );
    }
    return null;
};

export default FileUploader;