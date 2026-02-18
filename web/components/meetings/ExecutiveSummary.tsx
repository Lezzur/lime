"use client";

import { useState } from "react";
import type { MeetingNotes } from "@/lib/types";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import { editMeetingNotes } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  CheckSquare,
  Gavel,
  Lightbulb,
  Link2,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Save,
} from "lucide-react";

interface Props {
  notes: MeetingNotes;
  onSeekTranscript?: (time: number) => void;
}

export function ExecutiveSummary({ notes, onSeekTranscript }: Props) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState(false);
  const [editSummary, setEditSummary] = useState(notes.executive_summary);

  const toggle = (key: string) =>
    setExpanded((v) => ({ ...v, [key]: !v[key] }));

  const handleSaveSummary = async () => {
    setSaving(true);
    try {
      await editMeetingNotes(notes.meeting_id, { executive_summary: editSummary });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Executive Summary text */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-white font-medium">Summary</h2>
          <ConfidenceBadge confidence={notes.overall_confidence} showAlways />
        </div>
        <textarea
          value={editSummary}
          onChange={(e) => setEditSummary(e.target.value)}
          className="w-full bg-zinc-900 text-zinc-300 text-sm leading-relaxed rounded-xl p-4 border border-zinc-800 focus:border-zinc-600 outline-none resize-none min-h-32"
          rows={6}
        />
        {editSummary !== notes.executive_summary && (
          <button
            onClick={handleSaveSummary}
            disabled={saving}
            className="mt-2 flex items-center gap-2 text-xs text-lime-400 hover:text-lime-300 transition-colors"
          >
            <Save className="w-3.5 h-3.5" />
            {saving ? "Saving…" : "Save changes"}
          </button>
        )}
      </section>

      {/* Action Items */}
      {notes.action_items.length > 0 && (
        <section>
          <button
            onClick={() => toggle("actions")}
            className="flex items-center justify-between w-full mb-3"
          >
            <h3 className="text-zinc-300 font-medium flex items-center gap-2">
              <CheckSquare className="w-4 h-4 text-lime-500" />
              Action Items
              <span className="text-xs text-zinc-600 font-normal">
                ({notes.action_items.length})
              </span>
            </h3>
            {expanded.actions ? (
              <ChevronUp className="w-4 h-4 text-zinc-600" />
            ) : (
              <ChevronDown className="w-4 h-4 text-zinc-600" />
            )}
          </button>
          {expanded.actions !== false && (
            <div className="space-y-2">
              {notes.action_items.map((item) => (
                <div
                  key={item.id}
                  className={cn(
                    "flex items-start gap-3 p-3 rounded-lg border",
                    item.below_threshold
                      ? "bg-zinc-900/50 border-zinc-800"
                      : "bg-zinc-900 border-zinc-800"
                  )}
                >
                  <div className="w-4 h-4 rounded border border-zinc-700 flex-shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <p className="text-zinc-200 text-sm">{item.description}</p>
                    <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                      {item.owner && (
                        <span className="text-xs text-zinc-500">{item.owner}</span>
                      )}
                      {item.deadline && (
                        <span className="text-xs text-zinc-500 bg-zinc-800 px-1.5 py-0.5 rounded">
                          {item.deadline}
                        </span>
                      )}
                      <ConfidenceBadge confidence={item.confidence} />
                    </div>
                  </div>
                  {item.source_start_time !== null && (
                    <button
                      onClick={() => onSeekTranscript?.(item.source_start_time!)}
                      className="text-zinc-600 hover:text-zinc-400 text-xs flex-shrink-0"
                      title="Jump to transcript"
                    >
                      <Link2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* Decisions */}
      {notes.decisions.length > 0 && (
        <section>
          <button
            onClick={() => toggle("decisions")}
            className="flex items-center justify-between w-full mb-3"
          >
            <h3 className="text-zinc-300 font-medium flex items-center gap-2">
              <Gavel className="w-4 h-4 text-blue-400" />
              Decisions
              <span className="text-xs text-zinc-600 font-normal">({notes.decisions.length})</span>
            </h3>
            {expanded.decisions ? (
              <ChevronUp className="w-4 h-4 text-zinc-600" />
            ) : (
              <ChevronDown className="w-4 h-4 text-zinc-600" />
            )}
          </button>
          {expanded.decisions !== false && (
            <div className="space-y-2">
              {notes.decisions.map((d) => (
                <div
                  key={d.id}
                  className="p-3 rounded-lg bg-zinc-900 border border-zinc-800"
                >
                  <p className="text-zinc-200 text-sm">{d.description}</p>
                  {d.context && (
                    <p className="text-zinc-500 text-xs mt-1">{d.context}</p>
                  )}
                  <div className="flex items-center gap-2 mt-2">
                    <ConfidenceBadge confidence={d.confidence} />
                    {d.source_start_time !== null && (
                      <button
                        onClick={() => onSeekTranscript?.(d.source_start_time!)}
                        className="text-zinc-600 hover:text-zinc-400"
                      >
                        <Link2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* Insights */}
      {notes.insights.length > 0 && (
        <section>
          <button
            onClick={() => toggle("insights")}
            className="flex items-center justify-between w-full mb-3"
          >
            <h3 className="text-zinc-300 font-medium flex items-center gap-2">
              <Lightbulb className="w-4 h-4 text-yellow-400" />
              Insights
              <span className="text-xs text-zinc-600 font-normal">({notes.insights.length})</span>
            </h3>
            {expanded.insights ? (
              <ChevronUp className="w-4 h-4 text-zinc-600" />
            ) : (
              <ChevronDown className="w-4 h-4 text-zinc-600" />
            )}
          </button>
          {expanded.insights !== false && (
            <div className="space-y-2">
              {notes.insights.map((ins, i) => (
                <div
                  key={i}
                  className={cn(
                    "p-3 rounded-lg border",
                    ins.priority === "high"
                      ? "bg-yellow-950/30 border-yellow-900/50"
                      : "bg-zinc-900 border-zinc-800"
                  )}
                >
                  <p className="text-zinc-200 text-sm font-medium">{ins.title}</p>
                  <p className="text-zinc-400 text-xs mt-1">{ins.description}</p>
                  <ConfidenceBadge confidence={ins.confidence} className="mt-2" />
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* Contradictions */}
      {notes.connections?.contradictions && notes.connections.contradictions.length > 0 && (
        <section>
          <h3 className="text-zinc-300 font-medium flex items-center gap-2 mb-3">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            Contradictions flagged
          </h3>
          <div className="space-y-2">
            {notes.connections.contradictions.map((c, i) => (
              <div key={i} className="p-3 rounded-lg bg-red-950/20 border border-red-900/40">
                <p className="text-zinc-200 text-sm">{c.description}</p>
                {c.context && <p className="text-zinc-500 text-xs mt-1">{c.context}</p>}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
