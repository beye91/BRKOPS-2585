'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  CheckCircle2,
  XCircle,
  MessageSquare,
  AlertTriangle,
  Coffee,
  ShieldCheck,
  Lightbulb,
  ArrowRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface ApprovalPanelProps {
  analysis?: any; // This is now AI Advice (pre-deployment)
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

  // Determine recommendation styling
  const getRecommendationStyle = (rec: string) => {
    switch (rec?.toUpperCase()) {
      case 'APPROVE':
        return 'bg-success/10 text-success border-success/20';
      case 'REVIEW':
        return 'bg-warning/10 text-warning border-warning/20';
      case 'REJECT':
        return 'bg-error/10 text-error border-error/20';
      default:
        return 'bg-primary/10 text-primary border-primary/20';
    }
  };

  const getRiskStyle = (risk: string) => {
    switch (risk?.toUpperCase()) {
      case 'LOW':
        return 'bg-success/10 text-success';
      case 'MEDIUM':
        return 'bg-warning/10 text-warning';
      case 'HIGH':
        return 'bg-error/10 text-error';
      default:
        return 'bg-text-muted/10 text-text-muted';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="bg-background-elevated rounded-xl border-2 border-warning p-6 shadow-lg"
    >
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-full bg-warning/20 flex items-center justify-center animate-pulse">
          <ShieldCheck className="w-5 h-5 text-warning" />
        </div>
        <div>
          <h3 className="font-semibold">Pre-Deployment Approval Required</h3>
          <p className="text-sm text-text-secondary">Review the proposed changes before deployment</p>
        </div>
      </div>

      {/* AI Advice Summary */}
      {analysis && (
        <div className="mb-4 space-y-3">
          <div className="flex items-center gap-2">
            <Lightbulb className="w-4 h-4 text-primary" />
            <span className="text-sm font-medium">AI Advice</span>
          </div>

          <div className="flex gap-2">
            <span className={cn(
              'px-2 py-1 rounded text-sm border',
              getRecommendationStyle(analysis.recommendation)
            )}>
              {analysis.recommendation}
            </span>
            <span className={cn(
              'px-2 py-1 rounded text-sm',
              getRiskStyle(analysis.risk_level)
            )}>
              Risk: {analysis.risk_level}
            </span>
          </div>

          {analysis.recommendation_reason && (
            <p className="text-sm text-text-secondary">
              {analysis.recommendation_reason}
            </p>
          )}

          {/* Risk Factors */}
          {analysis.risk_factors && analysis.risk_factors.length > 0 && (
            <div className="bg-background p-3 rounded-lg">
              <span className="text-xs text-text-muted">Risk Factors</span>
              <ul className="mt-1 space-y-1">
                {analysis.risk_factors.slice(0, 3).map((factor: string, i: number) => (
                  <li key={i} className="text-sm flex items-start gap-2">
                    <AlertTriangle className="w-3 h-3 mt-1 text-warning shrink-0" />
                    {factor}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Pre-Checks */}
          {analysis.pre_checks && analysis.pre_checks.length > 0 && (
            <div className="bg-background p-3 rounded-lg">
              <span className="text-xs text-text-muted">Pre-Deployment Checks</span>
              <ul className="mt-1 space-y-1">
                {analysis.pre_checks.slice(0, 3).map((check: string, i: number) => (
                  <li key={i} className="text-sm flex items-start gap-2">
                    <CheckCircle2 className="w-3 h-3 mt-1 text-primary shrink-0" />
                    {check}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Config Preview */}
      {config?.commands && (
        <div className="mb-4">
          <label className="text-sm font-medium text-text-secondary mb-2 block">
            Commands to Deploy
          </label>
          <pre className="p-3 bg-background rounded-lg font-mono text-xs text-primary max-h-32 overflow-y-auto">
            {config.commands.slice(0, 5).join('\n')}
            {config.commands.length > 5 && `\n... and ${config.commands.length - 5} more`}
          </pre>
        </div>
      )}

      {/* Rollback Preview */}
      {config?.rollback_commands && config.rollback_commands.length > 0 && (
        <div className="mb-4">
          <label className="text-sm font-medium text-text-secondary mb-2 block flex items-center gap-1">
            <ArrowRight className="w-3 h-3 rotate-180" />
            Rollback Available
          </label>
          <div className="p-2 bg-success/10 rounded-lg text-xs text-success">
            {config.rollback_commands.length} rollback command(s) ready
          </div>
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
          Approve & Deploy
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
          Approve now, coffee first, deploy later
        </p>
      </div>
    </motion.div>
  );
}
