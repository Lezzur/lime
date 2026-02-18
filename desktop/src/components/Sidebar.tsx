import {
  LayoutDashboard,
  Mic,
  Search,
  Brain,
  Settings,
} from "lucide-react";
import { useMeetingStore } from "../stores/meetingStore";
import type { ActiveView } from "../stores/meetingStore";
import PersonalityToggle from "./PersonalityToggle";

const navItems: { id: ActiveView; label: string; Icon: React.ElementType }[] = [
  { id: "meetings", label: "Meetings", Icon: LayoutDashboard },
  { id: "memos", label: "Voice Memos", Icon: Mic },
  { id: "search", label: "Search", Icon: Search },
  { id: "memory", label: "Memory", Icon: Brain },
  { id: "settings", label: "Settings", Icon: Settings },
];

export default function Sidebar() {
  const { activeView, setActiveView } = useMeetingStore();

  return (
    <aside className="w-52 shrink-0 border-r border-[var(--lime-border)] bg-[var(--lime-surface)] flex flex-col">
      {/* Logo */}
      <div className="px-4 py-4">
        <div
          className="h-8 w-8 rounded-lg flex items-center justify-center text-black font-bold text-sm"
          style={{ backgroundColor: "var(--accent)" }}
        >
          L
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 space-y-0.5">
        {navItems.map(({ id, label, Icon }) => (
          <button
            key={id}
            onClick={() => setActiveView(id)}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors ${
              activeView === id
                ? "bg-white/10 text-white"
                : "text-[var(--lime-text-muted)] hover:bg-white/5 hover:text-white"
            }`}
          >
            <Icon
              size={15}
              style={activeView === id ? { color: "var(--accent)" } : {}}
            />
            {label}
          </button>
        ))}
      </nav>

      {/* Personality toggle */}
      <PersonalityToggle />
    </aside>
  );
}
