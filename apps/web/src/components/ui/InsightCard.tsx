import { useState } from 'react';
import { ChevronDown, ChevronUp, ArrowRight } from 'lucide-react';
import type { InsightCandidate } from '../../lib/api';
import { ConfidenceBadge } from './ConfidenceBadge';
import { cn, insightTypeLabel, insightTypeIcon, formatNumber } from '../../lib/utils';

interface Props {
  insight: InsightCandidate;
  rank: number;
}

const TYPE_COLORS: Record<string, string> = {
  temporal_spike: 'border-l-blue-500 bg-blue-50/30',
  workload_imbalance: 'border-l-purple-500 bg-purple-50/30',
  customer_specific_delay: 'border-l-orange-500 bg-orange-50/30',
  assignee_performance_gap: 'border-l-red-500 bg-red-50/30',
  category_recurrence: 'border-l-indigo-500 bg-indigo-50/30',
  satisfaction_degradation: 'border-l-rose-500 bg-rose-50/30',
  self_service_opportunity: 'border-l-emerald-500 bg-emerald-50/30',
  routing_problem: 'border-l-amber-500 bg-amber-50/30',
  queue_bottleneck: 'border-l-red-600 bg-red-50/30',
  rework_loop_pattern: 'border-l-violet-500 bg-violet-50/30',
  backlog_aging: 'border-l-yellow-600 bg-yellow-50/30',
};

export function InsightCard({ insight, rank }: Props) {
  const [expanded, setExpanded] = useState(false);

  const borderColor = TYPE_COLORS[insight.insight_type] || 'border-l-surface-400 bg-surface-50/30';

  return (
    <div
      className={cn(
        'border border-surface-200 rounded-xl border-l-4 overflow-hidden transition-shadow duration-200',
        borderColor,
        expanded ? 'shadow-card-hover' : 'shadow-card hover:shadow-card-hover'
      )}
    >
      <button
        className="w-full text-left p-5"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start gap-4">
          {/* Rank */}
          <div className="shrink-0 w-7 h-7 rounded-full bg-surface-900 text-white text-xs font-bold flex items-center justify-center">
            {rank}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-base">{insightTypeIcon(insight.insight_type)}</span>
                  <span className="text-xs font-medium text-surface-500 uppercase tracking-wide">
                    {insightTypeLabel(insight.insight_type)}
                  </span>
                </div>
                <h3 className="font-semibold text-surface-900 leading-snug">{insight.title}</h3>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <ConfidenceBadge confidence={insight.confidence} />
                {expanded ? (
                  <ChevronUp className="w-4 h-4 text-surface-400" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-surface-400" />
                )}
              </div>
            </div>

            {/* Quick stats */}
            <div className="flex items-center gap-4 mt-2">
              <span className="text-xs text-surface-500">
                <strong className="text-surface-700">{formatNumber(insight.support_count)}</strong> cases affected
              </span>
              {insight.impacted_population_pct > 0 && (
                <span className="text-xs text-surface-500">
                  <strong className="text-surface-700">{insight.impacted_population_pct.toFixed(1)}%</strong> of total
                </span>
              )}
              <span className="text-xs text-surface-500">
                Effect: <strong className="text-surface-700">{insight.effect_size.toFixed(2)}x</strong>
              </span>
            </div>

            {!expanded && (
              <p className="text-sm text-surface-600 mt-2 line-clamp-2">
                {insight.description_seed}
              </p>
            )}
          </div>
        </div>
      </button>

      {expanded && (
        <div className="px-5 pb-5 space-y-4 animate-slide-up">
          <div className="border-t border-surface-200 pt-4">
            {/* Full description */}
            <p className="text-sm text-surface-700 leading-relaxed">{insight.description_seed}</p>
          </div>

          {/* Why it matters */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-xs font-semibold text-surface-500 uppercase tracking-wide mb-2">Evidence</p>
              <div className="space-y-1">
                {Object.entries(insight.evidence_refs).map(([key, val]) => (
                  <div key={key} className="flex justify-between text-xs">
                    <span className="text-surface-500">{key.replace(/_/g, ' ')}</span>
                    <span className="font-medium text-surface-900 ml-2 truncate">
                      {typeof val === 'number' ? (Number.isInteger(val) ? formatNumber(val) : val.toFixed(2)) : String(val)}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <p className="text-xs font-semibold text-surface-500 uppercase tracking-wide mb-2">Metrics</p>
              <div className="space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-surface-500">Support count</span>
                  <span className="font-medium text-surface-900">{formatNumber(insight.support_count)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-surface-500">Effect size</span>
                  <span className="font-medium text-surface-900">{insight.effect_size.toFixed(3)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-surface-500">Confidence</span>
                  <span className="font-medium text-surface-900">{(insight.confidence * 100).toFixed(0)}%</span>
                </div>
                {insight.comparison_baseline && (
                  <div className="flex justify-between">
                    <span className="text-surface-500">Baseline</span>
                    <span className="font-medium text-surface-900 text-right max-w-[160px] truncate">{insight.comparison_baseline}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Recommended action */}
          <div className="bg-primary-50 border border-primary-100 rounded-lg p-3 flex gap-3">
            <ArrowRight className="w-4 h-4 text-primary-600 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs font-semibold text-primary-700 mb-0.5">Recommended Action</p>
              <p className="text-sm text-primary-800">{insight.recommended_action_seed}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
