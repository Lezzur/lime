"use client";

import { useCallback, useRef } from "react";
import type { GestureType } from "@/lib/types";

interface GestureCallbacks {
  onSingleTap?: (x: number, y: number) => void;
  onDoubleTap?: (x: number, y: number) => void;
  onLongPress?: (x: number, y: number) => void;
}

const DOUBLE_TAP_DELAY = 300; // ms between taps
const LONG_PRESS_DELAY = 600; // ms to hold

export function useGestures(callbacks: GestureCallbacks) {
  const lastTapTime = useRef(0);
  const lastTapPos = useRef({ x: 0, y: 0 });
  const singleTapTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const longPressTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isLongPress = useRef(false);

  const clearTimers = useCallback(() => {
    if (singleTapTimer.current) clearTimeout(singleTapTimer.current);
    if (longPressTimer.current) clearTimeout(longPressTimer.current);
    singleTapTimer.current = null;
    longPressTimer.current = null;
  }, []);

  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      const touch = e.touches[0];
      const x = touch.clientX;
      const y = touch.clientY;
      isLongPress.current = false;

      longPressTimer.current = setTimeout(() => {
        isLongPress.current = true;
        callbacks.onLongPress?.(x, y);
      }, LONG_PRESS_DELAY);
    },
    [callbacks]
  );

  const handleTouchEnd = useCallback(
    (e: React.TouchEvent) => {
      if (longPressTimer.current) {
        clearTimeout(longPressTimer.current);
        longPressTimer.current = null;
      }

      if (isLongPress.current) return;

      const touch = e.changedTouches[0];
      const x = touch.clientX;
      const y = touch.clientY;
      const now = Date.now();
      const timeSinceLast = now - lastTapTime.current;

      if (timeSinceLast < DOUBLE_TAP_DELAY) {
        // Double tap
        if (singleTapTimer.current) {
          clearTimeout(singleTapTimer.current);
          singleTapTimer.current = null;
        }
        callbacks.onDoubleTap?.(x, y);
        lastTapTime.current = 0;
      } else {
        // Potential single tap — wait to see if another tap follows
        lastTapTime.current = now;
        lastTapPos.current = { x, y };
        singleTapTimer.current = setTimeout(() => {
          callbacks.onSingleTap?.(x, y);
          singleTapTimer.current = null;
        }, DOUBLE_TAP_DELAY);
      }
    },
    [callbacks]
  );

  const handleTouchMove = useCallback(() => {
    // Cancel long press if finger moves
    if (longPressTimer.current) {
      clearTimeout(longPressTimer.current);
      longPressTimer.current = null;
    }
  }, []);

  return { handleTouchStart, handleTouchEnd, handleTouchMove, clearTimers };
}
