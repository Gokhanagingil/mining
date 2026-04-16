import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, RefreshCw, ArrowRight } from 'lucide-react';
import { jobsApi, type JobRun } from '../lib/api';
import { StatusBadge } from '../components/ui/StatusBadge';
import { formatDate } from '../lib/utils';

export function JobsPage() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<JobRun[]>([]);
  const [loading, setLoading] = useState(false);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const res = await jobsApi.list();
      setJobs(res.data.data || []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
    const interval = setInterval(fetch, 5000);
    return () => clearInterval(interval);
  }, [fetch]);

  const JOB_TYPE_LABELS: Record<string, string> = {
    profiling: 'Schema Profiling',
    analysis: 'Analysis Run',
  };

  return (
    <div className="px-6 py-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">Job History</h1>
          <p className="text-surface-500 text-sm mt-1">
            All background jobs: profiling, analysis, and their status
          </p>
        </div>
        <button className="btn-ghost" onClick={fetch}>
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {loading && jobs.length === 0 ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card animate-pulse">
              <div className="h-4 bg-surface-200 rounded w-1/4 mb-2" />
              <div className="h-3 bg-surface-100 rounded w-1/3" />
            </div>
          ))}
        </div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-20">
          <Activity className="w-12 h-12 text-surface-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-surface-600 mb-2">No jobs yet</h3>
          <p className="text-surface-500 text-sm">
            Upload and profile a dataset to see jobs here
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {jobs.map((job) => (
            <div
              key={job.id}
              className="card-hover cursor-pointer group"
              onClick={() => navigate(`/datasets/${job.datasetId}`)}
            >
              <div className="flex items-center gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <span className="font-medium text-surface-800">
                      {JOB_TYPE_LABELS[job.jobType] || job.jobType}
                    </span>
                    <StatusBadge status={job.status} />
                  </div>
                  <div className="flex items-center gap-4 text-xs text-surface-400">
                    <span>Dataset: {job.datasetId.slice(0, 8)}…</span>
                    <span>Started: {formatDate(job.startedAt)}</span>
                    {job.completedAt && (
                      <span>Completed: {formatDate(job.completedAt)}</span>
                    )}
                  </div>
                  {job.errorMessage && (
                    <p className="mt-1 text-xs text-danger-600">{job.errorMessage}</p>
                  )}
                </div>
                <ArrowRight className="w-4 h-4 text-surface-300 group-hover:text-primary-500 transition-colors shrink-0" />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
