import { cn, scoreColor } from '../../lib/utils';

interface Props {
  label: string;
  score: number;
  description?: string;
}

export function ScoreGauge({ label, score, description }: Props) {
  const color = score >= 70 ? 'bg-success-500' : score >= 40 ? 'bg-warning-500' : 'bg-danger-500';

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-surface-700">{label}</span>
        <span className={cn('text-sm font-bold', scoreColor(score))}>
          {score.toFixed(0)}
        </span>
      </div>
      <div className="w-full bg-surface-100 rounded-full h-2">
        <div
          className={cn('h-2 rounded-full transition-all duration-500', color)}
          style={{ width: `${Math.min(100, score)}%` }}
        />
      </div>
      {description && (
        <p className="text-xs text-surface-500">{description}</p>
      )}
    </div>
  );
}
