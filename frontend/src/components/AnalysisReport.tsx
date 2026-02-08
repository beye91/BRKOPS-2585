'use client';

import { motion } from 'framer-motion';
import {
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  Info,
  FileText,
  Lightbulb,
  ArrowRight,
} from 'lucide-react';
import { cn, getSeverityColor } from '@/lib/utils';

interface Finding {
  type?: string;
  description?: string;
  category?: string;
  message?: string;
  status?: string;
  severity?: string;
  affected_devices?: string[];
  evidence?: string;
}

interface Analysis {
  severity: string;
  findings: Finding[];
  root_cause?: string;
  recommendation: string;
  requires_action: boolean;
  suggested_remediation?: string;
}

interface Config {
  commands: string[];
  rollback_commands?: string[];
  explanation?: string;
  warnings?: string[];
}

interface AnalysisReportProps {
  analysis?: Analysis;
  config?: Config;
  operationStatus?: string;
  operationStage?: string;
}

export function AnalysisReport({ analysis, config, operationStatus, operationStage }: AnalysisReportProps) {
  // Derive effective severity from both severity and validation_status fields
  const effectiveSeverity = (() => {
    if (!analysis) return 'INFO';
    const s = analysis.severity?.toUpperCase();
    if (s === 'CRITICAL' || s === 'WARNING') return s;
    // Fall back to validation_status mapping
    const vs = (analysis as any).validation_status?.toUpperCase();
    if (vs === 'FAILED' || vs === 'ROLLBACK_REQUIRED') return 'CRITICAL';
    if (vs === 'WARNING') return 'WARNING';
    // Check rollback_recommended
    if ((analysis as any).rollback_recommended) return 'CRITICAL';
    return s || 'INFO';
  })();

  if (!analysis && !config) {
    return (
      <div className="bg-background-elevated rounded-xl border border-border p-8 text-center">
        <FileText className="w-12 h-12 text-text-muted mx-auto mb-4" />
        {!operationStatus ? (
          <>
            <p className="text-text-secondary">Start an operation to see AI analysis</p>
            <p className="text-sm text-text-muted mt-1">
              The AI will analyze Splunk data and generate recommendations
            </p>
          </>
        ) : operationStatus === 'running' && operationStage && !['ai_validation', 'ai_advice', 'notification', 'human_decision', 'apply_config'].includes(operationStage) ? (
          <>
            <p className="text-text-secondary">AI analysis will run after Splunk data collection</p>
            <p className="text-sm text-text-muted mt-1">
              Currently at: {operationStage.replace(/_/g, ' ')}
            </p>
          </>
        ) : (
          <>
            <p className="text-text-secondary">No analysis data available for this operation</p>
            <p className="text-sm text-text-muted mt-1">
              The AI validation stage did not produce results
            </p>
          </>
        )}
      </div>
    );
  }

  const getSeverityIcon = (severity: string) => {
    switch (severity?.toUpperCase()) {
      case 'CRITICAL':
        return <AlertCircle className="w-6 h-6 text-error" />;
      case 'WARNING':
        return <AlertTriangle className="w-6 h-6 text-warning" />;
      default:
        return <CheckCircle2 className="w-6 h-6 text-success" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Severity Banner */}
      {analysis && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className={cn(
            'p-4 rounded-xl border flex items-center gap-4',
            effectiveSeverity === 'CRITICAL' && 'bg-error/10 border-error',
            effectiveSeverity === 'WARNING' && 'bg-warning/10 border-warning',
            effectiveSeverity !== 'CRITICAL' && effectiveSeverity !== 'WARNING' && 'bg-success/10 border-success'
          )}
        >
          {getSeverityIcon(effectiveSeverity)}
          <div>
            <h3 className="font-semibold">
              {effectiveSeverity === 'CRITICAL'
                ? 'Critical Issues Detected'
                : effectiveSeverity === 'WARNING'
                ? 'Warnings Found'
                : 'Analysis Complete - No Issues'}
            </h3>
            <p className="text-sm text-text-secondary">
              {(analysis.requires_action || effectiveSeverity === 'CRITICAL')
                ? 'Immediate action may be required'
                : 'No immediate action needed'}
            </p>
          </div>
        </motion.div>
      )}

      {/* Findings */}
      {analysis?.findings && analysis.findings.length > 0 && (
        <div className="bg-background-elevated rounded-xl border border-border p-6">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-warning" />
            Findings ({analysis.findings.length})
          </h3>
          <div className="space-y-4">
            {analysis.findings.map((finding, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className="p-4 bg-background rounded-lg border border-border"
              >
                <div className="flex items-start gap-3">
                  <div
                    className={cn(
                      'w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold',
                      getSeverityColor(finding.severity?.toUpperCase() || effectiveSeverity)
                    )}
                  >
                    {index + 1}
                  </div>
                  <div className="flex-1">
                    <h4 className="font-medium mb-1">{finding.type || finding.category}</h4>
                    <p className="text-sm text-text-secondary">{finding.description || finding.message}</p>
                    {finding.affected_devices && finding.affected_devices.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-2">
                        {finding.affected_devices.map((device) => (
                          <span
                            key={device}
                            className="px-2 py-1 bg-primary/20 text-primary text-xs rounded"
                          >
                            {device}
                          </span>
                        ))}
                      </div>
                    )}
                    {finding.evidence && (
                      <pre className="mt-2 p-2 bg-background-elevated rounded text-xs font-mono overflow-x-auto">
                        {finding.evidence}
                      </pre>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Root Cause */}
      {analysis?.root_cause && (
        <div className="bg-background-elevated rounded-xl border border-border p-6">
          <h3 className="font-semibold mb-3 flex items-center gap-2">
            <Lightbulb className="w-5 h-5 text-warning" />
            Root Cause Analysis
          </h3>
          <p className="text-text-secondary">{analysis.root_cause}</p>
        </div>
      )}

      {/* Recommendation */}
      {analysis?.recommendation && (
        <div className="bg-background-elevated rounded-xl border border-border p-6">
          <h3 className="font-semibold mb-3 flex items-center gap-2">
            <ArrowRight className="w-5 h-5 text-primary" />
            Recommendation
          </h3>
          <p className="text-text-secondary">{analysis.recommendation}</p>
          {analysis.suggested_remediation && (
            <div className="mt-4 p-4 bg-primary/10 border border-primary/20 rounded-lg">
              <h4 className="text-sm font-medium text-primary mb-2">Suggested Remediation</h4>
              <p className="text-sm text-text-secondary">{analysis.suggested_remediation}</p>
            </div>
          )}
        </div>
      )}

      {/* Generated Config */}
      {config && (
        <div className="bg-background-elevated rounded-xl border border-border p-6">
          <h3 className="font-semibold mb-3 flex items-center gap-2">
            <FileText className="w-5 h-5 text-success" />
            Generated Configuration
          </h3>
          {config.explanation && (
            <p className="text-sm text-text-secondary mb-4">{config.explanation}</p>
          )}
          <pre className="p-4 bg-background rounded-lg font-mono text-sm text-primary overflow-x-auto">
            {config.commands?.join('\n')}
          </pre>
          {config.warnings && config.warnings.length > 0 && (
            <div className="mt-4 p-3 bg-warning/10 border border-warning/20 rounded-lg">
              <h4 className="text-sm font-medium text-warning mb-2">Warnings</h4>
              <ul className="text-sm text-text-secondary list-disc list-inside">
                {config.warnings.map((warning, i) => (
                  <li key={i}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
          {config.rollback_commands && config.rollback_commands.length > 0 && (
            <div className="mt-4">
              <h4 className="text-sm font-medium text-text-secondary mb-2">Rollback Commands</h4>
              <pre className="p-3 bg-background rounded-lg font-mono text-xs text-error overflow-x-auto">
                {config.rollback_commands.join('\n')}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
