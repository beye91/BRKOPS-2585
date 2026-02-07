/**
 * Error Summary Card Component
 *
 * Displays a count of errors across all severity levels.
 * Only shown when errors exist. Uses red glow for critical visibility.
 */

import { XCircle } from 'lucide-react';
import { ErrorSummary } from '@/lib/severity';

interface ErrorSummaryCardProps {
  summary: ErrorSummary;
  onViewDetails?: () => void;
}

export function ErrorSummaryCard({ summary, onViewDetails }: ErrorSummaryCardProps) {
  // Don't render if no errors
  if (summary.total === 0) return null;

  return (
    <div className="bg-error/20 border-l-8 border-error rounded-lg p-4 glow-critical">
      <h3 className="text-lg font-bold text-error mb-3 flex items-center gap-2">
        <XCircle className="w-5 h-5" />
        {summary.total} Issue{summary.total > 1 ? 's' : ''} Detected
      </h3>
      <div className="grid grid-cols-2 gap-2 mb-3">
        {summary.critical > 0 && (
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-error rounded-full" />
            <span className="text-sm font-medium">{summary.critical} Critical</span>
          </div>
        )}
        {summary.high > 0 && (
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-warning rounded-full" />
            <span className="text-sm font-medium">{summary.high} Warning</span>
          </div>
        )}
        {summary.medium > 0 && (
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-primary rounded-full" />
            <span className="text-sm font-medium">{summary.medium} Medium</span>
          </div>
        )}
        {summary.low > 0 && (
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-text-muted rounded-full" />
            <span className="text-sm font-medium">{summary.low} Low</span>
          </div>
        )}
      </div>
      {onViewDetails && (
        <button
          onClick={onViewDetails}
          className="text-sm underline hover:no-underline transition-all"
        >
          View Details →
        </button>
      )}
    </div>
  );
}
