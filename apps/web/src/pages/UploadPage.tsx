import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Upload,
  FileText,
  AlertCircle,
  CheckCircle2,
  Loader2,
  X,
} from 'lucide-react';
import { datasetsApi } from '../lib/api';
import { formatBytes } from '../lib/utils';

type UploadState = 'idle' | 'uploading' | 'success' | 'error';

export function UploadPage() {
  const navigate = useNavigate();
  const [state, setState] = useState<UploadState>('idle');
  const [progress, setProgress] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoProfile, setAutoProfile] = useState(true);

  const handleFile = useCallback((f: File) => {
    if (!f.name.toLowerCase().endsWith('.csv') && !f.name.toLowerCase().endsWith('.gz')) {
      setError('Only CSV files are supported');
      return;
    }
    setFile(f);
    setError(null);
    setState('idle');
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [handleFile]
  );

  const handleUpload = async () => {
    if (!file) return;
    setState('uploading');
    setProgress(0);
    setError(null);

    try {
      const res = await datasetsApi.upload(file, setProgress);
      const id = res.data.data!.id;
      setState('success');

      if (autoProfile) {
        await datasetsApi.startProfiling(id);
        setTimeout(() => navigate(`/datasets/${id}`), 1200);
      }
    } catch (err: any) {
      setState('error');
      setError(err.message);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-6 py-12">
      {/* Header */}
      <div className="mb-10">
        <h1 className="text-3xl font-bold text-surface-900 mb-2">
          Upload Dataset
        </h1>
        <p className="text-surface-500 text-base leading-relaxed">
          Upload a CSV file to begin process analysis. The system will profile
          your data, infer column semantics, and generate evidence-backed insights.
        </p>
      </div>

      {/* Upload zone */}
      <div
        className={`
          relative border-2 border-dashed rounded-2xl p-10 text-center transition-all duration-200 cursor-pointer
          ${dragOver ? 'border-primary-400 bg-primary-50' : 'border-surface-300 hover:border-surface-400 hover:bg-surface-50'}
          ${state === 'success' ? 'border-success-500 bg-success-50' : ''}
          ${state === 'error' ? 'border-danger-500 bg-danger-50' : ''}
        `}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => state !== 'uploading' && document.getElementById('file-input')?.click()}
      >
        <input
          id="file-input"
          type="file"
          accept=".csv,.gz"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        />

        {state === 'success' ? (
          <div className="space-y-2">
            <CheckCircle2 className="w-14 h-14 text-success-500 mx-auto" />
            <p className="font-semibold text-success-700 text-lg">Upload complete</p>
            <p className="text-success-600 text-sm">Redirecting to dataset view...</p>
          </div>
        ) : state === 'uploading' ? (
          <div className="space-y-4">
            <Loader2 className="w-14 h-14 text-primary-500 mx-auto animate-spin" />
            <p className="font-semibold text-surface-700">Uploading...</p>
            <div className="w-full bg-surface-200 rounded-full h-2.5 max-w-sm mx-auto">
              <div
                className="bg-primary-500 h-2.5 rounded-full transition-all duration-200"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-sm text-surface-500">{progress}%</p>
          </div>
        ) : file ? (
          <div className="space-y-3">
            <FileText className="w-14 h-14 text-primary-500 mx-auto" />
            <div>
              <p className="font-semibold text-surface-800 text-base">{file.name}</p>
              <p className="text-surface-500 text-sm">{formatBytes(file.size)}</p>
            </div>
            <button
              className="text-xs text-surface-400 hover:text-danger-600 transition-colors"
              onClick={(e) => { e.stopPropagation(); setFile(null); setState('idle'); }}
            >
              <X className="w-3.5 h-3.5 inline mr-1" />
              Remove
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <Upload className="w-14 h-14 text-surface-300 mx-auto" />
            <div>
              <p className="font-semibold text-surface-600 text-base">
                Drop your CSV here, or click to browse
              </p>
              <p className="text-surface-400 text-sm mt-1">
                Supports CSV (up to 500 MB). 1 million+ rows handled efficiently.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="mt-4 flex items-start gap-3 bg-danger-50 border border-danger-200 rounded-xl p-4">
          <AlertCircle className="w-5 h-5 text-danger-500 shrink-0 mt-0.5" />
          <p className="text-sm text-danger-700">{error}</p>
        </div>
      )}

      {/* Options */}
      {file && state !== 'success' && (
        <div className="mt-6 p-5 bg-white border border-surface-200 rounded-xl space-y-4">
          <h3 className="font-semibold text-surface-800 text-sm">Processing Options</h3>

          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={autoProfile}
              onChange={(e) => setAutoProfile(e.target.checked)}
              className="mt-0.5 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
            />
            <div>
              <p className="text-sm font-medium text-surface-700">
                Automatically start profiling after upload
              </p>
              <p className="text-xs text-surface-500 mt-0.5">
                Detects schema, infers column semantics, and prepares analysis pipeline
              </p>
            </div>
          </label>
        </div>
      )}

      {/* Upload button */}
      {file && state !== 'success' && state !== 'uploading' && (
        <button
          onClick={handleUpload}
          className="btn-primary mt-6 w-full py-3 justify-center text-base"
        >
          <Upload className="w-5 h-5" />
          Upload & Analyze
        </button>
      )}

      {/* Info cards */}
      <div className="mt-10 grid grid-cols-3 gap-4">
        {[
          {
            icon: '🔬',
            title: 'Smart Profiling',
            desc: 'Auto-detects column types, formats, and semantic roles',
          },
          {
            icon: '📊',
            title: 'Deterministic Metrics',
            desc: 'Evidence-based analysis before any AI interpretation',
          },
          {
            icon: '🧠',
            title: 'AI Commentary',
            desc: 'LLM insights grounded exclusively in measured evidence',
          },
        ].map((item) => (
          <div key={item.title} className="text-center p-4 rounded-xl bg-white border border-surface-100">
            <div className="text-2xl mb-2">{item.icon}</div>
            <p className="text-xs font-semibold text-surface-700 mb-1">{item.title}</p>
            <p className="text-xs text-surface-500 leading-relaxed">{item.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
