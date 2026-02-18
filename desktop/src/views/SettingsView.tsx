import { useEffect, useState } from "react";
import { Save, Loader2, RefreshCw, Swords } from "lucide-react";
import type { AppSettings, SparringConfig } from "../lib/types";
import { api } from "../lib/api";
import { useMeetingStore } from "../stores/meetingStore";

const DEFAULT_SETTINGS: AppSettings = {
  llm_provider: "ollama",
  llm_model: "llama3.2",
  transcription_provider: "whisper",
  confidence_threshold: 0.7,
  wake_word_enabled: false,
  wake_word: "hey lime",
  auto_analyze: true,
  audio_source: "microphone",
  personality_mode: "thinking-partner",
  sparring_config: { intensity: 5, focus_areas: ["logic", "assumptions"] },
};

const SPARRING_FOCUS_OPTIONS: { id: SparringConfig["focus_areas"][number]; label: string; description: string }[] = [
  { id: "logic", label: "Logic", description: "Challenge reasoning and arguments" },
  { id: "assumptions", label: "Assumptions", description: "Question underlying assumptions" },
  { id: "feasibility", label: "Feasibility", description: "Test practical viability" },
  { id: "risks", label: "Risks", description: "Expose potential risks and pitfalls" },
  { id: "alternatives", label: "Alternatives", description: "Push for unconsidered options" },
];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-3">
      <h3 className="text-[10px] uppercase tracking-widest text-[var(--lime-text-dim)]">
        {title}
      </h3>
      <div className="bg-[var(--lime-surface-2)] rounded-lg border border-[var(--lime-border)] divide-y divide-[var(--lime-border)]">
        {children}
      </div>
    </div>
  );
}

function Row({ label, description, children }: {
  label: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-4 px-4 py-3">
      <div className="flex-1 min-w-0">
        <p className="text-sm text-[var(--lime-text)]">{label}</p>
        {description && (
          <p className="text-xs text-[var(--lime-text-muted)] mt-0.5">{description}</p>
        )}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
        checked ? "" : "bg-[var(--lime-border)]"
      }`}
      style={checked ? { backgroundColor: "var(--accent)" } : {}}
    >
      <span
        className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
          checked ? "translate-x-4" : "translate-x-1"
        }`}
      />
    </button>
  );
}

function Select({
  value,
  options,
  onChange,
}: {
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="bg-[var(--lime-surface)] border border-[var(--lime-border)] rounded-md px-2 py-1 text-xs text-[var(--lime-text)] outline-none focus:border-[var(--accent)] transition-colors"
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

export default function SettingsView() {
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api
      .getSettings()
      .then(setSettings)
      .catch(() => {/* use defaults */})
      .finally(() => setLoading(false));
  }, []);

  function update<K extends keyof AppSettings>(key: K, value: AppSettings[K]) {
    setSettings((s) => ({ ...s, [key]: value }));
    setSaved(false);
  }

  async function save() {
    setSaving(true);
    try {
      const updated = await api.patchSettings(settings as any);
      setSettings(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      console.error("Settings save failed:", err);
    } finally {
      setSaving(false);
    }
  }

  async function consolidate() {
    try {
      await api.consolidateMemory();
    } catch (err) {
      console.error("Consolidation failed:", err);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 gap-2 text-[var(--lime-text-muted)] text-sm">
        <Loader2 size={16} className="animate-spin" />
        Loading settings…
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 overflow-y-auto">
      {/* Audio */}
      <Section title="Audio">
        <Row label="Default Source" description="What to capture during meetings">
          <Select
            value={settings.audio_source}
            options={[
              { value: "microphone", label: "Microphone" },
              { value: "system", label: "System Audio" },
              { value: "both", label: "Both" },
            ]}
            onChange={(v) => update("audio_source", v as AppSettings["audio_source"])}
          />
        </Row>
      </Section>

      {/* Transcription */}
      <Section title="Transcription">
        <Row label="Provider" description="Engine used for speech-to-text">
          <Select
            value={settings.transcription_provider}
            options={[
              { value: "whisper", label: "Whisper (Local)" },
              { value: "deepgram", label: "Deepgram" },
              { value: "assemblyai", label: "AssemblyAI" },
            ]}
            onChange={(v) =>
              update("transcription_provider", v as AppSettings["transcription_provider"])
            }
          />
        </Row>
      </Section>

      {/* Intelligence */}
      <Section title="Intelligence">
        <Row label="LLM Provider" description="Model for analysis and summaries">
          <Select
            value={settings.llm_provider}
            options={[
              { value: "ollama", label: "Ollama (Local)" },
              { value: "claude", label: "Claude (Anthropic)" },
              { value: "openai", label: "GPT-4o (OpenAI)" },
            ]}
            onChange={(v) => update("llm_provider", v as AppSettings["llm_provider"])}
          />
        </Row>
        <Row label="Model Name" description="Specific model identifier">
          <input
            type="text"
            value={settings.llm_model}
            onChange={(e) => update("llm_model", e.target.value)}
            className="bg-[var(--lime-surface)] border border-[var(--lime-border)] rounded-md px-2 py-1 text-xs text-[var(--lime-text)] outline-none focus:border-[var(--accent)] transition-colors selectable w-36"
          />
        </Row>
        <Row
          label="Confidence Threshold"
          description={`Only show results above ${Math.round(settings.confidence_threshold * 100)}%`}
        >
          <div className="flex items-center gap-2">
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={settings.confidence_threshold}
              onChange={(e) => update("confidence_threshold", parseFloat(e.target.value))}
              className="w-24 accent-[var(--accent)]"
            />
            <span className="text-xs text-[var(--lime-text-muted)] w-8 text-right">
              {Math.round(settings.confidence_threshold * 100)}%
            </span>
          </div>
        </Row>
        <Row label="Auto-Analyze" description="Run AI analysis after each meeting">
          <Toggle
            checked={settings.auto_analyze}
            onChange={(v) => update("auto_analyze", v)}
          />
        </Row>
      </Section>

      {/* Wake Word */}
      <Section title="Wake Word">
        <Row label="Enable Wake Word" description="Start recording hands-free">
          <Toggle
            checked={settings.wake_word_enabled}
            onChange={(v) => update("wake_word_enabled", v)}
          />
        </Row>
        {settings.wake_word_enabled && (
          <Row label="Wake Phrase">
            <input
              type="text"
              value={settings.wake_word}
              onChange={(e) => update("wake_word", e.target.value)}
              className="bg-[var(--lime-surface)] border border-[var(--lime-border)] rounded-md px-2 py-1 text-xs text-[var(--lime-text)] outline-none focus:border-[var(--accent)] transition-colors selectable w-36"
            />
          </Row>
        )}
      </Section>

      {/* Sparring Partner */}
      <Section title="Sparring Partner">
        <Row
          label="Default Intensity"
          description={`Level ${settings.sparring_config.intensity}/10 — controls how aggressively ideas are challenged`}
        >
          <div className="flex items-center gap-2">
            <Swords size={13} className="text-red-400" />
            <input
              type="range"
              min={1}
              max={10}
              step={1}
              value={settings.sparring_config.intensity}
              onChange={(e) =>
                update("sparring_config", {
                  ...settings.sparring_config,
                  intensity: parseInt(e.target.value),
                })
              }
              className="w-24 accent-red-500"
            />
            <span className="text-xs text-red-400 w-6 text-right font-medium">
              {settings.sparring_config.intensity}
            </span>
          </div>
        </Row>
        <div className="px-4 py-3">
          <p className="text-sm text-[var(--lime-text)] mb-2">Focus Areas</p>
          <p className="text-xs text-[var(--lime-text-muted)] mb-3">
            Choose what the sparring partner emphasizes when challenging your ideas.
          </p>
          <div className="flex flex-wrap gap-2">
            {SPARRING_FOCUS_OPTIONS.map((opt) => {
              const isActive = settings.sparring_config.focus_areas.includes(opt.id);
              return (
                <button
                  key={opt.id}
                  onClick={() => {
                    const current = settings.sparring_config.focus_areas;
                    const next = isActive
                      ? current.filter((a) => a !== opt.id)
                      : [...current, opt.id];
                    if (next.length > 0) {
                      update("sparring_config", {
                        ...settings.sparring_config,
                        focus_areas: next as SparringConfig["focus_areas"],
                      });
                    }
                  }}
                  className={`px-2.5 py-1.5 rounded-md text-xs transition-colors border ${
                    isActive
                      ? "border-red-500/30 text-red-400 bg-red-500/10"
                      : "border-[var(--lime-border)] text-[var(--lime-text-muted)] hover:border-[#404040]"
                  }`}
                  title={opt.description}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>
        </div>
      </Section>

      {/* Memory */}
      <Section title="Memory">
        <Row
          label="Force Consolidation"
          description="Manually trigger memory consolidation now"
        >
          <button
            onClick={consolidate}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs border border-[var(--lime-border)] text-[var(--lime-text-muted)] hover:border-[var(--accent)] hover:text-[var(--lime-text)] transition-colors"
          >
            <RefreshCw size={11} />
            Run
          </button>
        </Row>
      </Section>

      {/* Save */}
      <div className="flex justify-end pt-2">
        <button
          onClick={save}
          disabled={saving}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50 transition-colors"
          style={{ backgroundColor: "var(--accent)", color: "var(--accent-text)" }}
        >
          {saving ? (
            <Loader2 size={13} className="animate-spin" />
          ) : saved ? (
            "Saved!"
          ) : (
            <>
              <Save size={13} />
              Save Settings
            </>
          )}
        </button>
      </div>
    </div>
  );
}
