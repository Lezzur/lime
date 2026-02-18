import { useState, useRef } from "react";
import { Shield, Swords, BookOpen, X } from "lucide-react";
import { useMeetingStore } from "../stores/meetingStore";
import type { PersonalityMode } from "../lib/types";

const modes: {
  id: PersonalityMode;
  label: string;
  description: string;
  color: string;
  icon: React.ElementType;
}[] = [
  {
    id: "scribe",
    label: "Scribe",
    description: "Pure capture, no interpretation",
    color: "#3b82f6",
    icon: BookOpen,
  },
  {
    id: "thinking-partner",
    label: "Thinking Partner",
    description: "Collaborative idea development",
    color: "#84cc16",
    icon: Shield,
  },
  {
    id: "sparring",
    label: "Sparring Partner",
    description: "Challenge & stress-test ideas",
    color: "#ef4444",
    icon: Swords,
  },
];

const INTENSITY_LABELS: Record<number, string> = {
  1: "Gentle nudge",
  2: "Light pushback",
  3: "Friendly challenge",
  4: "Firm questioning",
  5: "Direct challenge",
  6: "Aggressive probing",
  7: "No punches pulled",
  8: "Ruthless scrutiny",
  9: "Full demolition",
  10: "Maximum adversarial",
};

function IntensitySlider() {
  const { sparringConfig, setSparringIntensity } = useMeetingStore();
  const [hoveredValue, setHoveredValue] = useState<number | null>(null);
  const sliderRef = useRef<HTMLDivElement>(null);

  const displayValue = hoveredValue ?? sparringConfig.intensity;
  const intensityPct = ((sparringConfig.intensity - 1) / 9) * 100;

  // Color interpolation from amber (low) through orange to red (high)
  const r = Math.round(239 + (sparringConfig.intensity - 1) * 0);
  const g = Math.round(158 - (sparringConfig.intensity - 1) * 14);
  const b = Math.round(11 + (sparringConfig.intensity - 1) * 3);
  const intensityColor = `rgb(${r}, ${g}, ${b})`;

  return (
    <div className="mt-2 px-1">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] text-[var(--lime-text-dim)] uppercase tracking-widest">
          Intensity
        </span>
        <span className="text-[10px] font-medium" style={{ color: intensityColor }}>
          {displayValue}/10 — {INTENSITY_LABELS[displayValue]}
        </span>
      </div>

      {/* Custom slider track */}
      <div
        ref={sliderRef}
        className="relative h-6 flex items-center cursor-pointer group"
        onMouseMove={(e) => {
          if (!sliderRef.current) return;
          const rect = sliderRef.current.getBoundingClientRect();
          const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
          setHoveredValue(Math.round(pct * 9) + 1);
        }}
        onMouseLeave={() => setHoveredValue(null)}
        onClick={(e) => {
          if (!sliderRef.current) return;
          const rect = sliderRef.current.getBoundingClientRect();
          const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
          setSparringIntensity(Math.round(pct * 9) + 1);
        }}
      >
        {/* Track background */}
        <div className="absolute inset-x-0 h-1.5 rounded-full bg-[var(--lime-border)]">
          {/* Filled portion */}
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${intensityPct}%`,
              background: `linear-gradient(to right, #f59e0b, ${intensityColor})`,
            }}
          />
        </div>

        {/* Tick marks */}
        <div className="absolute inset-x-0 flex justify-between px-0">
          {Array.from({ length: 10 }, (_, i) => (
            <div
              key={i}
              className="h-1 w-px transition-colors"
              style={{
                backgroundColor:
                  i + 1 <= sparringConfig.intensity
                    ? intensityColor
                    : "var(--lime-border)",
              }}
            />
          ))}
        </div>

        {/* Thumb */}
        <div
          className="absolute h-3 w-3 rounded-full border-2 transition-all shadow-lg"
          style={{
            left: `calc(${intensityPct}% - 6px)`,
            borderColor: intensityColor,
            backgroundColor: "var(--lime-bg)",
            boxShadow: `0 0 6px ${intensityColor}40`,
          }}
        />
      </div>

      {/* Scale labels */}
      <div className="flex justify-between mt-1">
        <span className="text-[9px] text-[var(--lime-text-dim)]">Gentle</span>
        <span className="text-[9px] text-[var(--lime-text-dim)]">Aggressive</span>
      </div>
    </div>
  );
}

export default function PersonalityToggle() {
  const { personalityMode, setPersonalityMode, quickExitSparring } = useMeetingStore();

  return (
    <div className="px-3 py-3 border-t border-[var(--lime-border)]">
      <p className="text-[10px] uppercase tracking-widest text-[var(--lime-text-dim)] mb-2 px-1">
        Agent Mode
      </p>
      <div className="space-y-0.5">
        {modes.map((mode) => {
          const Icon = mode.icon;
          const isActive = personalityMode === mode.id;

          return (
            <button
              key={mode.id}
              onClick={() => setPersonalityMode(mode.id)}
              className={`w-full flex items-center gap-2.5 px-2 py-1.5 rounded-md text-xs transition-colors ${
                isActive
                  ? "bg-white/10 text-white"
                  : "text-[var(--lime-text-muted)] hover:bg-white/5 hover:text-white"
              }`}
            >
              <Icon
                size={13}
                className="shrink-0"
                style={{ color: isActive ? mode.color : undefined }}
              />
              <span className="font-medium flex-1 text-left">{mode.label}</span>
              {isActive && (
                <span
                  className="h-1.5 w-1.5 rounded-full shrink-0"
                  style={{ backgroundColor: mode.color }}
                />
              )}
            </button>
          );
        })}
      </div>

      {/* Sparring intensity control */}
      {personalityMode === "sparring" && (
        <div className="mt-3 pt-3 border-t border-[var(--lime-border)]">
          <IntensitySlider />

          {/* Quick exit button */}
          <button
            onClick={quickExitSparring}
            className="mt-3 w-full flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md text-[10px] font-medium text-amber-400 bg-amber-500/10 border border-amber-500/20 hover:bg-amber-500/20 transition-colors"
          >
            <X size={10} />
            Exit Sparring Mode
          </button>
        </div>
      )}
    </div>
  );
}
