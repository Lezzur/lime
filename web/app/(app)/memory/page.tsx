"use client";

import { useEffect, useState } from "react";
import { getMemory, updateMemory, triggerConsolidation } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Brain, Save, RefreshCw, Loader } from "lucide-react";

type Tier = "short-term" | "medium-term" | "long-term";

const tiers: { id: Tier; label: string; description: string; color: string }[] = [
  {
    id: "short-term",
    label: "Short-term",
    description: "Raw signals — corrections, edits, preferences from recent sessions",
    color: "text-blue-400",
  },
  {
    id: "medium-term",
    label: "Medium-term",
    description: "Detected patterns — signals that have appeared multiple times",
    color: "text-yellow-400",
  },
  {
    id: "long-term",
    label: "Long-term",
    description: "Confirmed truths — ground rules that shape all outputs",
    color: "text-green-400",
  },
];

export default function MemoryPage() {
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

  const loadTier = async (tier: Tier) => {
    setLoading(true);
    try {
      const { content } = await getMemory(tier);
      setContents((v) => ({ ...v, [tier]: content }));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTier(activeTier);
  }, [activeTier]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateMemory(activeTier, contents[activeTier]);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  };

  const handleConsolidate = async () => {
    setConsolidating(true);
    try {
      await triggerConsolidation();
      await loadTier(activeTier);
    } finally {
      setConsolidating(false);
    }
  };

  const activeTierMeta = tiers.find((t) => t.id === activeTier)!;

  return (
    <div className="min-h-screen flex flex-col">
      <div className="border-b border-zinc-900 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Brain className="w-5 h-5 text-lime-400" />
          <h1 className="text-white font-semibold">Memory</h1>
        </div>
        <button
          onClick={handleConsolidate}
          disabled={consolidating}
          className="flex items-center gap-2 text-xs text-zinc-500 hover:text-zinc-300 transition-colors px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-800"
        >
          <RefreshCw className={cn("w-3.5 h-3.5", consolidating && "animate-spin")} />
          {consolidating ? "Consolidating…" : "Run consolidation"}
        </button>
      </div>

      {/* Tier tabs */}
      <div className="flex border-b border-zinc-900 px-6">
        {tiers.map((tier) => (
          <button
            key={tier.id}
            onClick={() => setActiveTier(tier.id)}
            className={cn(
              "px-4 py-3 text-sm border-b-2 transition-colors",
              activeTier === tier.id
                ? `border-current ${tier.color}`
                : "border-transparent text-zinc-500 hover:text-zinc-300"
            )}
          >
            {tier.label}
          </button>
        ))}
      </div>

      <div className="flex-1 flex flex-col px-6 py-4 gap-3">
        <p className="text-zinc-500 text-xs">{activeTierMeta.description}</p>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader className="w-5 h-5 text-zinc-600 animate-spin" />
          </div>
        ) : (
          <div className="flex-1 flex flex-col gap-3">
            <textarea
              value={contents[activeTier]}
              onChange={(e) =>
                setContents((v) => ({ ...v, [activeTier]: e.target.value }))
              }
              className="flex-1 min-h-[400px] bg-zinc-900 border border-zinc-800 rounded-xl p-4 text-zinc-300 text-sm font-mono leading-relaxed focus:border-zinc-600 outline-none resize-none"
              placeholder="No entries yet in this memory tier."
              spellCheck={false}
            />
            <div className="flex items-center justify-between">
              <p className="text-zinc-600 text-xs">
                Edits are treated as high-priority learning signals
              </p>
              <button
                onClick={handleSave}
                disabled={saving}
                className={cn(
                  "flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors",
                  saved
                    ? "bg-green-900/50 text-green-400 border border-green-800"
                    : "bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-zinc-700"
                )}
              >
                <Save className="w-3.5 h-3.5" />
                {saving ? "Saving…" : saved ? "Saved" : "Save changes"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
