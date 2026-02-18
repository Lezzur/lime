import { useMeetingStore } from "../stores/meetingStore";
import type { PersonalityMode } from "../lib/types";

const modes: { id: PersonalityMode; label: string; description: string; color: string }[] = [
  {
    id: "neutral",
    label: "Neutral",
    description: "Balanced, factual reporting",
    color: "#84cc16",
  },
  {
    id: "strategist",
    label: "Strategist",
    description: "Business impact & decisions",
    color: "#8b5cf6",
  },
  {
    id: "analyst",
    label: "Analyst",
    description: "Data-driven deep detail",
    color: "#3b82f6",
  },
  {
    id: "coach",
    label: "Coach",
    description: "People & next actions",
    color: "#f59e0b",
  },
];

export default function PersonalityToggle() {
  const { personalityMode, setPersonalityMode } = useMeetingStore();

  return (
    <div className="px-3 py-3 border-t border-[var(--lime-border)]">
      <p className="text-[10px] uppercase tracking-widest text-[var(--lime-text-dim)] mb-2 px-1">
        Agent Mode
      </p>
      <div className="space-y-0.5">
        {modes.map((mode) => (
          <button
            key={mode.id}
            onClick={() => setPersonalityMode(mode.id)}
            className={`w-full flex items-center gap-2.5 px-2 py-1.5 rounded-md text-xs transition-colors ${
              personalityMode === mode.id
                ? "bg-white/10 text-white"
                : "text-[var(--lime-text-muted)] hover:bg-white/5 hover:text-white"
            }`}
          >
            <span
              className="h-2 w-2 rounded-full shrink-0"
              style={{ backgroundColor: mode.color }}
            />
            <span className="font-medium">{mode.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
