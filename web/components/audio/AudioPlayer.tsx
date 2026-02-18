"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Play, Pause, SkipBack } from "lucide-react";
import { cn, formatDuration } from "@/lib/utils";

interface AudioPlayerProps {
  src: string;
  currentSegmentTime?: number; // seconds — seek when this changes
  onTimeUpdate?: (time: number) => void;
  className?: string;
}

export function AudioPlayer({
  src,
  currentSegmentTime,
  onTimeUpdate,
  className,
}: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState(false);

  useEffect(() => {
    const audio = new Audio(src);
    audioRef.current = audio;

    audio.onloadedmetadata = () => setDuration(audio.duration);
    audio.ontimeupdate = () => {
      setCurrentTime(audio.currentTime);
      onTimeUpdate?.(audio.currentTime);
    };
    audio.onended = () => setIsPlaying(false);
    audio.onerror = () => setError(true);

    return () => {
      audio.pause();
      audio.src = "";
    };
  }, [src, onTimeUpdate]);

  // Seek when transcript position changes externally
  useEffect(() => {
    if (currentSegmentTime === undefined || !audioRef.current) return;
    audioRef.current.currentTime = currentSegmentTime;
    audioRef.current.play().catch(() => {});
    setIsPlaying(true);
  }, [currentSegmentTime]);

  const togglePlay = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
    } else {
      audio.play().then(() => setIsPlaying(true)).catch(() => setError(true));
    }
  }, [isPlaying]);

  const seek = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current;
    if (!audio) return;
    const t = parseFloat(e.target.value);
    audio.currentTime = t;
    setCurrentTime(t);
  }, []);

  const restart = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.currentTime = 0;
    setCurrentTime(0);
  }, []);

  if (error) {
    return (
      <div className="text-zinc-500 text-xs px-3 py-2 bg-zinc-900 rounded-lg">
        Audio not available
      </div>
    );
  }

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <div className={cn("flex items-center gap-3 bg-zinc-900 rounded-xl px-4 py-3", className)}>
      <button onClick={restart} className="text-zinc-500 hover:text-zinc-300 transition-colors">
        <SkipBack className="w-4 h-4" />
      </button>

      <button
        onClick={togglePlay}
        className="w-8 h-8 rounded-full bg-lime-500 hover:bg-lime-400 flex items-center justify-center flex-shrink-0 transition-colors"
      >
        {isPlaying ? (
          <Pause className="w-3.5 h-3.5 text-black" />
        ) : (
          <Play className="w-3.5 h-3.5 text-black ml-0.5" />
        )}
      </button>

      {/* Scrubber */}
      <div className="flex-1 flex items-center gap-2">
        <input
          type="range"
          min={0}
          max={duration || 100}
          step={0.1}
          value={currentTime}
          onChange={seek}
          className="w-full h-1 accent-lime-500 cursor-pointer"
          style={{
            background: `linear-gradient(to right, rgb(132 204 22) ${progress}%, rgb(63 63 70) ${progress}%)`,
          }}
        />
      </div>

      <span className="text-zinc-500 text-xs font-mono tabular-nums flex-shrink-0">
        {formatDuration(currentTime)}{duration > 0 ? ` / ${formatDuration(duration)}` : ""}
      </span>
    </div>
  );
}
