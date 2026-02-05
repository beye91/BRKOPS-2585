'use client';

import { motion } from 'framer-motion';
import {
  X,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  Loader2,
  FileCode,
  ArrowRight,
} from 'lucide-react';
import { cn, calculateStageDuration, formatStageDuration, formatDate } from '@/lib/utils';

interface Stage {
  key: string;
  name: string;
  description: string;
}

interface StageData {
  status: string;
  data?: any;
  error?: string;
  started_at?: string;
  completed_at?: string;
}

interface StageDetailModalProps {
  stage: Stage;
  stageData: StageData;
  onClose: () => void;
}

export function StageDetailModal({ stage, stageData, onClose }: StageDetailModalProps) {
  const duration = calculateStageDuration(stageData);
  const status = stageData.status;

  const getStatusIcon = () => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-6 h-6 text-success" />;
      case 'failed':
        return <XCircle className="w-6 h-6 text-error" />;
      case 'running':
        return <Loader2 className="w-6 h-6 text-primary animate-spin" />;
      default:
        return <Clock className="w-6 h-6 text-text-muted" />;
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'completed':
        return 'bg-success/10 text-success border-success/20';
      case 'failed':
        return 'bg-error/10 text-error border-error/20';
      case 'running':
        return 'bg-primary/10 text-primary border-primary/20';
      default:
        return 'bg-background-elevated text-text-muted border-border';
    }
  };

  // Format the data for display
  const renderDataSection = () => {
    if (!stageData.data) return null;

    const data = stageData.data;

    // Special rendering for different stage types
    switch (stage.key) {
      case 'voice_input':
        return (
          <div className="space-y-3">
            <h4 className="font-medium text-sm text-text-secondary">Transcript</h4>
            <p className="text-text-primary bg-background p-3 rounded-lg italic">
              "{data.transcript}"
            </p>
          </div>
        );

      case 'intent_parsing':
        return (
          <div className="space-y-3">
            <h4 className="font-medium text-sm text-text-secondary">Parsed Intent</h4>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-background p-3 rounded-lg">
                <span className="text-xs text-text-muted">Action</span>
                <p className="font-medium">{data.action}</p>
              </div>
              <div className="bg-background p-3 rounded-lg">
                <span className="text-xs text-text-muted">Confidence</span>
                <p className="font-medium">{data.confidence}%</p>
              </div>
            </div>
            {data.target_devices && (
              <div className="bg-background p-3 rounded-lg">
                <span className="text-xs text-text-muted">Target Devices</span>
                <div className="flex gap-2 mt-1">
                  {data.target_devices.map((device: string) => (
                    <span key={device} className="px-2 py-1 bg-primary/10 text-primary rounded text-sm">
                      {device}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        );

      case 'config_generation':
        return (
          <div className="space-y-3">
            <h4 className="font-medium text-sm text-text-secondary">Generated Commands</h4>
            <pre className="text-xs font-mono bg-background p-3 rounded-lg overflow-x-auto text-primary">
              {data.commands?.join('\n')}
            </pre>
            {data.rollback_commands && (
              <>
                <h4 className="font-medium text-sm text-text-secondary mt-4">Rollback Commands</h4>
                <pre className="text-xs font-mono bg-background p-3 rounded-lg overflow-x-auto text-warning">
                  {data.rollback_commands?.join('\n')}
                </pre>
              </>
            )}
            {data.risk_level && (
              <div className="flex items-center gap-2">
                <AlertTriangle className={cn(
                  'w-4 h-4',
                  data.risk_level === 'high' && 'text-error',
                  data.risk_level === 'medium' && 'text-warning',
                  data.risk_level === 'low' && 'text-success'
                )} />
                <span className="text-sm">Risk Level: {data.risk_level}</span>
              </div>
            )}
          </div>
        );

      case 'ai_advice':
        return (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className={cn(
                'px-2 py-1 rounded text-sm font-medium',
                data.recommendation === 'APPROVE' && 'bg-success/10 text-success',
                data.recommendation === 'REVIEW' && 'bg-warning/10 text-warning',
                data.recommendation === 'REJECT' && 'bg-error/10 text-error'
              )}>
                Recommendation: {data.recommendation}
              </span>
              <span className={cn(
                'px-2 py-1 rounded text-sm',
                data.risk_level === 'HIGH' && 'bg-error/10 text-error',
                data.risk_level === 'MEDIUM' && 'bg-warning/10 text-warning',
                data.risk_level === 'LOW' && 'bg-success/10 text-success'
              )}>
                Risk: {data.risk_level}
              </span>
            </div>
            {data.risk_factors && (
              <div className="bg-background p-3 rounded-lg">
                <span className="text-xs text-text-muted">Risk Factors</span>
                <ul className="mt-1 space-y-1">
                  {data.risk_factors.map((factor: string, i: number) => (
                    <li key={i} className="text-sm flex items-start gap-2">
                      <ArrowRight className="w-3 h-3 mt-1 text-warning shrink-0" />
                      {factor}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {data.pre_checks && (
              <div className="bg-background p-3 rounded-lg">
                <span className="text-xs text-text-muted">Pre-Deployment Checks</span>
                <ul className="mt-1 space-y-1">
                  {data.pre_checks.map((check: string, i: number) => (
                    <li key={i} className="text-sm flex items-start gap-2">
                      <CheckCircle2 className="w-3 h-3 mt-1 text-primary shrink-0" />
                      {check}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        );

      case 'human_decision':
        // Handle awaiting approval state (before user decision)
        if (data.awaiting_approval) {
          return (
            <div className="space-y-3">
              <div className="p-3 rounded-lg border bg-warning/10 border-warning/20">
                <span className="text-sm font-medium text-warning">Awaiting Approval</span>
                <p className="text-sm mt-1 text-text-muted">{data.message || 'Waiting for human decision...'}</p>
              </div>
              {data.ai_advice && (
                <div className="bg-background p-3 rounded-lg">
                  <span className="text-xs text-text-muted">AI Recommendation</span>
                  <p className="font-medium">{data.ai_advice.recommendation || 'N/A'}</p>
                </div>
              )}
            </div>
          );
        }
        // Handle approved/rejected state (after user decision)
        return (
          <div className="space-y-3">
            <div className={cn(
              'p-3 rounded-lg border',
              data.approved ? 'bg-success/10 border-success/20' : 'bg-error/10 border-error/20'
            )}>
              <span className="text-sm font-medium">
                {data.approved ? 'Approved' : 'Rejected'}
              </span>
              {data.comment && (
                <p className="text-sm mt-1">{data.comment}</p>
              )}
              {data.decided_at && (
                <p className="text-xs text-text-muted mt-2">
                  Decision made at {formatDate(data.decided_at)}
                </p>
              )}
            </div>
          </div>
        );

      case 'cml_deployment':
        return (
          <div className="space-y-3">
            <div className={cn(
              'p-3 rounded-lg border',
              data.deployed ? 'bg-success/10 border-success/20' : 'bg-error/10 border-error/20'
            )}>
              <span className="text-sm font-medium">
                {data.deployed ? 'Successfully Deployed' : 'Deployment Failed'}
              </span>
            </div>
            {data.deployed && (
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-background p-3 rounded-lg">
                  <span className="text-xs text-text-muted">Device</span>
                  <p className="font-medium">{data.device}</p>
                </div>
                <div className="bg-background p-3 rounded-lg">
                  <span className="text-xs text-text-muted">Commands Applied</span>
                  <p className="font-medium">{data.commands_applied}</p>
                </div>
              </div>
            )}
            {data.error && (
              <div className="bg-error/10 border border-error/20 p-3 rounded-lg">
                <p className="text-sm text-error">{data.error}</p>
              </div>
            )}
          </div>
        );

      case 'ai_validation':
        return (
          <div className="space-y-3">
            <div className={cn(
              'p-3 rounded-lg border',
              data.validation_status === 'PASSED' && 'bg-success/10 border-success/20',
              data.validation_status === 'WARNING' && 'bg-warning/10 border-warning/20',
              data.validation_status === 'FAILED' && 'bg-error/10 border-error/20'
            )}>
              <span className="text-sm font-medium">
                Validation: {data.validation_status || data.status}
              </span>
              {data.overall_score && (
                <span className="ml-2 text-sm">Score: {data.overall_score}/100</span>
              )}
            </div>
            {data.findings && (
              <div className="bg-background p-3 rounded-lg">
                <span className="text-xs text-text-muted">Findings</span>
                <ul className="mt-1 space-y-2">
                  {data.findings.map((finding: any, i: number) => (
                    <li key={i} className="text-sm flex items-start gap-2">
                      <span className={cn(
                        'w-2 h-2 rounded-full mt-1.5 shrink-0',
                        finding.status === 'ok' && 'bg-success',
                        finding.status === 'warning' && 'bg-warning',
                        finding.status === 'error' && 'bg-error'
                      )} />
                      <span>
                        <strong>{finding.category}:</strong> {finding.message}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        );

      case 'monitoring':
        return (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-background p-3 rounded-lg">
                <span className="text-xs text-text-muted">Convergence Wait</span>
                <p className="font-medium">{data.wait_seconds}s</p>
              </div>
              <div className="bg-background p-3 rounded-lg">
                <span className="text-xs text-text-muted">Device Monitored</span>
                <p className="font-medium">{data.device || 'N/A'}</p>
              </div>
            </div>

            {/* OSPF Neighbors */}
            {data.ospf_neighbors && data.ospf_neighbors.length > 0 && (
              <div className="bg-background p-3 rounded-lg">
                <span className="text-xs text-text-muted">OSPF Neighbors ({data.ospf_neighbor_count || data.ospf_neighbors.length})</span>
                <div className="mt-2 space-y-1">
                  {data.ospf_neighbors.map((neighbor: any, i: number) => (
                    <div key={i} className="flex items-center justify-between text-sm">
                      <span className="font-mono">{neighbor.neighbor_id}</span>
                      <span className={cn(
                        'px-2 py-0.5 rounded text-xs',
                        neighbor.state?.includes('FULL') ? 'bg-success/20 text-success' : 'bg-warning/20 text-warning'
                      )}>
                        {neighbor.state}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Interface Status */}
            {data.interface_status && data.interface_status.length > 0 && (
              <div className="bg-background p-3 rounded-lg">
                <span className="text-xs text-text-muted">Interface Status</span>
                <div className="mt-2 space-y-1 max-h-32 overflow-y-auto">
                  {data.interface_status.map((iface: any, i: number) => (
                    <div key={i} className="flex items-center justify-between text-sm">
                      <span className="font-mono text-xs">{iface.interface}</span>
                      <span className="text-xs text-text-muted">{iface.ip_address}</span>
                      <span className={cn(
                        'px-2 py-0.5 rounded text-xs',
                        iface.status === 'up' ? 'bg-success/20 text-success' : 'bg-error/20 text-error'
                      )}>
                        {iface.status}/{iface.protocol}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Checks Summary */}
            {data.checks && data.checks.length > 0 && (
              <div className="bg-background p-3 rounded-lg">
                <span className="text-xs text-text-muted">Monitoring Checks</span>
                <ul className="mt-2 space-y-1">
                  {data.checks.map((check: any, i: number) => (
                    <li key={i} className="flex items-center gap-2 text-sm">
                      {check.status === 'completed' ? (
                        <CheckCircle2 className="w-3 h-3 text-success" />
                      ) : (
                        <AlertTriangle className="w-3 h-3 text-warning" />
                      )}
                      <span>{check.name}</span>
                      {check.message && <span className="text-text-muted text-xs">- {check.message}</span>}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Errors */}
            {data.errors && data.errors.length > 0 && (
              <div className="bg-error/10 border border-error/20 p-3 rounded-lg">
                <span className="text-xs text-error font-medium">Errors</span>
                <ul className="mt-1 space-y-1">
                  {data.errors.map((error: string, i: number) => (
                    <li key={i} className="text-sm text-error">{error}</li>
                  ))}
                </ul>
              </div>
            )}

            {data.monitoring_complete && !data.errors?.length && (
              <div className="flex items-center gap-2 text-success">
                <CheckCircle2 className="w-4 h-4" />
                <span className="text-sm">
                  Monitoring complete
                  {data.convergence_detected && ' - OSPF converged'}
                </span>
              </div>
            )}
          </div>
        );

      case 'splunk_analysis':
        return (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-background p-3 rounded-lg">
                <span className="text-xs text-text-muted">Query Status</span>
                <p className="font-medium">{data.queried ? 'Success' : 'Failed'}</p>
              </div>
              <div className="bg-background p-3 rounded-lg">
                <span className="text-xs text-text-muted">Results</span>
                <p className="font-medium">{data.result_count || 0} events</p>
              </div>
            </div>
            {data.results && data.results.length > 0 && (
              <div className="bg-background p-3 rounded-lg max-h-40 overflow-y-auto">
                <span className="text-xs text-text-muted">Sample Results</span>
                <pre className="text-xs font-mono mt-1">
                  {JSON.stringify(data.results.slice(0, 3), null, 2)}
                </pre>
              </div>
            )}
          </div>
        );

      case 'notifications':
        return (
          <div className="space-y-3">
            <div className="bg-background p-3 rounded-lg">
              <span className="text-xs text-text-muted">Notifications Sent</span>
              <p className="font-medium">{data.notifications_sent || 0}</p>
            </div>
            {data.results && data.results.length > 0 && (
              <div className="space-y-2">
                {data.results.map((result: any, i: number) => (
                  <div key={i} className="flex items-center gap-2 text-sm">
                    {result.success ? (
                      <CheckCircle2 className="w-4 h-4 text-success" />
                    ) : (
                      <XCircle className="w-4 h-4 text-error" />
                    )}
                    <span className="capitalize">{result.channel}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        );

      default:
        return (
          <pre className="text-xs font-mono bg-background p-3 rounded-lg overflow-x-auto">
            {JSON.stringify(data, null, 2)}
          </pre>
        );
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        transition={{ type: 'spring', duration: 0.3 }}
        className="bg-background-elevated rounded-xl border border-border shadow-xl w-full max-w-lg mx-4 max-h-[80vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-3">
            {getStatusIcon()}
            <div>
              <h3 className="font-semibold">{stage.name}</h3>
              <p className="text-sm text-text-secondary">{stage.description}</p>
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
        <div className="p-4 overflow-y-auto max-h-[60vh]">
          {/* Status and Timing */}
          <div className="flex items-center gap-3 mb-4">
            <span className={cn('px-2 py-1 rounded text-sm border capitalize', getStatusColor())}>
              {status}
            </span>
            {duration !== null && (
              <span className="text-sm text-text-secondary flex items-center gap-1">
                <Clock className="w-4 h-4" />
                Duration: {formatStageDuration(duration)}
              </span>
            )}
          </div>

          {/* Timing Details */}
          {stageData.started_at && (
            <div className="mb-4 text-sm text-text-secondary">
              <div>Started: {formatDate(stageData.started_at)}</div>
              {stageData.completed_at && (
                <div>Completed: {formatDate(stageData.completed_at)}</div>
              )}
            </div>
          )}

          {/* Error Display */}
          {stageData.error && (
            <div className="mb-4 p-3 bg-error/10 border border-error/20 rounded-lg">
              <div className="flex items-center gap-2 text-error mb-1">
                <XCircle className="w-4 h-4" />
                <span className="font-medium">Error</span>
              </div>
              <p className="text-sm text-error">{stageData.error}</p>
            </div>
          )}

          {/* Stage Data */}
          {renderDataSection()}
        </div>
      </motion.div>
    </motion.div>
  );
}
