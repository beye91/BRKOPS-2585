'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  History,
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  PauseCircle,
  Filter,
  RefreshCw,
  ChevronRight,
} from 'lucide-react';
import { operationsApi } from '@/services/api';
import { Operation } from '@/store/operations';
import { cn, truncate, formatDate } from '@/lib/utils';

type StatusFilter = 'all' | 'running' | 'completed' | 'failed' | 'paused';

interface OperationHistoryPanelProps {
  onSelectOperation: (operation: Operation) => void;
  currentOperationId?: string;
  limit?: number;
}

export function OperationHistoryPanel({
  onSelectOperation,
  currentOperationId,
  limit = 10,
}: OperationHistoryPanelProps) {
  const [operations, setOperations] = useState<Operation[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [refreshing, setRefreshing] = useState(false);

  const fetchOperations = useCallback(async () => {
    try {
      const params: { limit: number; status?: string } = { limit };
      if (statusFilter !== 'all') {
        params.status = statusFilter;
      }
      const response = await operationsApi.list(params);
      setOperations(response.data);
    } catch (error) {
      console.error('Failed to fetch operations:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [limit, statusFilter]);

  // Initial fetch
  useEffect(() => {
    fetchOperations();
  }, [fetchOperations]);

  // Auto-refresh every 10 seconds if there are active operations
  useEffect(() => {
    const hasActiveOps = operations.some((op) =>
      ['running', 'queued', 'paused'].includes(op.status)
    );

    if (!hasActiveOps) return;

    const interval = setInterval(() => {
      fetchOperations();
    }, 10000);

    return () => clearInterval(interval);
  }, [operations, fetchOperations]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchOperations();
  };

  const handleSelectOperation = async (operation: Operation) => {
    try {
      // Fetch full operation details
      const response = await operationsApi.get(operation.id);
      onSelectOperation(response.data);
    } catch (error) {
      console.error('Failed to fetch operation details:', error);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-4 h-4 text-success" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-error" />;
      case 'running':
        return <Loader2 className="w-4 h-4 text-primary animate-spin" />;
      case 'paused':
        return <PauseCircle className="w-4 h-4 text-warning" />;
      default:
        return <Clock className="w-4 h-4 text-text-muted" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-success/10 text-success';
      case 'failed':
        return 'bg-error/10 text-error';
      case 'running':
        return 'bg-primary/10 text-primary';
      case 'paused':
        return 'bg-warning/10 text-warning';
      default:
        return 'bg-background text-text-muted';
    }
  };

  const formatRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffInSeconds < 60) return 'Just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    return formatDate(dateString);
  };

  const calculateDuration = (op: Operation): string | null => {
    if (!op.started_at) return null;
    const start = new Date(op.started_at).getTime();
    const end = op.completed_at ? new Date(op.completed_at).getTime() : Date.now();
    const seconds = (end - start) / 1000;

    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  };

  const filterOptions: { value: StatusFilter; label: string }[] = [
    { value: 'all', label: 'All' },
    { value: 'running', label: 'Running' },
    { value: 'completed', label: 'Completed' },
    { value: 'failed', label: 'Failed' },
    { value: 'paused', label: 'Paused' },
  ];

  return (
    <div className="bg-background-elevated rounded-xl border border-border">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <History className="w-5 h-5 text-primary" />
          <h3 className="font-semibold">Operations History</h3>
        </div>
        <div className="flex items-center gap-3">
          {/* Status Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-text-muted" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
              className="bg-background border border-border rounded-lg px-2 py-1 text-sm focus:outline-none focus:border-primary"
            >
              {filterOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {/* Refresh Button */}
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-2 rounded-lg hover:bg-background transition-colors disabled:opacity-50"
            title="Refresh"
          >
            <RefreshCw className={cn('w-4 h-4 text-text-secondary', refreshing && 'animate-spin')} />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="max-h-[300px] overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 text-primary animate-spin" />
          </div>
        ) : operations.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-text-muted">
            <History className="w-8 h-8 mb-2 opacity-50" />
            <p className="text-sm">No operations found</p>
            {statusFilter !== 'all' && (
              <button
                onClick={() => setStatusFilter('all')}
                className="mt-2 text-xs text-primary hover:underline"
              >
                Clear filter
              </button>
            )}
          </div>
        ) : (
          <AnimatePresence mode="popLayout">
            {operations.map((operation) => {
              const isSelected = operation.id === currentOperationId;
              const duration = calculateDuration(operation);

              return (
                <motion.div
                  key={operation.id}
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  className={cn(
                    'flex items-center gap-3 p-3 border-b border-border/50 cursor-pointer transition-colors',
                    isSelected
                      ? 'bg-primary/10 border-l-2 border-l-primary'
                      : 'hover:bg-background'
                  )}
                  onClick={() => handleSelectOperation(operation)}
                >
                  {/* Status Icon */}
                  <div className="shrink-0">{getStatusIcon(operation.status)}</div>

                  {/* Main Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={cn('text-xs px-2 py-0.5 rounded', getStatusColor(operation.status))}>
                        {operation.status}
                      </span>
                      <span className="text-sm font-medium truncate">
                        {operation.use_case_name?.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <p className="text-xs text-text-secondary truncate mt-1">
                      {truncate(operation.input_text || 'No input', 50)}
                    </p>
                    <div className="flex items-center gap-2 mt-1 text-xs text-text-muted">
                      <span>{operation.current_stage?.replace(/_/g, ' ')}</span>
                      {duration && (
                        <>
                          <span>·</span>
                          <span>{duration}</span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Timestamp and Arrow */}
                  <div className="shrink-0 flex items-center gap-2">
                    <span className="text-xs text-text-muted">
                      {formatRelativeTime(operation.created_at)}
                    </span>
                    <ChevronRight className="w-4 h-4 text-text-muted" />
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
