/**
 * Error Severity System
 *
 * Classifies and prioritizes errors across pipeline stages to make
 * critical issues DOMINANT and OBVIOUS in the UI.
 */

export enum ErrorSeverity {
  CRITICAL = 'critical',
  HIGH = 'high',
  MEDIUM = 'medium',
  LOW = 'low',
  INFO = 'info'
}

export interface ErrorSummary {
  critical: number;
  high: number;
  medium: number;
  low: number;
  total: number;
}

export interface Operation {
  id: string;
  stages?: {
    ai_validation?: {
      data?: {
        validation_status?: string;
        rollback_recommended?: boolean;
        rollback_reason?: string;
        findings?: Array<{
          status?: string;
          severity?: string;
          category?: string;
          message?: string;
        }>;
      };
    };
    monitoring?: {
      data?: {
        diff?: {
          ospf_neighbors?: { change?: number };
          interfaces_up?: { change?: number };
          routes?: { change?: number };
        };
        deployment_healthy?: boolean;
      };
    };
  };
}

/**
 * Get error summary for an operation by analyzing all stages
 */
export function getOperationErrorSummary(operation: Operation): ErrorSummary {
  const summary: ErrorSummary = {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
    total: 0
  };

  // Check AI validation findings
  const validation = operation.stages?.ai_validation?.data;
  if (validation?.findings) {
    validation.findings.forEach((finding: any) => {
      if (finding.status === 'error' || finding.severity === 'critical') {
        summary.critical++;
      } else if (finding.status === 'warning' || finding.severity === 'warning') {
        summary.high++;
      }
    });
  }

  // Check monitoring diff for network degradation
  const monitoring = operation.stages?.monitoring?.data;
  if (monitoring?.diff) {
    const neighborChange = monitoring.diff.ospf_neighbors?.change || 0;
    const interfaceChange = monitoring.diff.interfaces_up?.change || 0;

    if (neighborChange < 0 || interfaceChange < 0) {
      summary.critical++;
    }
  }

  // Check if rollback recommended
  if (validation?.rollback_recommended) {
    summary.critical++;
  }

  summary.total = summary.critical + summary.high + summary.medium + summary.low;
  return summary;
}

/**
 * Determine severity level from validation status
 */
export function getValidationSeverity(status: string): ErrorSeverity {
  if (status === 'FAILED' || status === 'ROLLBACK_REQUIRED') {
    return ErrorSeverity.CRITICAL;
  }
  if (status === 'WARNING') {
    return ErrorSeverity.HIGH;
  }
  return ErrorSeverity.INFO;
}

/**
 * Get severity color for UI styling
 */
export function getSeverityColor(severity: ErrorSeverity): string {
  switch (severity) {
    case ErrorSeverity.CRITICAL:
      return 'error';
    case ErrorSeverity.HIGH:
      return 'warning';
    case ErrorSeverity.MEDIUM:
      return 'primary';
    case ErrorSeverity.LOW:
    case ErrorSeverity.INFO:
    default:
      return 'text-muted';
  }
}

/**
 * Check if operation has critical issues
 */
export function hasCriticalIssues(operation: Operation): boolean {
  const summary = getOperationErrorSummary(operation);
  return summary.critical > 0;
}

/**
 * Get human-readable severity label
 */
export function getSeverityLabel(severity: ErrorSeverity): string {
  switch (severity) {
    case ErrorSeverity.CRITICAL:
      return 'CRITICAL';
    case ErrorSeverity.HIGH:
      return 'High';
    case ErrorSeverity.MEDIUM:
      return 'Medium';
    case ErrorSeverity.LOW:
      return 'Low';
    case ErrorSeverity.INFO:
      return 'Info';
  }
}
