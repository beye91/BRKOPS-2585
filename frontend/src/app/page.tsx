'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Mic,
  Activity,
  Network,
  FileText,
  Bell,
  Settings,
  Play,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ChevronRight,
  Github,
  Loader2,
} from 'lucide-react';
import Link from 'next/link';
import { useWebSocketStore } from '@/store/websocket';
import { operationsApi } from '@/services/api';

export default function HomePage() {
  const { connected } = useWebSocketStore();
  const [recentOperations, setRecentOperations] = useState<any[]>([]);
  const [opsLoading, setOpsLoading] = useState(true);

  useEffect(() => {
    operationsApi.list({ limit: 5 })
      .then((res) => setRecentOperations(res.data || []))
      .catch((err) => console.error('Failed to fetch recent operations:', err))
      .finally(() => setOpsLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-background relative">
      {/* Background Image */}
      <div
        className="fixed inset-0 z-0 bg-cover bg-center bg-no-repeat"
        style={{ backgroundImage: 'url(/bg.jpg)' }}
      />
      <div className="fixed inset-0 z-0 bg-[#0A0E14]/80" />

      {/* Header */}
      <header className="border-b border-border bg-background-elevated/50 backdrop-blur-sm sticky top-0 z-50 relative">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src="/cisco_live_logo.png" alt="Cisco Live" className="h-8" />
            <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
              <Network className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-text-primary">BRKOPS-2585</h1>
              <p className="text-sm text-text-secondary">AI-Driven Network Operations</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm ${
              connected ? 'bg-success/20 text-success' : 'bg-error/20 text-error'
            }`}>
              <div className={`w-2 h-2 rounded-full ${connected ? 'bg-success animate-pulse' : 'bg-error'}`} />
              {connected ? 'Connected' : 'Disconnected'}
            </div>

            <Link
              href="/admin"
              className="p-2 rounded-lg hover:bg-background-elevated transition-colors"
            >
              <Settings className="w-5 h-5 text-text-secondary" />
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 relative z-10">
        {/* Hero Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h2 className="text-4xl font-bold mb-4">
            <span className="text-text-primary">From </span>
            <span className="text-error">Chaos</span>
            <span className="text-text-primary"> to </span>
            <span className="text-success">Control</span>
          </h2>
          <p className="text-text-secondary text-lg max-w-2xl mx-auto">
            Voice-driven network configuration with automated testing,
            AI-powered analysis, and human-in-the-loop approval.
          </p>
        </motion.div>

        {/* Quick Actions */}
        <div className="flex flex-wrap gap-6 justify-center items-stretch mb-12">
          <Link href="/demo">
            <motion.div
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="p-6 rounded-xl bg-background-elevated border border-border hover:border-primary transition-all cursor-pointer group h-full"
            >
              <div className="w-12 h-12 rounded-lg bg-primary/20 flex items-center justify-center mb-4 group-hover:bg-primary/30 transition-colors">
                <Play className="w-6 h-6 text-primary" />
              </div>
              <h3 className="text-lg font-semibold mb-2">Start Demo</h3>
              <p className="text-text-secondary text-sm">
                Launch the voice-driven network operations demo
              </p>
              <div className="flex items-center gap-1 mt-4 text-primary text-sm">
                Launch Demo <ChevronRight className="w-4 h-4" />
              </div>
            </motion.div>
          </Link>

          {/* QR Code */}
          <motion.div
            whileHover={{ scale: 1.02 }}
            className="p-6 rounded-xl bg-background-elevated border border-border transition-all flex flex-col items-center justify-center"
          >
            <img
              src="/qr-code.png"
              alt="QR Code"
              className="w-32 h-32 rounded-lg mb-3"
            />
            <p className="text-text-secondary text-sm text-center">Scan to follow along</p>
          </motion.div>

          {/* GitHub */}
          <a
            href="https://github.com/beye91/BRKOPS-2585"
            target="_blank"
            rel="noopener noreferrer"
          >
            <motion.div
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="p-6 rounded-xl bg-background-elevated border border-border hover:border-primary transition-all cursor-pointer group h-full flex flex-col items-center justify-center"
            >
              <div className="w-12 h-12 rounded-lg bg-primary/20 flex items-center justify-center mb-4 group-hover:bg-primary/30 transition-colors">
                <Github className="w-6 h-6 text-primary" />
              </div>
              <h3 className="text-lg font-semibold mb-2">View Source</h3>
              <p className="text-text-secondary text-sm text-center">
                Browse the project on GitHub
              </p>
              <div className="flex items-center gap-1 mt-4 text-primary text-sm">
                GitHub <ChevronRight className="w-4 h-4" />
              </div>
            </motion.div>
          </a>
        </div>

        {/* Pipeline Overview */}
        <div className="mb-12">
          <h3 className="text-xl font-semibold mb-6">Pipeline Stages</h3>
          <div className="grid grid-cols-9 gap-2">
            {[
              { name: 'Voice Input', icon: Mic },
              { name: 'Intent Parse', icon: FileText },
              { name: 'Config Gen', icon: FileText },
              { name: 'CML Deploy', icon: Network },
              { name: 'Monitor', icon: Activity },
              { name: 'Splunk Query', icon: FileText },
              { name: 'AI Analysis', icon: Activity },
              { name: 'Notify', icon: Bell },
              { name: 'Approve', icon: CheckCircle2 },
            ].map((stage, index) => (
              <div key={stage.name} className="flex flex-col items-center">
                <div className="w-10 h-10 rounded-full bg-background-elevated border border-border flex items-center justify-center mb-2">
                  <stage.icon className="w-5 h-5 text-text-secondary" />
                </div>
                <span className="text-xs text-text-secondary text-center">{stage.name}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Operations */}
        <div>
          <h3 className="text-xl font-semibold mb-6">Recent Operations</h3>
          {opsLoading ? (
            <div className="text-center py-12 bg-background-elevated rounded-xl border border-border">
              <Loader2 className="w-8 h-8 text-primary mx-auto mb-4 animate-spin" />
              <p className="text-text-secondary">Loading operations...</p>
            </div>
          ) : recentOperations.length === 0 ? (
            <div className="text-center py-12 bg-background-elevated rounded-xl border border-border">
              <Activity className="w-12 h-12 text-text-muted mx-auto mb-4" />
              <p className="text-text-secondary">No recent operations</p>
              <p className="text-text-muted text-sm mt-1">Start a demo to see operations here</p>
            </div>
          ) : (
            <div className="space-y-3">
              {recentOperations.map((op: any) => (
                <div
                  key={op.id}
                  className="p-4 bg-background-elevated rounded-lg border border-border flex items-center justify-between"
                >
                  <div className="flex items-center gap-4">
                    {op.status === 'completed' && <CheckCircle2 className="w-5 h-5 text-success" />}
                    {op.status === 'running' && <Activity className="w-5 h-5 text-primary animate-pulse" />}
                    {op.status === 'failed' && <XCircle className="w-5 h-5 text-error" />}
                    {(op.status === 'pending' || op.status === 'paused') && <AlertTriangle className="w-5 h-5 text-warning" />}
                    <div>
                      <p className="font-medium">{op.use_case_name || op.use_case}</p>
                      <p className="text-sm text-text-secondary truncate max-w-md">{op.input_text}</p>
                    </div>
                  </div>
                  <div className="text-sm text-text-muted">
                    {op.current_stage?.replace(/_/g, ' ')}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border mt-12 py-6 relative z-10 bg-background-elevated/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 text-center text-text-muted text-sm">
          BRKOPS-2585 | Cisco Live Demo Platform | Powered by CML & Splunk MCP Servers
        </div>
      </footer>
    </div>
  );
}
