"use client";

import { useCallback, useRef, useState } from "react";
import { useGestures } from "@/hooks/useGestures";

interface TapLight {
  id: number;
  x: number;
  y: number;
}

interface DiscreetModeProps {
  onBookmark: () => void;
  onPriorityFlag: () => void;
  onVoiceCapture: (active: boolean) => void;
  error?: boolean;
  offline?: boolean;
}

export function DiscreetMode({
  onBookmark,
  onPriorityFlag,
  onVoiceCapture,
  error = false,
  offline = false,
}: DiscreetModeProps) {
  const [lights, setLights] = useState<TapLight[]>([]);
  const [isVoiceCapturing, setIsVoiceCapturing] = useState(false);
  const lightIdRef = useRef(0);

  const spawnLight = useCallback((x: number, y: number) => {
    const id = ++lightIdRef.current;
    setLights((prev) => [...prev, { id, x, y }]);
    setTimeout(() => {
      setLights((prev) => prev.filter((l) => l.id !== id));
    }, 350); // slightly longer than the 0.3s animation
  }, []);

  const { handleTouchStart, handleTouchEnd, handleTouchMove } = useGestures({
    onSingleTap: (x, y) => {
      spawnLight(x, y);
      onBookmark();
    },
    onDoubleTap: (x, y) => {
      // Two quick lights for double tap
      spawnLight(x, y);
      setTimeout(() => spawnLight(x + 5, y + 5), 80);
      onPriorityFlag();
    },
    onLongPress: (x, y) => {
      spawnLight(x, y);
      setIsVoiceCapturing(true);
      onVoiceCapture(true);
    },
  });

  const handleTouchEndExtended = useCallback(
    (e: React.TouchEvent) => {
      handleTouchEnd(e);
      if (isVoiceCapturing) {
        setIsVoiceCapturing(false);
        onVoiceCapture(false);
      }
    },
    [handleTouchEnd, isVoiceCapturing, onVoiceCapture]
  );

  return (
    <div
      className="fixed inset-0 bg-black touch-none select-none overflow-hidden"
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEndExtended}
      onTouchMove={handleTouchMove}
      // Prevent double-tap zoom
      style={{ touchAction: "none" }}
    >
      {/* Tap light feedback — faint glow at tap position */}
      {lights.map((light) => (
        <div
          key={light.id}
          className="absolute pointer-events-none animate-tap-fade"
          style={{
            left: light.x - 30,
            top: light.y - 30,
            width: 60,
            height: 60,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(255,255,255,0.25) 0%, transparent 70%)",
          }}
        />
      ))}

      {/* Error indicator — subtle red flash, stays invisible otherwise */}
      {error && (
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-8 left-1/2 -translate-x-1/2 w-2 h-2 rounded-full bg-red-500 opacity-60 animate-pulse" />
        </div>
      )}

      {/* Offline indicator — subtle amber flash */}
      {offline && (
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-8 left-1/2 -translate-x-1/2 w-2 h-2 rounded-full bg-amber-500 opacity-60 animate-pulse" />
        </div>
      )}

      {/* Voice capture indicator — invisible but present */}
      {isVoiceCapturing && (
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-12 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full bg-white opacity-30 animate-pulse" />
        </div>
      )}
    </div>
  );
}
