'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  CheckCircle2,
  XCircle,
  MessageSquare,
  AlertTriangle,
  Coffee,
} from 'lucide-react';
import { cn, getSeverityColor } from '@/lib/utils';

interface ApprovalPanelProps {
  analysis?: any;
  config?: any;
  onApprove: (approved: boolean, comment?: string) => void;
}

export function ApprovalPanel({ analysis, config, onApprove }: ApprovalPanelProps) {
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (approved: boolean) => {
    setIsSubmitting(true);
    await onApprove(approved, comment || undefined);
    setIsSubmitting(false);
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="bg-background-elevated rounded-xl border-2 border-primary p-6 shadow-glow-primary"
    >
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
          <AlertTriangle className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h3 className="font-semibold">Human Decision Required</h3>
          <p className="text-sm text-text-secondary">Review and approve or reject this operation</p>
        </div>
      </div>

      {/* Summary */}
      {analysis && (
        <div className={cn(
          'p-3 rounded-lg mb-4',
          getSeverityColor(analysis.severity)
        )}>
          <div className="flex items-center gap-2">
            <span className="font-medium">Analysis:</span>
            <span>{analysis.severity}</span>
          </div>
          <p className="text-sm mt-1">{analysis.recommendation}</p>
        </div>
      )}

      {/* Config Preview */}
      {config?.commands && (
        <div className="mb-4">
          <label className="text-sm font-medium text-text-secondary mb-2 block">
            Commands to Apply
          </label>
          <pre className="p-3 bg-background rounded-lg font-mono text-xs text-primary max-h-32 overflow-y-auto">
            {config.commands.slice(0, 5).join('\n')}
            {config.commands.length > 5 && `\n... and ${config.commands.length - 5} more`}
          </pre>
        </div>
      )}

      {/* Comment */}
      <div className="mb-4">
        <label className="text-sm font-medium text-text-secondary mb-2 block">
          <MessageSquare className="w-4 h-4 inline mr-1" />
          Comment (optional)
        </label>
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Add a comment for this decision..."
          className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm resize-none h-20 focus:outline-none focus:border-primary"
        />
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={() => handleSubmit(true)}
          disabled={isSubmitting}
          className="flex-1 py-3 bg-success text-white rounded-lg font-medium flex items-center justify-center gap-2 hover:bg-success/90 transition-colors disabled:opacity-50"
        >
          <CheckCircle2 className="w-5 h-5" />
          Approve
        </button>
        <button
          onClick={() => handleSubmit(false)}
          disabled={isSubmitting}
          className="flex-1 py-3 bg-error text-white rounded-lg font-medium flex items-center justify-center gap-2 hover:bg-error/90 transition-colors disabled:opacity-50"
        >
          <XCircle className="w-5 h-5" />
          Reject
        </button>
      </div>

      {/* Fun Message */}
      <div className="mt-4 pt-4 border-t border-border text-center">
        <p className="text-sm text-text-muted flex items-center justify-center gap-2">
          <Coffee className="w-4 h-4" />
          Morning coffee, stress-free
        </p>
      </div>
    </motion.div>
  );
}
