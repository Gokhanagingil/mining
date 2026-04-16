import { cn, statusColor } from '../../lib/utils';
import { Loader2 } from 'lucide-react';

interface Props {
  status: string;
  className?: string;
}

const ACTIVE_STATUSES = ['profiling', 'analyzing'];

const STATUS_LABELS: Record<string, string> = {
  uploaded: 'Uploaded',
  profiling: 'Profiling...',
  'awaiting-mapping': 'Awaiting Mapping',
  analyzing: 'Analyzing...',
  completed: 'Completed',
  failed: 'Failed',
  pending: 'Pending',
  running: 'Running',
};

export function StatusBadge({ status, className }: Props) {
  const isActive = ACTIVE_STATUSES.includes(status);
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border',
        statusColor(status),
        className
      )}
    >
      {isActive && <Loader2 className="w-3 h-3 animate-spin" />}
      {STATUS_LABELS[status] || status}
    </span>
  );
}
