'use client';

import { useState } from 'react';
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
  TrendingUp,
  TrendingDown,
  Minus,
  RotateCcw,
} from 'lucide-react';
import { cn, calculateStageDuration, formatStageDuration, formatDate } from '@/lib/utils';
import { operationsApi } from '@/services/api';
import { AlertBanner } from '@/components/AlertBanner';

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
  operationId?: string;
  rollbackCommands?: string[];
  rollbackStatus?: StageData;
  onRollbackComplete?: () => void;
  operation?: any;  // Full operation object for accessing all stages
}

export function StageDetailModal({
  stage,
  stageData,
  onClose,
  operationId,
  rollbackCommands = [],
  rollbackStatus,
  onRollbackComplete,
  operation,
}: StageDetailModalProps) {
  const [isRollingBack, setIsRollingBack] = useState(false);
  const [rollbackError, setRollbackError] = useState<string | null>(null);
  const [showRollbackConfirm, setShowRollbackConfirm] = useState(false);

  const duration = calculateStageDuration(stageData);
  const status = stageData.status;

  const handleRollback = async () => {
    if (!operationId) return;

    setIsRollingBack(true);
    setRollbackError(null);

    try {
      await operationsApi.rollback(operationId, 'Manual rollback from stage detail');
      setShowRollbackConfirm(false);
      onRollbackComplete?.();
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'Rollback failed';
      setRollbackError(message);
    } finally {
      setIsRollingBack(false);
    }
  };

  const canRollback =
    stage.key === 'cml_deployment' &&
    stageData.status === 'completed' &&
    stageData.data?.deployed &&
    rollbackCommands.length > 0 &&
    rollbackStatus?.status !== 'completed' &&
    operationId;

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
        const hasPerDevice = data.per_device_configs && Object.keys(data.per_device_configs).length > 0;
        const perDeviceEntries = hasPerDevice ? Object.entries(data.per_device_configs) : [];
        const showPerDevice = perDeviceEntries.length > 1;

        return (
          <div className="space-y-3">
            {/* Summary info */}
            {data.explanation && (
              <div className="bg-background p-3 rounded-lg">
                <span className="text-xs text-text-muted">Explanation</span>
                <p className="text-sm mt-1">{data.explanation}</p>
              </div>
            )}

            {/* Per-device configs when multiple devices */}
            {showPerDevice ? (
              <div className="space-y-3">
                <h4 className="font-medium text-sm text-text-secondary">Per-Device Commands</h4>
                {perDeviceEntries.map(([device, cfg]: [string, any]) => (
                  <div key={device} className="border border-border rounded-lg p-3">
                    <h5 className="font-medium text-sm mb-2 text-primary">
                      {device}
                      {cfg.hostname && cfg.hostname !== device && (
                        <span className="text-text-muted font-normal ml-2">({cfg.hostname})</span>
                      )}
                      <span className="text-xs text-text-muted ml-2">
                        {cfg.commands?.length || 0} commands
                      </span>
                    </h5>
                    {/* Affected interfaces */}
                    {cfg.affected_interfaces?.length > 0 && (
                      <div className="mb-2">
                        <span className="text-xs text-text-muted">Affected Interfaces</span>
                        <div className="mt-1 space-y-1">
                          {cfg.affected_interfaces.map((iface: any, i: number) => (
                            <div key={i} className="flex items-center gap-2 text-xs bg-background p-1.5 rounded">
                              <span className="font-mono font-medium text-primary">{iface.name}</span>
                              <span className="text-text-muted">{iface.ip_address}/{iface.subnet_mask}</span>
                              {iface.description && (
                                <span className="text-text-muted italic">{iface.description}</span>
                              )}
                              <span className="ml-auto text-warning">
                                area {iface.current_area} → {iface.new_area}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {cfg.commands?.length > 0 && (
                      <pre className="text-xs font-mono bg-background p-2 rounded overflow-x-auto text-primary max-h-32 overflow-y-auto">
                        {cfg.commands?.join('\n')}
                      </pre>
                    )}
                    {cfg.rollback_commands?.length > 0 && (
                      <>
                        <span className="text-xs text-text-muted mt-2 block">Rollback</span>
                        <pre className="text-xs font-mono bg-background p-2 rounded overflow-x-auto text-warning max-h-24 overflow-y-auto">
                          {cfg.rollback_commands?.join('\n')}
                        </pre>
                      </>
                    )}
                    {cfg.warnings?.length > 0 && cfg.warnings.filter((w: string) => !w.startsWith('Generated password')).length > 0 && (
                      <div className="mt-2 text-xs text-warning">
                        {cfg.warnings.filter((w: string) => !w.startsWith('Generated password')).map((w: string, i: number) => (
                          <p key={i}>{w}</p>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <>
                {/* Show affected interfaces for single-device view */}
                {(() => {
                  const singleCfg: any = perDeviceEntries.length === 1 ? perDeviceEntries[0][1] : null;
                  const interfaces = singleCfg?.affected_interfaces || [];
                  if (interfaces.length === 0) return null;
                  return (
                    <div className="mb-3">
                      <h4 className="font-medium text-sm text-text-secondary">Affected Interfaces</h4>
                      <div className="mt-1 space-y-1">
                        {interfaces.map((iface: any, i: number) => (
                          <div key={i} className="flex items-center gap-2 text-xs bg-background p-2 rounded">
                            <span className="font-mono font-medium text-primary">{iface.name}</span>
                            <span className="text-text-muted">{iface.ip_address}/{iface.subnet_mask}</span>
                            {iface.description && (
                              <span className="text-text-muted italic">{iface.description}</span>
                            )}
                            <span className="ml-auto text-warning">
                              area {iface.current_area} → {iface.new_area}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })()}
                <h4 className="font-medium text-sm text-text-secondary">Generated Commands</h4>
                <pre className="text-xs font-mono bg-background p-3 rounded-lg overflow-x-auto text-primary">
                  {data.commands?.join('\n')}
                </pre>
                {data.rollback_commands?.length > 0 && (
                  <>
                    <h4 className="font-medium text-sm text-text-secondary mt-4">Rollback Commands</h4>
                    <pre className="text-xs font-mono bg-background p-3 rounded-lg overflow-x-auto text-warning">
                      {data.rollback_commands?.join('\n')}
                    </pre>
                  </>
                )}
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

      case 'baseline_collection':
        const baselineDevices = data.baselines ? Object.keys(data.baselines) : [];
        const hasMultiBaseline = baselineDevices.length > 1;

        return (
          <div className="space-y-3">
            <div className={cn(
              'p-3 rounded-lg border',
              data.collected ? 'bg-success/10 border-success/20' : 'bg-warning/10 border-warning/20'
            )}>
              <span className="text-sm font-medium">
                {data.collected
                  ? `Baseline Collected from ${hasMultiBaseline ? baselineDevices.length + ' Devices' : '1 Device'}`
                  : 'Baseline Collection Skipped'}
              </span>
            </div>

            {/* Multi-device baselines */}
            {data.collected && hasMultiBaseline && (
              <div className="space-y-3">
                {baselineDevices.map((deviceName: string) => {
                  const deviceBaseline = data.baselines[deviceName];
                  return (
                    <div key={deviceName} className="border border-border rounded-lg p-3">
                      <h5 className="font-medium text-sm mb-2 text-primary">{deviceName}</h5>
                      <div className="grid grid-cols-3 gap-2">
                        <div className="bg-background p-2 rounded">
                          <span className="text-xs text-text-muted">Neighbors</span>
                          <p className="font-medium text-sm">{deviceBaseline.ospf_neighbors?.length || 0}</p>
                        </div>
                        <div className="bg-background p-2 rounded">
                          <span className="text-xs text-text-muted">Interfaces</span>
                          <p className="font-medium text-sm">{deviceBaseline.interfaces?.length || 0}</p>
                        </div>
                        <div className="bg-background p-2 rounded">
                          <span className="text-xs text-text-muted">Routes</span>
                          <p className="font-medium text-sm">{deviceBaseline.routes?.length || 0}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Single-device baseline (backward compat) */}
            {data.collected && !hasMultiBaseline && data.baseline && (
              <>
                <div className="grid grid-cols-3 gap-3">
                  <div className="bg-background p-3 rounded-lg">
                    <span className="text-xs text-text-muted">OSPF Neighbors</span>
                    <p className="font-medium">{data.baseline.ospf_neighbors?.length || 0}</p>
                  </div>
                  <div className="bg-background p-3 rounded-lg">
                    <span className="text-xs text-text-muted">Interfaces</span>
                    <p className="font-medium">{data.baseline.interfaces?.length || 0}</p>
                  </div>
                  <div className="bg-background p-3 rounded-lg">
                    <span className="text-xs text-text-muted">OSPF Routes</span>
                    <p className="font-medium">{data.baseline.routes?.length || 0}</p>
                  </div>
                </div>
                {data.baseline.ospf_neighbors && data.baseline.ospf_neighbors.length > 0 && (
                  <div className="bg-background p-3 rounded-lg">
                    <span className="text-xs text-text-muted">OSPF Neighbors (Pre-Change)</span>
                    <div className="mt-2 space-y-1">
                      {data.baseline.ospf_neighbors.map((neighbor: any, i: number) => (
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
              </>
            )}
            {data.error && (
              <div className="bg-error/10 border border-error/20 p-3 rounded-lg">
                <p className="text-sm text-error">{data.error}</p>
              </div>
            )}
          </div>
        );

      case 'cml_deployment':
        const hasDeviceResults = data.device_results && Object.keys(data.device_results).length > 1;

        return (
          <div className="space-y-3">
            <div className={cn(
              'p-3 rounded-lg border',
              data.all_deployed ? 'bg-success/10 border-success/20'
                : data.deployed ? 'bg-warning/10 border-warning/20'
                : 'bg-error/10 border-error/20'
            )}>
              <span className="text-sm font-medium">
                {data.all_deployed
                  ? `Successfully Deployed to ${data.devices?.length || 1} Device(s)`
                  : data.deployed
                    ? `Partially Deployed (${data.devices?.length || 0} succeeded, ${data.failed_devices?.length || 0} failed)`
                    : 'Deployment Failed'}
              </span>
            </div>

            {/* Per-device results table */}
            {data.deployed && hasDeviceResults && (
              <div className="space-y-2">
                <h4 className="font-medium text-sm text-text-secondary">Per-Device Results</h4>
                {Object.entries(data.device_results).map(([deviceName, result]: [string, any]) => (
                  <div
                    key={deviceName}
                    className={cn(
                      'flex items-center justify-between p-2 rounded-lg border',
                      result.deployed ? 'bg-success/5 border-success/20' : 'bg-error/5 border-error/20'
                    )}
                  >
                    <div className="flex items-center gap-2">
                      {result.deployed ? (
                        <CheckCircle2 className="w-4 h-4 text-success" />
                      ) : (
                        <XCircle className="w-4 h-4 text-error" />
                      )}
                      <span className="font-medium text-sm">{deviceName}</span>
                    </div>
                    <span className={cn(
                      'text-xs px-2 py-0.5 rounded',
                      result.deployed ? 'bg-success/20 text-success' : 'bg-error/20 text-error'
                    )}>
                      {result.deployed ? 'Deployed' : result.error || 'Failed'}
                    </span>
                  </div>
                ))}
                <div className="bg-background p-3 rounded-lg">
                  <span className="text-xs text-text-muted">Commands Applied (per device)</span>
                  <p className="font-medium">{data.commands_applied}</p>
                </div>
              </div>
            )}

            {/* Single device display (backward compat) */}
            {data.deployed && !hasDeviceResults && (
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

            {/* Rollback Section */}
            {canRollback && (
              <div className="mt-4 pt-4 border-t border-border">
                <h4 className="font-medium text-sm flex items-center gap-2 mb-3">
                  <RotateCcw className="w-4 h-4" />
                  Rollback Available
                </h4>

                {/* Show rollback commands */}
                <div className="mb-3">
                  <span className="text-xs text-text-muted">Rollback Commands</span>
                  <pre className="mt-1 text-xs font-mono bg-background p-3 rounded-lg overflow-x-auto text-warning max-h-32 overflow-y-auto">
                    {rollbackCommands.join('\n')}
                  </pre>
                </div>

                {/* Rollback error */}
                {rollbackError && (
                  <div className="mb-3 p-3 bg-error/10 border border-error/20 rounded-lg">
                    <p className="text-sm text-error">{rollbackError}</p>
                  </div>
                )}

                {/* Confirmation dialog */}
                {showRollbackConfirm ? (
                  <div className="p-3 bg-warning/10 border border-warning/20 rounded-lg">
                    <p className="text-sm text-warning mb-3">
                      Are you sure you want to rollback this configuration? This will apply the rollback commands to {data.device}.
                    </p>
                    <div className="flex gap-2">
                      <button
                        onClick={handleRollback}
                        disabled={isRollingBack}
                        className="px-4 py-2 bg-warning text-white rounded hover:bg-warning/90 disabled:opacity-50 flex items-center gap-2"
                      >
                        {isRollingBack ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Rolling back...
                          </>
                        ) : (
                          <>
                            <RotateCcw className="w-4 h-4" />
                            Confirm Rollback
                          </>
                        )}
                      </button>
                      <button
                        onClick={() => setShowRollbackConfirm(false)}
                        disabled={isRollingBack}
                        className="px-4 py-2 bg-background border border-border rounded hover:bg-background-elevated disabled:opacity-50"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => setShowRollbackConfirm(true)}
                    className="px-4 py-2 bg-warning/10 border border-warning/30 text-warning rounded hover:bg-warning/20 flex items-center gap-2"
                  >
                    <RotateCcw className="w-4 h-4" />
                    Execute Rollback
                  </button>
                )}
              </div>
            )}

            {/* Rollback already executed */}
            {rollbackStatus?.status === 'completed' && (
              <div className="mt-4 pt-4 border-t border-border">
                <div className={cn(
                  'p-3 rounded-lg border',
                  rollbackStatus.data?.success ? 'bg-success/10 border-success/20' : 'bg-error/10 border-error/20'
                )}>
                  <div className="flex items-center gap-2 mb-1">
                    {rollbackStatus.data?.success ? (
                      <CheckCircle2 className="w-4 h-4 text-success" />
                    ) : (
                      <XCircle className="w-4 h-4 text-error" />
                    )}
                    <span className="text-sm font-medium">
                      {rollbackStatus.data?.success ? 'Rollback Completed' : 'Rollback Failed'}
                    </span>
                  </div>
                  {rollbackStatus.data?.commands_executed && (
                    <p className="text-xs text-text-muted">
                      {rollbackStatus.data.commands_executed} commands executed
                    </p>
                  )}
                  {rollbackStatus.completed_at && (
                    <p className="text-xs text-text-muted mt-1">
                      {formatDate(rollbackStatus.completed_at)}
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Rollback in progress (from another session) */}
            {rollbackStatus?.status === 'running' && (
              <div className="mt-4 pt-4 border-t border-border">
                <div className="p-3 rounded-lg border bg-primary/10 border-primary/20">
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 text-primary animate-spin" />
                    <span className="text-sm font-medium">Rollback in Progress</span>
                  </div>
                </div>
              </div>
            )}

            {/* Rollback failed */}
            {rollbackStatus?.status === 'failed' && (
              <div className="mt-4 pt-4 border-t border-border">
                <div className="p-3 rounded-lg border bg-error/10 border-error/20">
                  <div className="flex items-center gap-2 mb-1">
                    <XCircle className="w-4 h-4 text-error" />
                    <span className="text-sm font-medium">Rollback Failed</span>
                  </div>
                  {rollbackStatus.data?.error && (
                    <p className="text-xs text-error">{rollbackStatus.data.error}</p>
                  )}
                </div>
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
        const getDiffIcon = (change: number) => {
          if (change > 0) return <TrendingUp className="w-3 h-3 text-success" />;
          if (change < 0) return <TrendingDown className="w-3 h-3 text-error" />;
          return <Minus className="w-3 h-3 text-text-muted" />;
        };

        const getDiffColor = (change: number) => {
          if (change > 0) return 'text-success';
          if (change < 0) return 'text-error';
          return 'text-text-muted';
        };

        return (
          <div className="space-y-4">
            {/* Deployment Health Status - Large Badge */}
            {data.deployment_healthy !== undefined && data.deployment_healthy !== null && (
              <div className={cn(
                'p-4 rounded-lg text-center border-l-8',
                data.deployment_healthy
                  ? 'bg-success/20 border-success text-success'
                  : 'bg-error/20 border-error text-error glow-critical'
              )}>
                <span className="text-2xl font-bold">
                  {data.deployment_healthy ? '✅ NETWORK HEALTHY' : '🔴 NETWORK DEGRADED'}
                </span>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div className="bg-background p-3 rounded-lg">
                <span className="text-xs text-text-muted">Convergence Wait</span>
                <p className="font-medium">{data.wait_seconds}s</p>
              </div>
              <div className="bg-background p-3 rounded-lg">
                <span className="text-xs text-text-muted">Devices Monitored</span>
                <p className="font-medium">
                  {data.devices ? data.devices.length : 1} device(s)
                </p>
                {data.devices && data.devices.length > 1 && (
                  <p className="text-xs text-text-muted mt-1">{data.devices.join(', ')}</p>
                )}
              </div>
            </div>

            {/* Network State Changes - Sort to show problems first */}
            {data.diff && (
              <div className="space-y-2">
                <h4 className="font-medium text-lg">Network State Changes</h4>

                {Object.entries(data.diff)
                  .sort(([, a]: [string, any], [, b]: [string, any]) => (a.change || 0) - (b.change || 0))
                  .map(([metric, values]: [string, any]) => {
                    const change = values.change || 0;
                    const isNegative = change < 0;
                    const isPositive = change > 0;

                    return (
                      <div
                        key={metric}
                        className={cn(
                          'p-3 rounded-lg flex items-center justify-between transition-all',
                          isNegative && 'bg-error/20 border-l-4 border-error',
                          !isNegative && 'bg-background'
                        )}
                      >
                        <span className={cn(
                          'font-medium',
                          isNegative && 'text-error text-lg font-bold'
                        )}>
                          {metric.replace(/_/g, ' ').toUpperCase()}
                        </span>
                        <div className="flex items-center gap-2">
                          <span className={isNegative ? 'font-bold' : ''}>
                            {values.before}
                          </span>
                          <span className="text-text-muted">→</span>
                          <span className={cn(
                            isNegative && 'font-bold text-error text-lg',
                            isPositive && 'text-success'
                          )}>
                            {values.after}
                          </span>
                          <span className={cn(
                            'font-bold text-lg ml-2',
                            isNegative && 'text-error',
                            isPositive && 'text-success',
                            change === 0 && 'text-text-muted'
                          )}>
                            ({change > 0 ? '+' : ''}{change})
                            {isNegative ? ' ↓' : isPositive ? ' ↑' : ' —'}
                          </span>
                        </div>
                      </div>
                    );
                  })}
              </div>
            )}

            {/* Per-Device Health Summary */}
            {data.per_device && Object.keys(data.per_device).length > 1 && (
              <div className="space-y-2">
                <h4 className="font-medium text-lg">Per-Device Health</h4>
                {Object.entries(data.per_device).map(([deviceName, deviceData]: [string, any]) => (
                  <div
                    key={deviceName}
                    className={cn(
                      'p-3 rounded-lg border flex items-center justify-between',
                      deviceData.healthy ? 'bg-success/5 border-success/20' : 'bg-error/5 border-error/20'
                    )}
                  >
                    <div className="flex items-center gap-2">
                      {deviceData.healthy ? (
                        <CheckCircle2 className="w-4 h-4 text-success" />
                      ) : (
                        <XCircle className="w-4 h-4 text-error" />
                      )}
                      <span className="font-medium text-sm">{deviceName}</span>
                    </div>
                    <div className="flex items-center gap-3 text-xs">
                      <span className={cn(
                        deviceData.diff?.ospf_neighbors?.change < 0 ? 'text-error' : 'text-text-muted'
                      )}>
                        Neighbors: {deviceData.diff?.ospf_neighbors?.change >= 0 ? '+' : ''}{deviceData.diff?.ospf_neighbors?.change || 0}
                      </span>
                      <span className={cn(
                        deviceData.diff?.interfaces_up?.change < 0 ? 'text-error' : 'text-text-muted'
                      )}>
                        Intf: {deviceData.diff?.interfaces_up?.change >= 0 ? '+' : ''}{deviceData.diff?.interfaces_up?.change || 0}
                      </span>
                      <span className={cn(
                        deviceData.diff?.routes?.change < 0 ? 'text-error' : 'text-text-muted'
                      )}>
                        Routes: {deviceData.diff?.routes?.change >= 0 ? '+' : ''}{deviceData.diff?.routes?.change || 0}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* OSPF Neighbors */}
            {data.ospf_neighbors && data.ospf_neighbors.length > 0 && (
              <div className="bg-background p-3 rounded-lg">
                <span className="text-xs text-text-muted">OSPF Neighbors (Post-Change: {data.ospf_neighbor_count || data.ospf_neighbors.length})</span>
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
                <span className="text-xs text-text-muted">Interface Status (Post-Change)</span>
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
                      ) : check.status === 'error' ? (
                        <XCircle className="w-3 h-3 text-error" />
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
                  <div key={i} className={cn(
                    'p-3 rounded-lg border',
                    result.success ? 'bg-success/10 border-success/20' : 'bg-error/10 border-error/20'
                  )}>
                    <div className="flex items-center gap-2 text-sm">
                      {result.success ? (
                        <CheckCircle2 className="w-4 h-4 text-success" />
                      ) : (
                        <XCircle className="w-4 h-4 text-error" />
                      )}
                      <span className="capitalize font-medium">{result.channel}</span>
                      {result.ticket_number && (
                        <span className="text-xs bg-primary/20 text-primary px-2 py-0.5 rounded font-mono">
                          {result.ticket_number}
                        </span>
                      )}
                    </div>
                    {result.reason && (
                      <p className="text-xs text-text-secondary mt-1 ml-6">{result.reason}</p>
                    )}
                    {!result.success && result.error && (
                      <p className="text-xs text-error mt-1 ml-6">{result.error}</p>
                    )}
                    {result.ticket_link && (
                      <a href={result.ticket_link} target="_blank" rel="noopener noreferrer" className="text-xs text-primary hover:underline mt-1 ml-6 block">
                        View Ticket
                      </a>
                    )}
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

        {/* Critical Error Banner */}
        {(() => {
          const validation = operation?.stages?.ai_validation?.data;
          const isCritical = validation?.validation_status === 'FAILED' ||
                             validation?.validation_status === 'ROLLBACK_REQUIRED' ||
                             validation?.rollback_recommended;

          if (!isCritical) return null;

          return (
            <div className="p-4 border-b border-border">
              <AlertBanner
                severity="critical"
                title="CRITICAL ISSUES DETECTED"
                message={validation?.rollback_reason || "This deployment has critical errors that require attention"}
                actionLabel="View Rollback"
              />
            </div>
          );
        })()}

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
