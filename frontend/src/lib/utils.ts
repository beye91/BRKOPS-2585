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

export const PIPELINE_STAGES = [
  { key: 'voice_input', name: 'Voice Input', description: 'Capture and transcribe voice command' },
  { key: 'intent_parsing', name: 'Intent Parsing', description: 'Parse intent with LLM' },
  { key: 'config_generation', name: 'Config Generation', description: 'Generate network configuration' },
  { key: 'cml_deployment', name: 'CML Deployment', description: 'Push configuration to CML' },
  { key: 'monitoring', name: 'Monitoring', description: 'Wait for network convergence' },
  { key: 'splunk_analysis', name: 'Splunk Analysis', description: 'Query Splunk for logs' },
  { key: 'ai_analysis', name: 'AI Analysis', description: 'Analyze results with AI' },
  { key: 'notifications', name: 'Notifications', description: 'Send alerts via WebEx/ServiceNow' },
  { key: 'human_decision', name: 'Human Decision', description: 'Await human approval' },
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
