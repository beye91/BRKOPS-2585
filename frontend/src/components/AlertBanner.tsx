/**
 * Alert Banner Component
 *
 * Displays dominant, obvious alerts at the top of views.
 * Used for critical errors, warnings, and important notifications.
 */

import { motion } from 'framer-motion';
import { XCircle, AlertTriangle, Info } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AlertBannerProps {
  severity: 'critical' | 'warning' | 'info';
  title: string;
  message: string | React.ReactNode;
  onAction?: () => void;
  actionLabel?: string;
  onDismiss?: () => void;
}

export function AlertBanner({
  severity,
  title,
  message,
  onAction,
  actionLabel,
  onDismiss
}: AlertBannerProps) {
  const Icon = severity === 'critical' ? XCircle : severity === 'warning' ? AlertTriangle : Info;

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'w-full p-4 rounded-lg border-l-8 flex items-center justify-between',
        severity === 'critical' && 'bg-error/20 border-error glow-critical',
        severity === 'warning' && 'bg-warning/20 border-warning',
        severity === 'info' && 'bg-primary/10 border-primary'
      )}
    >
      <div className="flex items-center gap-3">
        <Icon className={cn(
          'w-6 h-6',
          severity === 'critical' && 'text-error',
          severity === 'warning' && 'text-warning',
          severity === 'info' && 'text-primary'
        )} />
        <div>
          <h3 className="font-bold text-lg">{title}</h3>
          <p className="text-sm">{message}</p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        {onAction && (
          <button
            onClick={onAction}
            className="px-4 py-2 bg-white text-background rounded hover:bg-gray-100 transition-colors"
          >
            {actionLabel || 'View Details'}
          </button>
        )}
        {onDismiss && (
          <button onClick={onDismiss} className="p-2 hover:opacity-70 transition-opacity">
            <XCircle className="w-5 h-5" />
          </button>
        )}
      </div>
    </motion.div>
  );
}
