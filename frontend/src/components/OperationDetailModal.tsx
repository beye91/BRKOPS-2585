'use client';

import { motion } from 'framer-motion';
import {
  X,
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  PauseCircle,
  Calendar,
  FileText,
  Mic,
} from 'lucide-react';
import { Operation } from '@/store/operations';
import { Pipeline } from './Pipeline';
import { cn, formatDate, PIPELINE_STAGES } from '@/lib/utils';

interface OperationDetailModalProps {
  operation: Operation;
  onClose: () => void;
  onRefresh?: () => void;
}

export function OperationDetailModal({ operation, onClose, onRefresh }: OperationDetailModalProps) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-6 h-6 text-success" />;
      case 'failed':
        return <XCircle className="w-6 h-6 text-error" />;
      case 'running':
        return <Loader2 className="w-6 h-6 text-primary animate-spin" />;
      case 'paused':
        return <PauseCircle className="w-6 h-6 text-warning" />;
      default:
        return <Clock className="w-6 h-6 text-text-muted" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-success/10 text-success border-success/20';
      case 'failed':
        return 'bg-error/10 text-error border-error/20';
      case 'running':
        return 'bg-primary/10 text-primary border-primary/20';
      case 'paused':
        return 'bg-warning/10 text-warning border-warning/20';
      default:
        return 'bg-background text-text-muted border-border';
    }
  };

  const calculateDuration = (): string | null => {
    if (!operation.started_at) return null;
    const start = new Date(operation.started_at).getTime();
    const end = operation.completed_at ? new Date(operation.completed_at).getTime() : Date.now();
    const seconds = (end - start) / 1000;

    if (seconds < 60) return `${Math.round(seconds)} seconds`;
    if (seconds < 3600) {
      const mins = Math.floor(seconds / 60);
      const secs = Math.round(seconds % 60);
      return `${mins}m ${secs}s`;
    }
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${mins}m`;
  };

  const duration = calculateDuration();

  // Count completed stages
  const completedStages = Object.values(operation.stages || {}).filter(
    (stage) => stage.status === 'completed'
  ).length;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        transition={{ type: 'spring', duration: 0.3 }}
        className="bg-background-elevated rounded-xl border border-border shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-3">
            {getStatusIcon(operation.status)}
            <div>
              <h3 className="font-semibold">Operation Details</h3>
              <p className="text-sm text-text-secondary">
                {operation.use_case_name?.replace(/_/g, ' ')}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-background transition-colors"
          >
            <X className="w-5 h-5 text-text-secondary" />
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto max-h-[calc(90vh-80px)]">
          {/* Summary Section */}
          <div className="p-4 border-b border-border">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {/* Status */}
              <div className="bg-background rounded-lg p-3">
                <span className="text-xs text-text-muted block mb-1">Status</span>
                <span
                  className={cn(
                    'inline-flex items-center gap-1 px-2 py-1 rounded text-sm font-medium border',
                    getStatusColor(operation.status)
                  )}
                >
                  {operation.status.toUpperCase()}
                </span>
              </div>

              {/* Current Stage */}
              <div className="bg-background rounded-lg p-3">
                <span className="text-xs text-text-muted block mb-1">Current Stage</span>
                <span className="text-sm font-medium">
                  {operation.current_stage?.replace(/_/g, ' ') || 'N/A'}
                </span>
              </div>

              {/* Progress */}
              <div className="bg-background rounded-lg p-3">
                <span className="text-xs text-text-muted block mb-1">Progress</span>
                <span className="text-sm font-medium">
                  {completedStages} / {PIPELINE_STAGES.length} stages
                </span>
              </div>

              {/* Duration */}
              <div className="bg-background rounded-lg p-3">
                <span className="text-xs text-text-muted block mb-1">Duration</span>
                <span className="text-sm font-medium">{duration || 'N/A'}</span>
              </div>
            </div>
          </div>

          {/* Input Section */}
          <div className="p-4 border-b border-border">
            <div className="flex items-center gap-2 mb-2">
              <Mic className="w-4 h-4 text-primary" />
              <h4 className="font-medium">Input Command</h4>
            </div>
            <div className="bg-background rounded-lg p-3">
              <p className="text-sm italic text-text-primary">
                "{operation.input_text || 'No input provided'}"
              </p>
            </div>
          </div>

          {/* Pipeline Section */}
          <div className="p-4 border-b border-border">
            <Pipeline
              stages={PIPELINE_STAGES}
              currentStage={operation.current_stage || ''}
              stagesData={operation.stages || {}}
              isPaused={operation.status === 'paused'}
              operationId={operation.id}
              onRefresh={onRefresh}
            />
          </div>

          {/* Timestamps Section */}
          <div className="p-4 border-b border-border">
            <div className="flex items-center gap-2 mb-2">
              <Calendar className="w-4 h-4 text-primary" />
              <h4 className="font-medium">Timeline</h4>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-background rounded-lg p-3">
                <span className="text-xs text-text-muted block mb-1">Created</span>
                <span className="text-sm">{formatDate(operation.created_at)}</span>
              </div>
              {operation.started_at && (
                <div className="bg-background rounded-lg p-3">
                  <span className="text-xs text-text-muted block mb-1">Started</span>
                  <span className="text-sm">{formatDate(operation.started_at)}</span>
                </div>
              )}
              {operation.completed_at && (
                <div className="bg-background rounded-lg p-3">
                  <span className="text-xs text-text-muted block mb-1">Completed</span>
                  <span className="text-sm">{formatDate(operation.completed_at)}</span>
                </div>
              )}
            </div>
          </div>

          {/* Error Section (if any) */}
          {operation.error_message && (
            <div className="p-4 border-b border-border">
              <div className="bg-error/10 border border-error/20 rounded-lg p-4">
                <div className="flex items-center gap-2 text-error mb-2">
                  <XCircle className="w-4 h-4" />
                  <span className="font-medium">Error</span>
                </div>
                <p className="text-sm text-error">{operation.error_message}</p>
              </div>
            </div>
          )}

          {/* Result Section (if completed) */}
          {operation.result && (
            <div className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <FileText className="w-4 h-4 text-primary" />
                <h4 className="font-medium">Result</h4>
              </div>
              <pre className="bg-background rounded-lg p-3 text-xs font-mono overflow-x-auto">
                {JSON.stringify(operation.result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}
