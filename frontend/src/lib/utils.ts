import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date) {
  return new Date(date).toLocaleString();
}

export function formatDuration(seconds: number) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function truncate(str: string, length: number) {
  if (str.length <= length) return str;
  return str.slice(0, length) + '...';
}

// Pipeline stages in correct execution order
// Human decision happens BEFORE deployment, not after!
// Baseline collection captures network state before changes
export const PIPELINE_STAGES = [
  { key: 'voice_input', name: 'Voice Input', description: 'Capture and transcribe voice command' },
  { key: 'intent_parsing', name: 'Intent Parsing', description: 'Parse intent with LLM' },
  { key: 'config_generation', name: 'Config Generation', description: 'Generate network configuration' },
  { key: 'ai_advice', name: 'AI Advice', description: 'Review changes and assess risks' },
  { key: 'human_decision', name: 'Human Decision', description: 'Approve before deployment' },
  { key: 'baseline_collection', name: 'Baseline', description: 'Collect network state before changes' },
  { key: 'cml_deployment', name: 'CML Deployment', description: 'Push configuration to CML' },
  { key: 'monitoring', name: 'Monitoring', description: 'Compare before/after network state' },
  { key: 'splunk_analysis', name: 'Splunk Analysis', description: 'Query Splunk for logs' },
  { key: 'ai_validation', name: 'AI Validation', description: 'Validate deployment results' },
  { key: 'notifications', name: 'Notifications', description: 'Send alerts via WebEx/ServiceNow' },
];

export function getStageIndex(stageKey: string) {
  return PIPELINE_STAGES.findIndex((s) => s.key === stageKey);
}

export function getStageColor(status: string) {
  switch (status) {
    case 'completed':
      return 'text-success';
    case 'running':
      return 'text-primary';
    case 'failed':
      return 'text-error';
    case 'pending':
    default:
      return 'text-text-muted';
  }
}

export function getSeverityColor(severity: string) {
  switch (severity?.toUpperCase()) {
    case 'CRITICAL':
      return 'text-error bg-error/10';
    case 'WARNING':
      return 'text-warning bg-warning/10';
    case 'INFO':
    default:
      return 'text-success bg-success/10';
  }
}

export function calculateStageDuration(stageData: {
  started_at?: string;
  completed_at?: string;
}): number | null {
  if (!stageData?.started_at || !stageData?.completed_at) {
    return null;
  }
  const start = new Date(stageData.started_at).getTime();
  const end = new Date(stageData.completed_at).getTime();
  return (end - start) / 1000; // Return seconds
}

export function formatStageDuration(seconds: number | null): string {
  if (seconds === null) return '';
  if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}m ${secs}s`;
}

export function getDurationColor(seconds: number | null, fastThreshold = 2, mediumThreshold = 10): string {
  if (seconds === null) return 'text-text-muted';
  if (seconds < fastThreshold) return 'text-success';
  if (seconds < mediumThreshold) return 'text-warning';
  return 'text-error';
}
