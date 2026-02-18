import { useEffect, useState, useCallback } from "react";
import { Brain, RefreshCw, Save, Loader } from "lucide-react";
import { api } from "../lib/api";

type Tier = "short-term" | "medium-term" | "long-term";

const TIERS: { id: Tier; label: string; description: string; color: string }[] = [
  {
    id: "long-term",
    label: "Long-term",
    description: "Confirmed truths — ground rules that shape all outputs",
    color: "text-green-400",
  },
  {
    id: "medium-term",
    label: "Medium-term",
    description: "Detected patterns — signals that have appeared multiple times",
    color: "text-yellow-400",
  },
  {
    id: "short-term",
    label: "Short-term",
    description: "Raw signals — corrections, edits, preferences from recent sessions",
    color: "text-blue-400",
  },
];

export default function MemoryView() {
  const [activeTier, setActiveTier] = useState<Tier>("long-term");
  const [contents, setContents] = useState<Record<Tier, string>>({
    "short-term": "",
    "medium-term": "",
    "long-term": "",
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [consolidating, setConsolidating] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTier = useCallback(async (tier: Tier) => {
    setLoading(true);
    setError(null);
    try {
      const { content } = await api.getMemory(tier);
      setContents((v) => ({ ...v, [tier]: content }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load memory");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTier(activeTier);
  }, [activeTier, loadTier]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await api.updateMemory(activeTier, contents[activeTier]);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const handleConsolidate = async () => {
    setConsolidating(true);
    setError(null);
    try {
      await api.consolidateMemory();
      await loadTier(activeTier);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Consolidation failed");
    } finally {
      setConsolidating(false);
    }
  };

  const activeMeta = TIERS.find((t) => t.id === activeTier)!;

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-[var(--lime-border)] shrink-0">
        <div className="flex items-center gap-2">
          <Brain size={15} style={{ color: "var(--accent)" }} />
          <span className="text-sm font-medium text-white">Memory</span>
        </div>
        <button
          onClick={handleConsolidate}
          disabled={consolidating}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs text-[var(--lime-text-muted)] hover:text-white bg-white/5 hover:bg-white/10 border border-[var(--lime-border)] transition-colors disabled:opacity-50"
        >
          <RefreshCw size={12} className={consolidating ? "animate-spin" : ""} />
          {consolidating ? "Consolidating…" : "Run consolidation"}
        </button>
      </div>

      {/* Tier tabs */}
      <div className="flex border-b border-[var(--lime-border)] px-5 shrink-0">
        {TIERS.map((tier) => (
          <button
            key={tier.id}
            onClick={() => setActiveTier(tier.id)}
            className={`px-3 py-2.5 text-xs border-b-2 transition-colors ${
              activeTier === tier.id
                ? `border-current ${tier.color}`
                : "border-transparent text-[var(--lime-text-muted)] hover:text-white"
            }`}
          >
            {tier.label}
          </button>
        ))}
      </div>

      {/* Description */}
      <div className="px-5 pt-3 pb-1 shrink-0">
        <p className="text-xs text-[var(--lime-text-muted)]">{activeMeta.description}</p>
      </div>

      {/* Editor */}
      <div className="flex-1 flex flex-col overflow-hidden px-5 pb-4 gap-3 min-h-0">
        {loading ? (
          <div className="flex items-center justify-center flex-1">
            <Loader size={18} className="text-[var(--lime-text-muted)] animate-spin" />
          </div>
        ) : (
          <>
            <textarea
              value={contents[activeTier]}
              onChange={(e) =>
                setContents((v) => ({ ...v, [activeTier]: e.target.value }))
              }
              className="flex-1 min-h-0 bg-[var(--lime-surface)] border border-[var(--lime-border)] rounded-lg p-3.5 text-[var(--lime-text)] text-xs font-mono leading-relaxed focus:border-white/20 outline-none resize-none"
              placeholder="No entries yet in this memory tier."
              spellCheck={false}
            />
            <div className="flex items-center justify-between shrink-0">
              {error ? (
                <p className="text-xs text-red-400">{error}</p>
              ) : (
                <p className="text-xs text-[var(--lime-text-dim)]">
                  Edits are treated as high-priority learning signals
                </p>
              )}
              <button
                onClick={handleSave}
                disabled={saving}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs transition-colors disabled:opacity-50 ${
                  saved
                    ? "bg-green-500/20 text-green-400 border border-green-500/30"
                    : "bg-white/5 hover:bg-white/10 text-[var(--lime-text-muted)] hover:text-white border border-[var(--lime-border)]"
                }`}
              >
                <Save size={12} />
                {saving ? "Saving…" : saved ? "Saved" : "Save changes"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
