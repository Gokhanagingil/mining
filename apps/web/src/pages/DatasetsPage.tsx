import { useNavigate } from 'react-router-dom';
import {
  Database,
  Plus,
  RefreshCw,
  ArrowRight,
  FileText,
  Calendar,
} from 'lucide-react';
import { useDatasets } from '../hooks/useDataset';
import { StatusBadge } from '../components/ui/StatusBadge';
import { formatBytes, formatDate, formatNumber } from '../lib/utils';

export function DatasetsPage() {
  const navigate = useNavigate();
  const { datasets, loading, refetch } = useDatasets();

  return (
    <div className="px-6 py-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">Datasets</h1>
          <p className="text-surface-500 text-sm mt-1">
            All uploaded datasets and their analysis status
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            className="btn-ghost"
            onClick={refetch}
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <button
            className="btn-primary"
            onClick={() => navigate('/')}
          >
            <Plus className="w-4 h-4" />
            Upload Dataset
          </button>
        </div>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card animate-pulse">
              <div className="h-5 bg-surface-200 rounded w-1/3 mb-3" />
              <div className="h-4 bg-surface-100 rounded w-1/4" />
            </div>
          ))}
        </div>
      ) : datasets.length === 0 ? (
        <div className="text-center py-20">
          <Database className="w-12 h-12 text-surface-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-surface-600 mb-2">No datasets yet</h3>
          <p className="text-surface-500 text-sm mb-6">
            Upload your first CSV to start analyzing processes
          </p>
          <button className="btn-primary" onClick={() => navigate('/')}>
            <Plus className="w-4 h-4" />
            Upload Dataset
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {datasets.map((ds) => (
            <div
              key={ds.id}
              className="card-hover cursor-pointer group"
              onClick={() => navigate(`/datasets/${ds.id}`)}
            >
              <div className="flex items-center gap-5">
                {/* Icon */}
                <div className="w-10 h-10 bg-primary-50 rounded-xl flex items-center justify-center shrink-0">
                  <FileText className="w-5 h-5 text-primary-600" />
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <h3 className="font-semibold text-surface-900 truncate">{ds.name}</h3>
                    <StatusBadge status={ds.status} />
                  </div>
                  <div className="flex items-center gap-4 text-xs text-surface-400">
                    <span>{formatBytes(ds.fileSizeBytes)}</span>
                    {ds.rowCount && (
                      <span>{formatNumber(ds.rowCount)} rows</span>
                    )}
                    {ds.columnCount && (
                      <span>{ds.columnCount} columns</span>
                    )}
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {formatDate(ds.createdAt)}
                    </span>
                  </div>
                </div>

                {/* Actions */}
                <ArrowRight className="w-5 h-5 text-surface-300 group-hover:text-primary-500 transition-colors shrink-0" />
              </div>

              {ds.errorMessage && (
                <div className="mt-3 text-xs text-danger-600 bg-danger-50 px-3 py-2 rounded-lg">
                  {ds.errorMessage}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
