import { cn, confidenceColor } from '../../lib/utils';
import { ShieldCheck } from 'lucide-react';

interface Props {
  confidence: number;
  showIcon?: boolean;
  className?: string;
}

export function ConfidenceBadge({ confidence, showIcon = true, className }: Props) {
  const pct = Math.round(confidence * 100);
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border',
        confidenceColor(confidence),
        className
      )}
    >
      {showIcon && <ShieldCheck className="w-3 h-3" />}
      {pct}%
    </span>
  );
}
