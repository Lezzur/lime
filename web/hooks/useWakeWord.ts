"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { CaptureMode } from "@/lib/types";

interface WakeWordConfig {
  wakeWord: string; // e.g. "koda"
  onModeSwitch?: (mode: CaptureMode) => void;
  onCommand?: (command: string) => void;
  enabled: boolean;
}

export function useWakeWord({ wakeWord, onModeSwitch, onCommand, enabled }: WakeWordConfig) {
  const [isListening, setIsListening] = useState(false);
  const [lastCommand, setLastCommand] = useState<string | null>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  const parseCommand = useCallback(
    (transcript: string) => {
      const lower = transcript.toLowerCase().trim();
      if (!lower.includes(wakeWord.toLowerCase())) return;

      const afterWakeWord = lower
        .slice(lower.indexOf(wakeWord.toLowerCase()) + wakeWord.length)
        .trim();

      setLastCommand(afterWakeWord);
      onCommand?.(afterWakeWord);

      if (afterWakeWord.includes("discreet") || afterWakeWord.includes("silent")) {
        onModeSwitch?.("discreet");
      } else if (
        afterWakeWord.includes("active") ||
        afterWakeWord.includes("show") ||
        afterWakeWord.includes("display")
      ) {
        onModeSwitch?.("active");
      }
    },
    [wakeWord, onModeSwitch, onCommand]
  );

  const start = useCallback(() => {
    if (typeof window === "undefined") return;
    const SpeechRecognition =
      window.SpeechRecognition || (window as unknown as { webkitSpeechRecognition: typeof window.SpeechRecognition }).webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          parseCommand(event.results[i][0].transcript);
        }
      }
    };

    recognition.onend = () => {
      if (enabled) {
        // Auto-restart for continuous wake word listening
        setTimeout(() => recognition.start(), 300);
      } else {
        setIsListening(false);
      }
    };

    recognition.onerror = (event) => {
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        setIsListening(false);
        return;
      }
      // Restart on other errors
      if (enabled) setTimeout(() => recognition.start(), 1000);
    };

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);
  }, [enabled, parseCommand]);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
    recognitionRef.current = null;
    setIsListening(false);
  }, []);

  useEffect(() => {
    if (enabled) {
      start();
    } else {
      stop();
    }
    return () => stop();
  }, [enabled, start, stop]);

  return { isListening, lastCommand };
}
