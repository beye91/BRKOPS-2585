'use client';

import { useRef, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Mic, MicOff, Send, Loader2, Volume2, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { voiceApi } from '@/services/api';

interface VoiceInputProps {
  transcript: string;
  setTranscript: (value: string) => void;
  isRecording: boolean;
  setIsRecording: (value: boolean) => void;
  onStart: () => void;
  isLoading: boolean;
}

export function VoiceInput({
  transcript,
  setTranscript,
  isRecording,
  setIsRecording,
  onStart,
  isLoading,
}: VoiceInputProps) {
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationRef = useRef<number>();
  const [micAvailable, setMicAvailable] = useState<boolean | null>(null);

  useEffect(() => {
    // Check if microphone is available (requires HTTPS or localhost)
    const checkMicAvailability = () => {
      const isSecure = typeof window !== 'undefined' &&
        (window.location.protocol === 'https:' ||
         window.location.hostname === 'localhost' ||
         window.location.hostname === '127.0.0.1');
      const hasMediaDevices = typeof navigator !== 'undefined' &&
        navigator.mediaDevices &&
        typeof navigator.mediaDevices.getUserMedia === 'function';
      setMicAvailable(isSecure && hasMediaDevices);
    };
    checkMicAvailability();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, []);

  const startRecording = async () => {
    if (!micAvailable) {
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Set up audio analysis for visual feedback
      const audioContext = new AudioContext();
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;

      // Update audio level for visualization
      const updateLevel = () => {
        if (!analyserRef.current) return;
        const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
        analyserRef.current.getByteFrequencyData(dataArray);
        const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
        setAudioLevel(average / 255);
        animationRef.current = requestAnimationFrame(updateLevel);
      };
      updateLevel();

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        if (animationRef.current) {
          cancelAnimationFrame(animationRef.current);
        }
        setAudioLevel(0);

        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        const file = new File([blob], 'recording.webm', { type: 'audio/webm' });

        setIsTranscribing(true);
        try {
          const response = await voiceApi.transcribe(file);
          setTranscript(response.data.text);
        } catch (error) {
          console.error('Transcription failed:', error);
        } finally {
          setIsTranscribing(false);
        }

        // Stop all tracks
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error('Failed to start recording:', error);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const exampleCommands = [
    "I want to change OSPF configuration on Router-1 to use area 10",
    "Rotate credentials on all datacenter switches",
    "Apply the security patch for CVE-2024-1234 on edge routers",
  ];

  return (
    <div className="bg-background-elevated rounded-xl border border-border p-6">
      <h2 className="text-lg font-semibold mb-6">Voice Command Input</h2>

      {/* Microphone unavailable warning */}
      {micAvailable === false && (
        <div className="mb-6 p-4 bg-warning/10 border border-warning/30 rounded-lg flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-warning flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-warning font-medium">Voice recording unavailable</p>
            <p className="text-sm text-text-secondary mt-1">
              Microphone requires HTTPS. Please type your command below or click an example.
            </p>
          </div>
        </div>
      )}

      {/* Recording Button */}
      <div className="flex justify-center mb-8">
        <motion.button
          onClick={isRecording ? stopRecording : startRecording}
          disabled={isTranscribing || isLoading || micAvailable === false}
          className={cn(
            'relative w-32 h-32 rounded-full flex items-center justify-center transition-all',
            isRecording
              ? 'bg-error shadow-glow-error'
              : micAvailable === false
              ? 'bg-gray-600 cursor-not-allowed'
              : 'bg-primary shadow-glow-primary hover:bg-primary-hover',
            (isTranscribing || isLoading) && 'opacity-50 cursor-not-allowed'
          )}
          whileHover={micAvailable !== false ? { scale: 1.05 } : {}}
          whileTap={micAvailable !== false ? { scale: 0.95 } : {}}
        >
          {isRecording ? (
            <MicOff className="w-12 h-12 text-white" />
          ) : (
            <Mic className={cn("w-12 h-12", micAvailable === false ? "text-gray-400" : "text-white")} />
          )}

          {/* Audio level ring */}
          {isRecording && (
            <motion.div
              className="absolute inset-0 rounded-full border-4 border-error"
              animate={{
                scale: 1 + audioLevel * 0.3,
                opacity: 1 - audioLevel * 0.5,
              }}
            />
          )}

          {/* Transcribing indicator */}
          {isTranscribing && (
            <div className="absolute inset-0 rounded-full flex items-center justify-center bg-primary/80">
              <Loader2 className="w-12 h-12 text-white animate-spin" />
            </div>
          )}
        </motion.button>
      </div>

      {/* Instructions */}
      <p className="text-center text-text-secondary mb-6">
        {micAvailable === false
          ? 'Type your command below or select an example'
          : isRecording
          ? 'Recording... Click to stop'
          : isTranscribing
          ? 'Transcribing audio...'
          : 'Click to start recording your voice command'}
      </p>

      {/* Transcript Input */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-text-secondary mb-2">
          Voice Command Transcript
        </label>
        <textarea
          value={transcript}
          onChange={(e) => setTranscript(e.target.value)}
          placeholder="Your voice command will appear here, or type directly..."
          className="w-full h-32 px-4 py-3 bg-background border border-border rounded-lg resize-none focus:outline-none focus:border-primary"
        />
      </div>

      {/* Start Button */}
      <button
        onClick={onStart}
        disabled={!transcript.trim() || isLoading}
        className={cn(
          'w-full py-3 rounded-lg font-medium flex items-center justify-center gap-2 transition-colors',
          transcript.trim() && !isLoading
            ? 'bg-primary text-white hover:bg-primary-hover'
            : 'bg-border text-text-muted cursor-not-allowed'
        )}
      >
        {isLoading ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            Starting Operation...
          </>
        ) : (
          <>
            <Send className="w-5 h-5" />
            Start Operation
          </>
        )}
      </button>

      {/* Example Commands */}
      <div className="mt-6">
        <p className="text-sm text-text-muted mb-3">Or try an example:</p>
        <div className="space-y-2">
          {exampleCommands.map((cmd, index) => (
            <button
              key={index}
              onClick={() => setTranscript(cmd)}
              className="w-full text-left px-4 py-2 bg-background rounded-lg text-sm text-text-secondary hover:text-text-primary hover:bg-background-hover transition-colors"
            >
              "{cmd}"
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
