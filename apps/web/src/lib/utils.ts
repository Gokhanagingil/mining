import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export function formatNumber(n: number): string {
  return new Intl.NumberFormat('en-US').format(n);
}

export function formatDuration(minutes: number): string {
  if (minutes < 60) return `${Math.round(minutes)} min`;
  if (minutes < 1440) return `${(minutes / 60).toFixed(1)} hrs`;
  return `${(minutes / 1440).toFixed(1)} days`;
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatPercent(n: number, decimals = 1): string {
  return `${n.toFixed(decimals)}%`;
}

export function confidenceLabel(confidence: number): 'high' | 'medium' | 'low' {
  if (confidence >= 0.75) return 'high';
  if (confidence >= 0.50) return 'medium';
  return 'low';
}

export function confidenceColor(confidence: number): string {
  if (confidence >= 0.75) return 'text-success-700 bg-success-50 border-green-200';
  if (confidence >= 0.50) return 'text-warning-700 bg-warning-50 border-yellow-200';
  return 'text-danger-700 bg-danger-50 border-red-200';
}

export function severityColor(severity: string): string {
  switch (severity) {
    case 'critical': return 'text-red-700 bg-red-50 border-red-200';
    case 'high': return 'text-orange-700 bg-orange-50 border-orange-200';
    case 'medium': return 'text-yellow-700 bg-yellow-50 border-yellow-200';
    default: return 'text-blue-700 bg-blue-50 border-blue-200';
  }
}

export function statusColor(status: string): string {
  switch (status) {
    case 'completed': return 'text-success-700 bg-success-50 border-green-200';
    case 'analyzing':
    case 'profiling': return 'text-blue-700 bg-blue-50 border-blue-200';
    case 'failed': return 'text-danger-700 bg-danger-50 border-red-200';
    case 'awaiting-mapping': return 'text-warning-700 bg-warning-50 border-yellow-200';
    default: return 'text-surface-600 bg-surface-50 border-surface-200';
  }
}

export function insightTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    temporal_spike: 'Temporal Spike',
    workload_imbalance: 'Workload Imbalance',
    customer_specific_delay: 'Customer Delay',
    assignee_performance_gap: 'Performance Gap',
    category_recurrence: 'Category Pattern',
    satisfaction_degradation: 'Satisfaction Issue',
    self_service_opportunity: 'Self-Service Opportunity',
    routing_problem: 'Routing Problem',
    queue_bottleneck: 'Queue Bottleneck',
    rework_loop_pattern: 'Rework Loop',
    outlier_case: 'Outlier Case',
    backlog_aging: 'Backlog Aging',
  };
  return labels[type] || type;
}

export function insightTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    temporal_spike: '📈',
    workload_imbalance: '⚖️',
    customer_specific_delay: '👤',
    assignee_performance_gap: '🔍',
    category_recurrence: '🔁',
    satisfaction_degradation: '😟',
    self_service_opportunity: '🤖',
    routing_problem: '🔀',
    queue_bottleneck: '🚧',
    rework_loop_pattern: '↩️',
    outlier_case: '⚠️',
    backlog_aging: '⏳',
  };
  return icons[type] || '📊';
}

export function effortColor(effort: string): string {
  switch (effort) {
    case 'low': return 'text-success-700 bg-success-50';
    case 'medium': return 'text-warning-700 bg-warning-50';
    case 'high': return 'text-danger-700 bg-danger-50';
    default: return 'text-surface-600 bg-surface-100';
  }
}

export function scoreColor(score: number): string {
  if (score >= 70) return 'text-success-600';
  if (score >= 40) return 'text-warning-600';
  return 'text-danger-600';
}
