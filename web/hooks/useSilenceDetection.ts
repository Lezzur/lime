"use client";

import { useCallback, useRef } from "react";

interface SilenceDetectionOptions {
  silenceThreshold?: number; // RMS threshold (0-1) below which is "silent"
  silenceDuration?: number; // ms of silence before triggering (default 15000)
  onSilence?: () => void;
}

export function useSilenceDetection({
  silenceThreshold = 0.01,
  silenceDuration = 15000,
  onSilence,
}: SilenceDetectionOptions) {
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const rafRef = useRef<number | null>(null);
  const isSilentRef = useRef(false);

  const getRMS = useCallback((analyser: AnalyserNode): number => {
    const buffer = new Uint8Array(analyser.fftSize);
    analyser.getByteTimeDomainData(buffer);
    let sum = 0;
    for (const sample of buffer) {
      const normalized = sample / 128 - 1;
      sum += normalized * normalized;
    }
    return Math.sqrt(sum / buffer.length);
  }, []);

  const start = useCallback(
    (stream: MediaStream) => {
      const audioCtx = new AudioContext();
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 2048;

      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);

      audioContextRef.current = audioCtx;
      analyserRef.current = analyser;

      const check = () => {
        const rms = getRMS(analyser);
        const nowSilent = rms < silenceThreshold;

        if (nowSilent && !isSilentRef.current) {
          isSilentRef.current = true;
          silenceTimerRef.current = setTimeout(() => {
            onSilence?.();
          }, silenceDuration);
        } else if (!nowSilent && isSilentRef.current) {
          isSilentRef.current = false;
          if (silenceTimerRef.current) {
            clearTimeout(silenceTimerRef.current);
            silenceTimerRef.current = null;
          }
        }

        rafRef.current = requestAnimationFrame(check);
      };

      rafRef.current = requestAnimationFrame(check);
    },
    [getRMS, onSilence, silenceDuration, silenceThreshold]
  );

  const stop = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    audioContextRef.current?.close();
    audioContextRef.current = null;
    analyserRef.current = null;
    isSilentRef.current = false;
  }, []);

  return { start, stop };
}
