// components/UploadZone.jsx
import { useRef, useState } from "react";
import { Upload, FileText, FileSearch, Loader2 } from "lucide-react";

export default function UploadZone({ onFileSelect, onAnalyze, file, loading }) {
  const inputRef = useRef(null);
  const [drag, setDrag] = useState(false);

  function handleDrop(e) {
    e.preventDefault();
    setDrag(false);
    const f = e.dataTransfer.files[0];
    if (f) onFileSelect(f);
  }

  return (
    <div className="upload-zone-wrapper">
      <div
        className={`upload-zone ${drag ? "drag-over" : ""} ${file ? "has-file" : ""}`}
        onDragOver={e => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={handleDrop}
        onClick={() => !loading && inputRef.current.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          style={{ display: "none" }}
          onChange={e => onFileSelect(e.target.files[0])}
        />
        <div className="upload-icon-wrap">
          {file ? <FileText size={20} /> : <Upload size={20} />}
        </div>
        {file ? (
          <div>
            <p className="upload-filename">{file.name}</p>
            <p className="upload-hint">Click or drop to replace</p>
          </div>
        ) : (
          <div>
            <p className="upload-title">Drop your RFP here</p>
            <p className="upload-hint">Click to browse · PDF only</p>
          </div>
        )}
      </div>

      <button
        className="btn-analyze"
        onClick={onAnalyze}
        disabled={!file || loading}
      >
        {loading ? (
          <>
            <Loader2 size={14} className="spin" />
            Analyzing…
          </>
        ) : (
          <>
            <FileSearch size={14} />
            Run Agent Pipeline
          </>
        )}
      </button>
    </div>
  );
}
