import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  BarChart3,
  Play,
  RefreshCw,
  FileText,
  Layers,
  GitBranch,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Download,
} from 'lucide-react';
import { useDataset } from '../hooks/useDataset';
import { datasetsApi } from '../lib/api';
import { StatusBadge } from '../components/ui/StatusBadge';
import { ScoreGauge } from '../components/ui/ScoreGauge';
import { ConfidenceBadge } from '../components/ui/ConfidenceBadge';
import { formatBytes, formatDate, formatNumber } from '../lib/utils';
import { cn } from '../lib/utils';

type Tab = 'overview' | 'profile' | 'mapping' | 'results';

export function DatasetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { dataset, loading, refetch } = useDataset(id);
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  if (loading && !dataset) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (!dataset) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <AlertCircle className="w-12 h-12 text-danger-500" />
        <p className="text-surface-600">Dataset not found</p>
        <button className="btn-secondary" onClick={() => navigate('/datasets')}>
          <ArrowLeft className="w-4 h-4" />
          Back to Datasets
        </button>
      </div>
    );
  }

  const profiling = dataset.profilingResult;
  const readiness = profiling?.process_readiness;

  const handleStartProfiling = async () => {
    setActionLoading(true);
    setActionError(null);
    try {
      await datasetsApi.startProfiling(id!);
      await refetch();
    } catch (err: any) {
      setActionError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleStartAnalysis = async () => {
    setActionLoading(true);
    setActionError(null);
    try {
      await datasetsApi.startAnalysis(id!);
      await refetch();
      setActiveTab('results');
    } catch (err: any) {
      setActionError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleExport = () => {
    const data = JSON.stringify(
      {
        dataset,
        profiling: dataset.profilingResult,
        mapping: dataset.mappingDecision,
      },
      null,
      2
    );
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${dataset.name}-analysis.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const tabs: Array<{ id: Tab; label: string; icon: any }> = [
    { id: 'overview', label: 'Overview', icon: FileText },
    { id: 'profile', label: 'Schema Profile', icon: Layers },
    { id: 'mapping', label: 'Column Mapping', icon: GitBranch },
    { id: 'results', label: 'Analysis Results', icon: BarChart3 },
  ];

  const canProfile = ['uploaded', 'failed'].includes(dataset.status);
  const canAnalyze = ['awaiting-mapping', 'completed'].includes(dataset.status) && dataset.mappingDecision;
  const isProcessing = ['profiling', 'analyzing'].includes(dataset.status);

  return (
    <div className="flex flex-col h-full">
      {/* Top bar */}
      <div className="bg-white border-b border-surface-200 px-6 py-4 sticky top-0 z-10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              className="btn-ghost"
              onClick={() => navigate('/datasets')}
            >
              <ArrowLeft className="w-4 h-4" />
              Back
            </button>
            <div className="h-5 w-px bg-surface-200" />
            <div>
              <h1 className="font-semibold text-surface-900">{dataset.name}</h1>
              <div className="flex items-center gap-2 mt-0.5">
                <StatusBadge status={dataset.status} />
                <span className="text-xs text-surface-400">
                  {formatBytes(dataset.fileSizeBytes)}
                  {dataset.rowCount && ` · ${formatNumber(dataset.rowCount)} rows`}
                  {dataset.columnCount && ` · ${dataset.columnCount} columns`}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              className="btn-ghost"
              onClick={refetch}
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button className="btn-secondary" onClick={handleExport}>
              <Download className="w-4 h-4" />
              Export JSON
            </button>
            {canProfile && (
              <button
                className="btn-primary"
                onClick={handleStartProfiling}
                disabled={actionLoading}
              >
                {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                Start Profiling
              </button>
            )}
            {canAnalyze && (
              <button
                className="btn-primary"
                onClick={handleStartAnalysis}
                disabled={actionLoading}
              >
                {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />}
                Run Analysis
              </button>
            )}
          </div>
        </div>

        {/* Error */}
        {(actionError || dataset.errorMessage) && (
          <div className="mt-3 flex items-center gap-2 text-sm text-danger-700 bg-danger-50 border border-danger-200 rounded-lg px-3 py-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            {actionError || dataset.errorMessage}
          </div>
        )}

        {/* Processing indicator */}
        {isProcessing && (
          <div className="mt-3 flex items-center gap-2 text-sm text-primary-700 bg-primary-50 border border-primary-200 rounded-lg px-3 py-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            {dataset.status === 'profiling'
              ? 'Profiling in progress — detecting schema, types, and semantic roles...'
              : 'Analysis in progress — computing metrics and generating insights...'}
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 mt-4">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                  activeTab === tab.id
                    ? 'bg-primary-50 text-primary-700 border border-primary-200'
                    : 'text-surface-500 hover:text-surface-700 hover:bg-surface-50'
                )}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === 'overview' && (
          <OverviewTab dataset={dataset} readiness={readiness} />
        )}
        {activeTab === 'profile' && profiling && (
          <ProfileTab profiling={profiling} />
        )}
        {activeTab === 'mapping' && (
          <MappingTab dataset={dataset} onMappingUpdated={refetch} />
        )}
        {activeTab === 'results' && (
          <ResultsTab datasetId={id!} dataset={dataset} onNavigate={navigate} />
        )}
        {!profiling && activeTab !== 'overview' && activeTab !== 'mapping' && (
          <div className="text-center py-16 text-surface-400">
            <Layers className="w-10 h-10 mx-auto mb-3 opacity-50" />
            <p>Profiling data not yet available</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Overview Tab ────────────────────────────────────────────────────────────

function OverviewTab({ dataset, readiness }: any) {
  return (
    <div className="max-w-4xl space-y-6">
      {/* Stat cards */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Rows', value: dataset.rowCount ? formatNumber(dataset.rowCount) : '—' },
          { label: 'Columns', value: dataset.columnCount ?? '—' },
          { label: 'File Size', value: formatBytes(dataset.fileSizeBytes) },
          { label: 'Status', value: dataset.status },
        ].map((s) => (
          <div key={s.label} className="card">
            <p className="stat-label">{s.label}</p>
            <p className="stat-value">{s.value}</p>
          </div>
        ))}
      </div>

      {/* Process readiness */}
      {readiness && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="section-title">Process Analysis Readiness</h3>
              <p className="section-subtitle">How suitable this dataset is for process mining</p>
            </div>
            <div className="text-right">
              <div className={cn(
                'text-3xl font-bold',
                readiness.overall >= 70 ? 'text-success-600' :
                readiness.overall >= 40 ? 'text-warning-600' : 'text-danger-600'
              )}>
                {readiness.overall.toFixed(0)}
              </div>
              <div className="text-xs text-surface-500">/ 100</div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-x-8 gap-y-4">
            <ScoreGauge label="Timeline Quality" score={readiness.timeline_quality} />
            <ScoreGauge label="Case Traceability" score={readiness.case_traceability} />
            <ScoreGauge label="Activity Clarity" score={readiness.activity_clarity} />
            <ScoreGauge label="Actor Clarity" score={readiness.actor_clarity} />
            <ScoreGauge label="Customer Segmentation" score={readiness.customer_segmentation} />
            <ScoreGauge label="Recommendation Confidence" score={readiness.recommendation_confidence} />
          </div>

          {readiness.warnings?.length > 0 && (
            <div className="mt-4 space-y-2">
              {readiness.warnings.map((w: string, i: number) => (
                <div key={i} className="flex items-start gap-2 text-sm text-warning-700 bg-warning-50 rounded-lg px-3 py-2">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  {w}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Timeline */}
      <div className="card">
        <h3 className="section-title mb-4">Dataset Timeline</h3>
        <div className="space-y-2 text-sm">
          {[
            { label: 'Uploaded', value: formatDate(dataset.createdAt), done: true },
            { label: 'Profiling Completed', value: dataset.profilingCompletedAt ? formatDate(dataset.profilingCompletedAt) : null, done: !!dataset.profilingCompletedAt },
            { label: 'Mapping Configured', value: dataset.mappingDecision ? 'Configured' : null, done: !!dataset.mappingDecision },
            { label: 'Analysis Completed', value: dataset.analysisCompletedAt ? formatDate(dataset.analysisCompletedAt) : null, done: !!dataset.analysisCompletedAt },
          ].map((step) => (
            <div key={step.label} className="flex items-center gap-3">
              {step.done ? (
                <CheckCircle2 className="w-4 h-4 text-success-500 shrink-0" />
              ) : (
                <div className="w-4 h-4 rounded-full border-2 border-surface-300 shrink-0" />
              )}
              <span className={step.done ? 'text-surface-700' : 'text-surface-400'}>
                {step.label}
              </span>
              {step.value && (
                <span className="text-surface-400 ml-auto">{step.value}</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Profile Tab ─────────────────────────────────────────────────────────────

function ProfileTab({ profiling }: { profiling: any }) {
  const [filter, setFilter] = useState('');
  const [selectedCol, setSelectedCol] = useState<any | null>(null);

  const inferenceMap = Object.fromEntries(
    (profiling.semantic_inferences || []).map((inf: any) => [inf.column_name, inf])
  );

  const filtered = profiling.columns.filter((c: any) =>
    c.column_name.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="max-w-6xl">
      <div className="flex items-center gap-4 mb-6">
        <div className="flex-1">
          <input
            className="input max-w-xs"
            placeholder="Filter columns..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
        </div>
        <div className="text-sm text-surface-500">
          {profiling.columns.length} columns · {formatNumber(profiling.row_count)} rows
        </div>
      </div>

      <div className="grid grid-cols-1 gap-2">
        {filtered.map((col: any) => {
          const inf = inferenceMap[col.column_name];
          return (
            <div
              key={col.column_name}
              className={cn(
                'bg-white border rounded-xl p-4 cursor-pointer transition-all',
                selectedCol?.column_name === col.column_name
                  ? 'border-primary-300 ring-1 ring-primary-200'
                  : 'border-surface-200 hover:border-surface-300'
              )}
              onClick={() => setSelectedCol(
                selectedCol?.column_name === col.column_name ? null : col
              )}
            >
              <div className="flex items-center gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-medium text-surface-900 truncate">
                      {col.column_name}
                    </span>
                    <span className="badge badge-surface text-xs">{col.inferred_type}</span>
                    {col.is_enum_like && <span className="badge badge-primary">categorical</span>}
                    {col.is_free_text && <span className="badge badge-surface">free text</span>}
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-xs text-surface-500">
                    <span>Nulls: <strong>{(col.null_ratio * 100).toFixed(1)}%</strong></span>
                    <span>Distinct: <strong>{formatNumber(col.distinct_count)}</strong></span>
                    {col.min_value && <span>Min: <strong>{col.min_value}</strong></span>}
                    {col.max_value && <span>Max: <strong>{col.max_value}</strong></span>}
                  </div>
                </div>

                {inf && (
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-xs text-surface-500">
                      {inf.inferred_role.replace(/_/g, ' ')}
                    </span>
                    <ConfidenceBadge confidence={inf.confidence} />
                  </div>
                )}
              </div>

              {/* Expanded detail */}
              {selectedCol?.column_name === col.column_name && (
                <div className="mt-4 pt-4 border-t border-surface-100 grid grid-cols-2 gap-4 animate-slide-up">
                  <div>
                    <p className="text-xs font-semibold text-surface-500 uppercase tracking-wide mb-2">
                      Sample Values
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {col.sample_values?.slice(0, 8).map((v: string, i: number) => (
                        <span key={i} className="px-2 py-0.5 bg-surface-50 border border-surface-200 rounded text-xs font-mono">
                          {v}
                        </span>
                      ))}
                    </div>
                  </div>
                  {inf && (
                    <div>
                      <p className="text-xs font-semibold text-surface-500 uppercase tracking-wide mb-2">
                        Semantic Inference
                      </p>
                      <p className="text-xs text-surface-700 mb-1">
                        <strong>Role:</strong> {inf.inferred_role.replace(/_/g, ' ')}
                      </p>
                      <p className="text-xs text-surface-500">{inf.reason}</p>
                      {inf.alternative_roles?.length > 0 && (
                        <div className="mt-2">
                          <p className="text-xs text-surface-400">Alternatives:</p>
                          {inf.alternative_roles.slice(0, 2).map((alt: any) => (
                            <span key={alt.role} className="text-xs text-surface-500 mr-2">
                              {alt.role.replace(/_/g, ' ')} ({(alt.confidence * 100).toFixed(0)}%)
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                  {col.top_values && (
                    <div className="col-span-2">
                      <p className="text-xs font-semibold text-surface-500 uppercase tracking-wide mb-2">
                        Top Values
                      </p>
                      <div className="space-y-1">
                        {col.top_values.slice(0, 5).map((tv: any) => (
                          <div key={tv.value} className="flex items-center gap-2">
                            <span className="text-xs text-surface-700 w-40 truncate">{tv.value}</span>
                            <div className="flex-1 bg-surface-100 rounded-full h-1.5">
                              <div
                                className="bg-primary-400 h-1.5 rounded-full"
                                style={{ width: `${tv.pct}%` }}
                              />
                            </div>
                            <span className="text-xs text-surface-500 w-12 text-right">
                              {tv.pct.toFixed(1)}%
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Mapping Tab ─────────────────────────────────────────────────────────────

function MappingTab({ dataset, onMappingUpdated }: any) {
  const profiling = dataset.profilingResult;
  const existing = dataset.mappingDecision || {};
  const [mapping, setMapping] = useState<Record<string, string>>(existing);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const columns = profiling?.columns?.map((c: any) => c.column_name) || [];
  const inferences = profiling?.semantic_inferences || [];

  // Pre-fill from inferences if no existing mapping
  const prefill = () => {
    const auto: Record<string, string> = {};
    for (const inf of inferences) {
      const role = inf.inferred_role;
      if (role === 'case_id' && !auto.case_id_column) auto.case_id_column = inf.column_name;
      else if (role === 'activity_name' && !auto.activity_column) auto.activity_column = inf.column_name;
      else if (role === 'created_at' && !auto.created_at_column) auto.created_at_column = inf.column_name;
      else if (role === 'updated_at' && !auto.updated_at_column) auto.updated_at_column = inf.column_name;
      else if (role === 'resolved_at' && !auto.resolved_at_column) auto.resolved_at_column = inf.column_name;
      else if (role === 'closed_at' && !auto.closed_at_column) auto.closed_at_column = inf.column_name;
      else if (role === 'assignee' && !auto.assignee_column) auto.assignee_column = inf.column_name;
      else if (role === 'assignment_group' && !auto.assignment_group_column) auto.assignment_group_column = inf.column_name;
      else if (role === 'customer' && !auto.customer_column) auto.customer_column = inf.column_name;
      else if (role === 'satisfaction_score' && !auto.satisfaction_column) auto.satisfaction_column = inf.column_name;
      else if (role === 'priority' && !auto.priority_column) auto.priority_column = inf.column_name;
      else if (role === 'category' && !auto.category_column) auto.category_column = inf.column_name;
      else if (role === 'subcategory' && !auto.subcategory_column) auto.subcategory_column = inf.column_name;
      else if ((role === 'status' || role === 'state') && !auto.status_column) auto.status_column = inf.column_name;
    }
    setMapping(auto);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await datasetsApi.updateMapping(dataset.id, {
        ...mapping,
        dataset_id: dataset.id,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
      onMappingUpdated();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setSaving(false);
    }
  };

  const FIELDS = [
    { key: 'case_id_column', label: 'Case / Ticket ID', desc: 'Unique identifier per case or incident' },
    { key: 'status_column', label: 'Status / State', desc: 'Current state of the case' },
    { key: 'created_at_column', label: 'Created At', desc: 'Timestamp when case was opened' },
    { key: 'updated_at_column', label: 'Updated At', desc: 'Last modification timestamp' },
    { key: 'resolved_at_column', label: 'Resolved At', desc: 'Resolution timestamp' },
    { key: 'closed_at_column', label: 'Closed At', desc: 'Close timestamp' },
    { key: 'assignee_column', label: 'Assignee', desc: 'Person handling the case' },
    { key: 'assignment_group_column', label: 'Assignment Group / Team', desc: 'Team or queue' },
    { key: 'customer_column', label: 'Customer / Requester', desc: 'Who submitted the case' },
    { key: 'category_column', label: 'Category', desc: 'Primary classification' },
    { key: 'subcategory_column', label: 'Subcategory', desc: 'Secondary classification' },
    { key: 'priority_column', label: 'Priority / Urgency', desc: 'Priority level' },
    { key: 'satisfaction_column', label: 'Satisfaction Score', desc: 'CSAT or NPS score' },
    { key: 'activity_column', label: 'Activity / Event Type', desc: 'Activity or event name' },
  ];

  if (!profiling) {
    return (
      <div className="text-center py-16 text-surface-400">
        <p>Complete profiling first to configure column mapping.</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="section-title">Column Mapping</h3>
          <p className="section-subtitle">
            Map your dataset columns to semantic roles. The system has pre-filled suggestions based on column names and data.
          </p>
        </div>
        <button className="btn-secondary" onClick={prefill}>
          <RefreshCw className="w-4 h-4" />
          Auto-fill
        </button>
      </div>

      <div className="space-y-3">
          {FIELDS.map(({ key, label, desc }) => {
          // Find suggestion based on semantic role
          const suggestion = inferences.find((inf: any) => {
            const role = inf.inferred_role;
            if (key === 'case_id_column') return role === 'case_id';
            if (key === 'activity_column') return role === 'activity_name';
            if (key === 'created_at_column') return role === 'created_at';
            if (key === 'updated_at_column') return role === 'updated_at';
            if (key === 'resolved_at_column') return role === 'resolved_at';
            if (key === 'closed_at_column') return role === 'closed_at';
            if (key === 'assignee_column') return role === 'assignee';
            if (key === 'assignment_group_column') return role === 'assignment_group';
            if (key === 'customer_column') return role === 'customer';
            if (key === 'satisfaction_column') return role === 'satisfaction_score';
            if (key === 'priority_column') return role === 'priority';
            if (key === 'category_column') return role === 'category';
            if (key === 'subcategory_column') return role === 'subcategory';
            if (key === 'status_column') return role === 'status' || role === 'state';
            return false;
          });

          return (
            <div key={key} className="bg-white border border-surface-200 rounded-xl p-4">
              <div className="flex items-start gap-4">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-surface-800 mb-0.5">
                    {label}
                  </label>
                  <p className="text-xs text-surface-500 mb-2">{desc}</p>

                  {suggestion && !mapping[key] && (
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs text-primary-600">
                        Suggested: <strong>{suggestion.column_name}</strong>
                      </span>
                      <ConfidenceBadge confidence={suggestion.confidence} />
                      <button
                        className="text-xs text-primary-600 underline"
                        onClick={() => setMapping((m) => ({ ...m, [key]: suggestion.column_name }))}
                      >
                        Apply
                      </button>
                    </div>
                  )}

                  <select
                    className="input"
                    value={mapping[key] || ''}
                    onChange={(e) =>
                      setMapping((m) => ({ ...m, [key]: e.target.value || '' }))
                    }
                  >
                    <option value="">— Not mapped —</option>
                    {columns.map((col: string) => (
                      <option key={col} value={col}>{col}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-6 flex items-center gap-3">
        <button
          className="btn-primary"
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
          Save Mapping
        </button>
        {saved && (
          <span className="text-sm text-success-600 flex items-center gap-1">
            <CheckCircle2 className="w-4 h-4" />
            Saved!
          </span>
        )}
      </div>
    </div>
  );
}

// ─── Results Tab ─────────────────────────────────────────────────────────────

function ResultsTab({ datasetId, dataset, onNavigate }: { datasetId: string; dataset: any; onNavigate: (path: string) => void }) {
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const loadResults = async () => {
    setLoading(true);
    try {
      const res = await datasetsApi.getResults(datasetId);
      setResults(res.data.data);
    } catch (_err) {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  if (!results && !loading) {
    loadResults();
  }

  const run = results?.latestRun;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (!run || run.status !== 'completed') {
    return (
      <div className="text-center py-20 text-surface-400">
        <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-40" />
        <p className="text-base font-medium mb-2">No analysis results yet</p>
        <p className="text-sm">
          {dataset.status === 'awaiting-mapping'
            ? 'Configure column mapping and run analysis to see results'
            : dataset.status === 'analyzing'
            ? 'Analysis in progress...'
            : 'Run analysis to generate insights'}
        </p>
      </div>
    );
  }

  onNavigate(`/datasets/${datasetId}/results`);
  return null;
}
