'use client';

import { useRef, useEffect, useState } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { Search, Filter, AlertTriangle, Info, AlertCircle, Bug } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LogEntry {
  _time?: string;
  _raw?: string;
  host?: string;
  source?: string;
  sourcetype?: string;
  message?: string;
  level?: string;
  [key: string]: any;
}

interface LogStreamProps {
  logs: LogEntry[];
  operationStatus?: string;
  operationStage?: string;
}

export function LogStream({ logs, operationStatus, operationStage }: LogStreamProps) {
  const parentRef = useRef<HTMLDivElement>(null);
  const [filter, setFilter] = useState('');
  const [levelFilter, setLevelFilter] = useState<string>('all');
  const [autoScroll, setAutoScroll] = useState(true);

  // Filter logs
  const filteredLogs = logs.filter((log) => {
    const text = log._raw || log.message || JSON.stringify(log);
    const matchesText = filter === '' || text.toLowerCase().includes(filter.toLowerCase());
    const matchesLevel =
      levelFilter === 'all' ||
      (log.level?.toLowerCase() || 'info') === levelFilter.toLowerCase();
    return matchesText && matchesLevel;
  });

  // Virtual list for performance
  const virtualizer = useVirtualizer({
    count: filteredLogs.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 60,
    overscan: 5,
  });

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && parentRef.current) {
      parentRef.current.scrollTop = parentRef.current.scrollHeight;
    }
  }, [logs.length, autoScroll]);

  const getLevelIcon = (level?: string) => {
    switch (level?.toLowerCase()) {
      case 'error':
        return <AlertCircle className="w-4 h-4 text-error" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-warning" />;
      case 'debug':
        return <Bug className="w-4 h-4 text-text-muted" />;
      default:
        return <Info className="w-4 h-4 text-primary" />;
    }
  };

  const getLevelColor = (level?: string) => {
    switch (level?.toLowerCase()) {
      case 'error':
        return 'border-l-error';
      case 'warning':
        return 'border-l-warning';
      case 'debug':
        return 'border-l-text-muted';
      default:
        return 'border-l-primary';
    }
  };

  const formatLogMessage = (message: string): React.ReactNode => {
    // Highlight OSPF errors in red
    const ospfKeywords = /(%OSPF-[45]-\w+|ERROR|FAILED|DOWN)/gi;
    const parts = message.split(ospfKeywords);

    return parts.map((part, i) =>
      ospfKeywords.test(part) ? (
        <span key={i} className="text-error font-semibold">{part}</span>
      ) : part
    );
  };

  return (
    <div className="bg-background-elevated rounded-xl border border-border overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold">Log Stream</h2>
          <div className="flex items-center gap-2">
            <span className="text-sm text-text-muted">
              {filteredLogs.length} of {logs.length} entries
            </span>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="rounded border-border"
              />
              Auto-scroll
            </label>
          </div>
        </div>

        <div className="flex gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
            <input
              type="text"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Search logs..."
              className="w-full pl-10 pr-4 py-2 bg-background border border-border rounded-lg text-sm focus:outline-none focus:border-primary"
            />
          </div>

          {/* Level Filter */}
          <select
            value={levelFilter}
            onChange={(e) => setLevelFilter(e.target.value)}
            className="px-3 py-2 bg-background border border-border rounded-lg text-sm"
          >
            <option value="all">All Levels</option>
            <option value="error">Error</option>
            <option value="warning">Warning</option>
            <option value="info">Info</option>
            <option value="debug">Debug</option>
          </select>
        </div>
      </div>

      {/* Log Entries */}
      <div
        ref={parentRef}
        className="h-[600px] overflow-auto"
        style={{ contain: 'strict' }}
      >
        {filteredLogs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-text-muted">
            <Info className="w-12 h-12 mb-4" />
            {!operationStatus ? (
              <>
                <p>Run a demo operation to collect network logs</p>
                <p className="text-sm mt-1">Splunk log data will stream here during the pipeline</p>
              </>
            ) : operationStatus === 'running' && operationStage && !['splunk_analysis', 'ai_validation', 'ai_advice', 'notification', 'human_decision', 'apply_config'].includes(operationStage) ? (
              <>
                <p>Waiting for Splunk analysis stage</p>
                <p className="text-sm mt-1">Logs will appear when the pipeline reaches the Splunk query step</p>
              </>
            ) : operationStatus === 'completed' || operationStage === 'splunk_analysis' ? (
              <>
                <p>Splunk query returned no log entries</p>
                <p className="text-sm mt-1">The query completed but no matching results were found</p>
              </>
            ) : (
              <>
                <p>No log entries found</p>
                <p className="text-sm mt-1">Logs will appear after Splunk analysis</p>
              </>
            )}
          </div>
        ) : (
          <div
            style={{
              height: `${virtualizer.getTotalSize()}px`,
              width: '100%',
              position: 'relative',
            }}
          >
            {virtualizer.getVirtualItems().map((virtualRow) => {
              const log = filteredLogs[virtualRow.index];
              return (
                <div
                  key={virtualRow.index}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: `${virtualRow.size}px`,
                    transform: `translateY(${virtualRow.start}px)`,
                  }}
                  className={cn(
                    'px-4 py-2 border-b border-border border-l-4 hover:bg-background/50',
                    getLevelColor(log.level)
                  )}
                >
                  <div className="flex items-start gap-3">
                    {getLevelIcon(log.level)}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        {log._time && (
                          <span className="text-xs text-text-muted font-mono">
                            {(() => {
                              try {
                                const date = new Date(log._time);
                                // Format as: Feb 5, 14:30:45 PST
                                return date.toLocaleString('en-US', {
                                  month: 'short',
                                  day: 'numeric',
                                  hour: '2-digit',
                                  minute: '2-digit',
                                  second: '2-digit',
                                  timeZoneName: 'short',
                                });
                              } catch (e) {
                                // Fallback to raw value if parsing fails
                                return log._time;
                              }
                            })()}
                          </span>
                        )}
                        {log.host && (
                          <span className="text-xs px-1.5 py-0.5 bg-primary/20 text-primary rounded">
                            {log.host}
                          </span>
                        )}
                        {log.sourcetype && (
                          <span className="text-xs text-text-muted">{log.sourcetype}</span>
                        )}
                      </div>
                      <pre className="text-sm text-text-primary font-mono whitespace-pre-wrap break-all">
                        {formatLogMessage(log._raw || log.message || JSON.stringify(log, null, 2))}
                      </pre>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
