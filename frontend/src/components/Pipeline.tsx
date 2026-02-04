'use client';

import { motion } from 'framer-motion';
import {
  Mic,
  Brain,
  FileCode,
  Upload,
  Timer,
  Search,
  Activity,
  Bell,
  UserCheck,
  CheckCircle2,
  Loader2,
  Circle,
  XCircle,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface Stage {
  key: string;
  name: string;
  description: string;
}

interface StageData {
  status: string;
  data?: any;
  error?: string;
}

interface PipelineProps {
  stages: Stage[];
  currentStage: string;
  stagesData: Record<string, StageData>;
  onAdvance?: () => void;
  isPaused?: boolean;
}

const stageIcons: Record<string, any> = {
  voice_input: Mic,
  intent_parsing: Brain,
  config_generation: FileCode,
  cml_deployment: Upload,
  monitoring: Timer,
  splunk_analysis: Search,
  ai_analysis: Activity,
  notifications: Bell,
  human_decision: UserCheck,
};

export function Pipeline({ stages, currentStage, stagesData, onAdvance, isPaused }: PipelineProps) {
  const currentIndex = stages.findIndex((s) => s.key === currentStage);

  return (
    <div className="bg-background-elevated rounded-xl border border-border p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Pipeline Progress</h2>
        {isPaused && onAdvance && (
          <button
            onClick={onAdvance}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
            Advance to Next Stage
          </button>
        )}
      </div>

      <div className="relative">
        {/* Progress bar background */}
        <div className="absolute top-5 left-0 right-0 h-1 bg-border rounded-full" />

        {/* Progress bar filled */}
        <motion.div
          className="absolute top-5 left-0 h-1 bg-primary rounded-full"
          initial={{ width: 0 }}
          animate={{
            width: `${Math.max(0, ((currentIndex + 1) / stages.length) * 100)}%`,
          }}
          transition={{ duration: 0.5 }}
        />

        {/* Stages */}
        <div className="relative flex justify-between">
          {stages.map((stage, index) => {
            const Icon = stageIcons[stage.key] || Circle;
            const stageData = stagesData[stage.key];
            const status = stageData?.status || 'pending';
            const isActive = stage.key === currentStage;
            const isPast = index < currentIndex;

            return (
              <div
                key={stage.key}
                className="flex flex-col items-center"
                style={{ width: `${100 / stages.length}%` }}
              >
                {/* Stage Circle */}
                <motion.div
                  className={cn(
                    'relative w-10 h-10 rounded-full flex items-center justify-center z-10',
                    status === 'completed' && 'bg-success',
                    status === 'running' && 'bg-primary',
                    status === 'failed' && 'bg-error',
                    status === 'pending' && 'bg-background-elevated border-2 border-border'
                  )}
                  initial={{ scale: 1 }}
                  animate={isActive ? { scale: [1, 1.1, 1] } : { scale: 1 }}
                  transition={{ repeat: isActive ? Infinity : 0, duration: 1.5 }}
                >
                  {status === 'completed' && (
                    <CheckCircle2 className="w-5 h-5 text-white" />
                  )}
                  {status === 'running' && (
                    <Loader2 className="w-5 h-5 text-white animate-spin" />
                  )}
                  {status === 'failed' && (
                    <XCircle className="w-5 h-5 text-white" />
                  )}
                  {status === 'pending' && (
                    <Icon className="w-5 h-5 text-text-muted" />
                  )}

                  {/* Pulse effect for active stage */}
                  {isActive && status === 'running' && (
                    <div className="absolute inset-0 rounded-full bg-primary animate-ping opacity-25" />
                  )}
                </motion.div>

                {/* Stage Label */}
                <span
                  className={cn(
                    'mt-2 text-xs text-center font-medium',
                    isActive ? 'text-primary' : isPast ? 'text-text-primary' : 'text-text-muted'
                  )}
                >
                  {stage.name}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Current Stage Details */}
      {currentStage && (
        <motion.div
          key={currentStage}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-6 p-4 bg-background rounded-lg border border-border"
        >
          <div className="flex items-center gap-3">
            {(() => {
              const Icon = stageIcons[currentStage] || Circle;
              return <Icon className="w-5 h-5 text-primary" />;
            })()}
            <div>
              <h3 className="font-medium">
                {stages.find((s) => s.key === currentStage)?.name}
              </h3>
              <p className="text-sm text-text-secondary">
                {stages.find((s) => s.key === currentStage)?.description}
              </p>
            </div>
          </div>

          {stagesData[currentStage]?.error && (
            <div className="mt-3 p-3 bg-error/10 border border-error/20 rounded-lg">
              <p className="text-sm text-error">{stagesData[currentStage].error}</p>
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}
