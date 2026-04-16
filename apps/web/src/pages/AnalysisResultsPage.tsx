import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  BarChart3,
  Brain,
  Target,
  Lightbulb,
  TrendingUp,
  Users,
  Clock,
  AlertTriangle,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
} from 'recharts';
import { datasetsApi, type AnalysisRun, type InsightCandidate } from '../lib/api';
import { InsightCard } from '../components/ui/InsightCard';
import { cn, formatNumber, formatDuration, severityColor, effortColor } from '../lib/utils';

type Section = 'insights' | 'executive' | 'metrics' | 'recommendations';

export function AnalysisResultsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [run, setRun] = useState<AnalysisRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState<Section>('insights');

  useEffect(() => {
    if (!id) return;
    loadResults();
  }, [id]);

  const loadResults = async () => {
    setLoading(true);
    try {
      const res = await datasetsApi.getResults(id!);
      setRun(res.data.data?.latestRun || null);
    } catch (err) {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (!run || run.status !== 'completed') {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <BarChart3 className="w-12 h-12 text-surface-300" />
        <p className="text-surface-600">No completed analysis found</p>
        <button className="btn-secondary" onClick={() => navigate(`/datasets/${id}`)}>
          <ArrowLeft className="w-4 h-4" />
          Back to Dataset
        </button>
      </div>
    );
  }

  const insights: InsightCandidate[] = run.insightCandidates || [];
  const metrics = run.metricsResult || {};
  const llm = run.llmReport;

  const sections: Array<{ id: Section; label: string; icon: any; count?: number }> = [
    { id: 'insights', label: 'Insights', icon: Lightbulb, count: insights.length },
    { id: 'executive', label: 'AI Summary', icon: Brain },
    { id: 'metrics', label: 'Metrics', icon: BarChart3 },
    { id: 'recommendations', label: 'Recommendations', icon: Target, count: llm?.recommendations?.length },
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Top bar */}
      <div className="bg-white border-b border-surface-200 px-6 py-4 sticky top-0 z-10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button className="btn-ghost" onClick={() => navigate(`/datasets/${id}`)}>
              <ArrowLeft className="w-4 h-4" />
              Back
            </button>
            <div className="h-5 w-px bg-surface-200" />
            <div>
              <h1 className="font-semibold text-surface-900">Analysis Results</h1>
              {run.completedAt && (
                <p className="text-xs text-surface-400">
                  Completed {new Date(run.completedAt).toLocaleString()}
                  {llm?.is_mock && (
                    <span className="ml-2 badge badge-warning">Mock AI</span>
                  )}
                </p>
              )}
            </div>
          </div>
          <button className="btn-ghost" onClick={loadResults}>
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>

        {/* Key stats bar */}
        <div className="flex items-center gap-6 mt-3 pt-3 border-t border-surface-100">
          {[
            {
              icon: TrendingUp,
              label: 'Insights Found',
              value: insights.length,
              color: 'text-primary-600',
            },
            {
              icon: Clock,
              label: 'Median Resolution',
              value: metrics.duration_metrics?.median_minutes
                ? formatDuration(metrics.duration_metrics.median_minutes)
                : '—',
              color: 'text-surface-700',
            },
            {
              icon: Users,
              label: 'Assignees Analyzed',
              value: metrics.top_assignees?.length || '—',
              color: 'text-surface-700',
            },
            {
              icon: AlertTriangle,
              label: 'SLA Breach Rate',
              value: metrics.sla_breach_rate?.breach_rate_pct
                ? `${metrics.sla_breach_rate.breach_rate_pct.toFixed(1)}%`
                : '—',
              color: 'text-surface-700',
            },
          ].map((stat) => {
            const Icon = stat.icon;
            return (
              <div key={stat.label} className="flex items-center gap-2">
                <Icon className={cn('w-4 h-4', stat.color)} />
                <span className="text-xs text-surface-500">{stat.label}:</span>
                <span className={cn('text-sm font-semibold', stat.color)}>{stat.value}</span>
              </div>
            );
          })}
        </div>

        {/* Section tabs */}
        <div className="flex gap-1 mt-3">
          {sections.map((s) => {
            const Icon = s.icon;
            return (
              <button
                key={s.id}
                onClick={() => setActiveSection(s.id)}
                className={cn(
                  'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                  activeSection === s.id
                    ? 'bg-primary-50 text-primary-700 border border-primary-200'
                    : 'text-surface-500 hover:text-surface-700 hover:bg-surface-50'
                )}
              >
                <Icon className="w-4 h-4" />
                {s.label}
                {s.count !== undefined && (
                  <span className={cn(
                    'ml-1 px-1.5 py-0.5 rounded-full text-xs font-bold',
                    activeSection === s.id ? 'bg-primary-100 text-primary-700' : 'bg-surface-100 text-surface-500'
                  )}>
                    {s.count}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeSection === 'insights' && (
          <InsightsSection insights={insights} />
        )}
        {activeSection === 'executive' && llm && (
          <ExecutiveSection llm={llm} />
        )}
        {activeSection === 'metrics' && (
          <MetricsSection metrics={metrics} />
        )}
        {activeSection === 'recommendations' && llm && (
          <RecommendationsSection llm={llm} />
        )}
      </div>
    </div>
  );
}

// ─── Insights Section ─────────────────────────────────────────────────────────

function InsightsSection({ insights }: { insights: InsightCandidate[] }) {
  if (insights.length === 0) {
    return (
      <div className="text-center py-16 text-surface-400">
        <Lightbulb className="w-10 h-10 mx-auto mb-3 opacity-40" />
        <p>No insights generated. Ensure column mapping is complete.</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl space-y-3">
      <div className="flex items-center justify-between mb-4">
        <h2 className="section-title">
          {insights.length} Evidence-Backed Insights
        </h2>
        <p className="text-xs text-surface-400">Ranked by impact × support × confidence</p>
      </div>
      {insights.map((insight, i) => (
        <InsightCard key={insight.insight_id} insight={insight} rank={i + 1} />
      ))}
    </div>
  );
}

// ─── Executive Section ────────────────────────────────────────────────────────

function ExecutiveSection({ llm }: { llm: any }) {
  return (
    <div className="max-w-4xl space-y-6">
      {llm.is_mock && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-700">
          <strong>Note:</strong> AI commentary was generated by the built-in evidence analyzer (mock mode).
          Configure <code className="font-mono">OPENAI_API_KEY</code> for GPT-4 powered analysis.
        </div>
      )}

      {/* Executive Summary */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <Brain className="w-5 h-5 text-primary-500" />
          <h3 className="section-title">Executive Summary</h3>
        </div>
        <p className="text-surface-700 leading-relaxed text-base">{llm.executive_summary}</p>
      </div>

      {/* Process Manager Summary */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <Users className="w-5 h-5 text-primary-500" />
          <h3 className="section-title">Process Manager Findings</h3>
        </div>
        <p className="text-surface-700 leading-relaxed">{llm.process_manager_summary}</p>
      </div>

      {/* Top Bottlenecks */}
      {llm.top_bottlenecks?.length > 0 && (
        <div className="card">
          <h3 className="section-title mb-4">Top Bottlenecks</h3>
          <div className="space-y-4">
            {llm.top_bottlenecks.map((b: any, i: number) => (
              <div key={i} className="flex gap-4 p-4 bg-surface-50 rounded-xl border border-surface-200">
                <span className={cn(
                  'shrink-0 px-2 py-0.5 rounded text-xs font-semibold border',
                  severityColor(b.severity)
                )}>
                  {b.severity.toUpperCase()}
                </span>
                <div className="flex-1">
                  <p className="font-semibold text-surface-900 mb-1">{b.title}</p>
                  <p className="text-sm text-surface-600 mb-2">{b.description}</p>
                  <p className="text-xs text-primary-700 bg-primary-50 rounded-lg px-3 py-2">
                    {b.recommendation}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Hypotheses */}
      {llm.hypotheses?.length > 0 && (
        <div className="card">
          <h3 className="section-title mb-4">Root Cause Hypotheses</h3>
          <div className="space-y-3">
            {llm.hypotheses.map((h: any, i: number) => (
              <div key={i} className="p-4 border border-surface-200 rounded-xl">
                <div className="flex items-start justify-between gap-4 mb-2">
                  <p className="font-medium text-surface-900">{h.hypothesis}</p>
                  <span className={cn(
                    'shrink-0 px-2 py-0.5 rounded-full text-xs font-medium border',
                    h.confidence === 'high' ? 'text-success-700 bg-success-50 border-green-200' :
                    h.confidence === 'medium' ? 'text-warning-700 bg-warning-50 border-yellow-200' :
                    'text-surface-600 bg-surface-50 border-surface-200'
                  )}>
                    {h.confidence} confidence
                  </span>
                </div>
                <p className="text-sm text-surface-500">{h.supporting_evidence}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Disclaimer */}
      {llm.disclaimer && (
        <div className="bg-surface-50 border border-surface-200 rounded-xl p-4 text-xs text-surface-500">
          <strong>Disclaimer:</strong> {llm.disclaimer}
        </div>
      )}
    </div>
  );
}

// ─── Metrics Section ──────────────────────────────────────────────────────────

function MetricsSection({ metrics }: { metrics: any }) {
  const volumeData = metrics.volume_over_time || [];
  const weekdayData = metrics.weekday_patterns || [];
  const categories = metrics.top_categories || [];
  const assignees = metrics.top_assignees || [];
  const duration = metrics.duration_metrics || {};

  return (
    <div className="max-w-5xl space-y-6">
      {/* Duration Overview */}
      {duration.median_minutes && (
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: 'Median Resolution', value: formatDuration(duration.median_minutes) },
            { label: 'P95 Resolution', value: formatDuration(duration.p95_minutes) },
            { label: 'Mean Resolution', value: formatDuration(duration.mean_minutes) },
            { label: 'Cases Analyzed', value: formatNumber(duration.case_count || 0) },
          ].map((s) => (
            <div key={s.label} className="card">
              <p className="stat-label">{s.label}</p>
              <p className="stat-value text-xl">{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Volume over time */}
      {volumeData.length > 0 && (
        <div className="card">
          <h3 className="section-title mb-4">Volume Over Time</h3>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={volumeData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="period" tick={{ fontSize: 11 }} stroke="#94a3b8" />
              <YAxis tick={{ fontSize: 11 }} stroke="#94a3b8" />
              <Tooltip
                contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
              />
              <Area
                type="monotone"
                dataKey="count"
                stroke="#6366f1"
                fill="#e0eaff"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Weekday patterns */}
      {weekdayData.length > 0 && (
        <div className="card">
          <h3 className="section-title mb-4">Weekday Distribution</h3>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={weekdayData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="weekday_name" tick={{ fontSize: 11 }} stroke="#94a3b8" />
              <YAxis tick={{ fontSize: 11 }} stroke="#94a3b8" />
              <Tooltip
                contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0' }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {weekdayData.map((entry: any, index: number) => (
                  <Cell
                    key={index}
                    fill={entry.relative_to_mean > 1.3 ? '#f43f5e' : entry.relative_to_mean > 1.1 ? '#f59e0b' : '#6366f1'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Top categories + assignees side by side */}
      <div className="grid grid-cols-2 gap-4">
        {categories.length > 0 && (
          <div className="card">
            <h3 className="section-title mb-4">Top Categories</h3>
            <div className="space-y-2">
              {categories.slice(0, 8).map((c: any) => (
                <div key={c.category} className="flex items-center gap-3">
                  <span className="text-sm text-surface-700 w-40 truncate" title={c.category}>
                    {c.category}
                  </span>
                  <div className="flex-1 bg-surface-100 rounded-full h-2">
                    <div
                      className="bg-primary-400 h-2 rounded-full"
                      style={{ width: `${c.pct}%` }}
                    />
                  </div>
                  <span className="text-xs text-surface-500 w-12 text-right">
                    {c.pct.toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {assignees.length > 0 && (
          <div className="card">
            <h3 className="section-title mb-4">Top Assignees</h3>
            <div className="space-y-2">
              {assignees.slice(0, 8).map((a: any) => (
                <div key={a.actor} className="flex items-center justify-between text-sm">
                  <span className="text-surface-700 truncate max-w-[140px]" title={a.actor}>
                    {a.actor}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-surface-500">{formatNumber(a.case_count)} cases</span>
                    {a.median_duration_minutes && (
                      <span className="text-xs text-surface-400">
                        {formatDuration(a.median_duration_minutes)} median
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Reopen signals */}
      {metrics.reopen_signals?.reopened_count > 0 && (
        <div className="card border-l-4 border-l-amber-400">
          <h3 className="section-title mb-2">Reopen / Loop Signals</h3>
          <p className="text-sm text-surface-600">
            <strong>{formatNumber(metrics.reopen_signals.reopened_count)}</strong> cases
            ({metrics.reopen_signals.reopen_rate_pct?.toFixed(1)}%) show signs of reopening or escalation.
            Risk level: <strong className={cn(
              metrics.reopen_signals.risk_level === 'high' ? 'text-danger-600' :
              metrics.reopen_signals.risk_level === 'medium' ? 'text-warning-600' : 'text-success-600'
            )}>{metrics.reopen_signals.risk_level}</strong>
          </p>
        </div>
      )}
    </div>
  );
}

// ─── Recommendations Section ──────────────────────────────────────────────────

function RecommendationsSection({ llm }: { llm: any }) {
  const recs = llm.recommendations || [];

  if (recs.length === 0) {
    return (
      <div className="text-center py-16 text-surface-400">
        <Target className="w-10 h-10 mx-auto mb-3 opacity-40" />
        <p>No recommendations available</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="section-title">{recs.length} Recommendations</h2>
        <p className="text-xs text-surface-400">Prioritized by impact</p>
      </div>
      {recs.map((rec: any, i: number) => (
        <div key={i} className="card">
          <div className="flex items-start gap-4">
            <div className="w-7 h-7 rounded-full bg-primary-100 text-primary-700 text-sm font-bold flex items-center justify-center shrink-0">
              {rec.priority || i + 1}
            </div>
            <div className="flex-1">
              <div className="flex items-start justify-between gap-4 mb-2">
                <h3 className="font-semibold text-surface-900">{rec.title}</h3>
                <div className="flex items-center gap-2 shrink-0">
                  <span className={cn(
                    'px-2 py-0.5 rounded text-xs font-medium',
                    effortColor(rec.effort)
                  )}>
                    {rec.effort} effort
                  </span>
                </div>
              </div>
              <p className="text-sm text-surface-600 mb-3">{rec.description}</p>
              {rec.expected_impact && (
                <div className="bg-success-50 border border-success-200 rounded-lg px-3 py-2">
                  <p className="text-xs font-semibold text-success-700 mb-0.5">Expected Impact</p>
                  <p className="text-sm text-success-800">{rec.expected_impact}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
