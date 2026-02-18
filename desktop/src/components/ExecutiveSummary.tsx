import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import { useState } from "react";
import { CheckSquare, AlertCircle, Lightbulb, Link2, Edit2, Check, X, AlertTriangle, Network } from "lucide-react";
import type { MeetingNotes, ActionItem, Decision, Connection } from "../lib/types";
import { api } from "../lib/api";
import { useMeetingStore } from "../stores/meetingStore";

interface Props {
  meetingId: string;
  notes: MeetingNotes;
}

function ConfidenceDot({ value }: { value: number }) {
  const color =
    value >= 0.8 ? "bg-emerald-500" : value >= 0.5 ? "bg-amber-500" : "bg-red-500";
  return (
    <span
      className={`inline-block h-1.5 w-1.5 rounded-full ${color} ml-1.5`}
      title={`Confidence: ${Math.round(value * 100)}%`}
    />
  );
}

function SummaryEditor({ meetingId, initial }: { meetingId: string; initial: string }) {
  const { setMeetingNotes, selectedMeetingNotes } = useMeetingStore();
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({ placeholder: "No summary generated yet…" }),
    ],
    content: initial,
    editable: editing,
    editorProps: {
      attributes: { class: "tiptap-editor selectable text-sm text-[var(--lime-text)] leading-relaxed" },
    },
  });

  async function save() {
    if (!editor) return;
    setSaving(true);
    try {
      const updated = await api.patchMeetingNotes(meetingId, {
        executive_summary: editor.getText(),
      } as any);
      setMeetingNotes({ ...selectedMeetingNotes!, ...updated });
      setEditing(false);
      editor.setEditable(false);
    } catch (err) {
      console.error("Save failed:", err);
    } finally {
      setSaving(false);
    }
  }

  function cancel() {
    editor?.setEditable(false);
    editor?.commands.setContent(initial);
    setEditing(false);
  }

  function startEdit() {
    editor?.setEditable(true);
    setEditing(true);
  }

  return (
    <div className="group relative">
      <EditorContent editor={editor} />
      <div className="flex items-center gap-2 mt-2">
        {!editing ? (
          <button
            onClick={startEdit}
            className="opacity-0 group-hover:opacity-100 flex items-center gap-1 text-[10px] text-[var(--lime-text-dim)] hover:text-[var(--lime-text-muted)] transition-all"
          >
            <Edit2 size={10} /> Edit
          </button>
        ) : (
          <>
            <button
              onClick={save}
              disabled={saving}
              className="flex items-center gap-1 text-[10px] text-emerald-400 hover:text-emerald-300 transition-colors"
            >
              <Check size={10} /> {saving ? "Saving…" : "Save"}
            </button>
            <button
              onClick={cancel}
              className="flex items-center gap-1 text-[10px] text-[var(--lime-text-dim)] hover:text-[var(--lime-text-muted)] transition-colors"
            >
              <X size={10} /> Cancel
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function ActionItemRow({ item }: { item: ActionItem }) {
  const priorityColor =
    item.priority === "high"
      ? "text-red-400 border-red-500/30 bg-red-500/10"
      : item.priority === "medium"
      ? "text-amber-400 border-amber-500/30 bg-amber-500/10"
      : "text-[var(--lime-text-muted)] border-[var(--lime-border)] bg-transparent";

  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-[var(--lime-border)] last:border-0">
      <CheckSquare size={14} className="text-[var(--lime-text-dim)] mt-0.5 shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-[var(--lime-text)] selectable">{item.description}</p>
        <div className="flex flex-wrap items-center gap-2 mt-1">
          {item.owner && (
            <span className="text-xs text-[var(--lime-text-muted)]">→ {item.owner}</span>
          )}
          {item.deadline && (
            <span className="text-xs text-[var(--lime-text-dim)]">by {item.deadline}</span>
          )}
          <span
            className={`text-[10px] px-1.5 py-0.5 rounded border font-medium ${priorityColor}`}
          >
            {item.priority}
          </span>
          <ConfidenceDot value={item.confidence} />
        </div>
        {item.source_quote && (
          <p className="text-xs text-[var(--lime-text-dim)] italic mt-1 truncate">
            "{item.source_quote}"
          </p>
        )}
      </div>
    </div>
  );
}

function DecisionRow({ item }: { item: Decision }) {
  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-[var(--lime-border)] last:border-0">
      <AlertCircle size={14} className="text-[var(--lime-text-dim)] mt-0.5 shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-[var(--lime-text)] selectable">{item.description}</p>
        {item.context && (
          <p className="text-xs text-[var(--lime-text-muted)] mt-0.5 selectable">{item.context}</p>
        )}
        <div className="flex items-center gap-2 mt-1">
          {item.participants?.map((p) => (
            <span key={p} className="text-[10px] text-[var(--lime-text-dim)] bg-white/5 px-1.5 py-0.5 rounded">
              {p}
            </span>
          ))}
          <ConfidenceDot value={item.confidence} />
        </div>
      </div>
    </div>
  );
}

function ConnectionRow({ conn }: { conn: Connection }) {
  const typeLabel = conn.connection_type?.replace(/_/g, " ");
  const typeColors: Record<string, string> = {
    shared_topic: "text-lime-400 bg-lime-500/10 border-lime-500/20",
    shared_person: "text-blue-400 bg-blue-500/10 border-blue-500/20",
    follow_up: "text-purple-400 bg-purple-500/10 border-purple-500/20",
    decision_referenced: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    action_dependency: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20",
    recurring_theme: "text-pink-400 bg-pink-500/10 border-pink-500/20",
  };
  const badgeColor = conn.connection_type
    ? typeColors[conn.connection_type] ?? "text-[var(--lime-text-muted)] bg-white/5 border-[var(--lime-border)]"
    : "";

  return (
    <div className="flex items-start gap-2.5 p-2.5 rounded-lg bg-[var(--lime-surface-2)] border border-[var(--lime-border)] text-xs">
      <Link2 size={12} className="text-[var(--lime-text-dim)] mt-0.5 shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[var(--lime-text)] font-medium">
            {conn.meeting_title ?? conn.meeting_id}
          </span>
          {conn.connection_type && (
            <span className={`text-[10px] px-1 py-0.5 rounded border ${badgeColor}`}>
              {typeLabel}
            </span>
          )}
          {conn.strength != null && (
            <span className="text-[10px] text-[var(--lime-text-dim)]">
              {Math.round(conn.strength * 100)}% match
            </span>
          )}
        </div>
        <p className="text-[var(--lime-text-muted)] mt-0.5">{conn.relationship}</p>
        {conn.shared_entities && conn.shared_entities.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1">
            {conn.shared_entities.map((e, j) => (
              <span
                key={j}
                className="text-[10px] px-1 py-0.5 rounded bg-white/5 text-[var(--lime-text-dim)]"
              >
                {e.name}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ExecutiveSummary({ meetingId, notes }: Props) {
  return (
    <div className="space-y-6 p-6 selectable">
      {/* Summary */}
      <section>
        <h3 className="text-xs uppercase tracking-widest text-[var(--lime-text-dim)] mb-3">
          Summary
        </h3>
        {notes.executive_summary ? (
          <SummaryEditor meetingId={meetingId} initial={notes.executive_summary} />
        ) : (
          <p className="text-sm text-[var(--lime-text-dim)] italic">Processing…</p>
        )}
      </section>

      {/* Sentiment badge */}
      {notes.sentiment && (
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs border border-[var(--lime-border)] text-[var(--lime-text-muted)]">
          {notes.sentiment}
        </div>
      )}

      {/* Action Items */}
      {notes.action_items?.length > 0 && (
        <section>
          <h3 className="text-xs uppercase tracking-widest text-[var(--lime-text-dim)] mb-2">
            Action Items ({notes.action_items.length})
          </h3>
          <div className="bg-[var(--lime-surface-2)] rounded-lg border border-[var(--lime-border)] px-3">
            {notes.action_items.map((item) => (
              <ActionItemRow key={item.id} item={item} />
            ))}
          </div>
        </section>
      )}

      {/* Decisions */}
      {notes.decisions?.length > 0 && (
        <section>
          <h3 className="text-xs uppercase tracking-widest text-[var(--lime-text-dim)] mb-2">
            Decisions ({notes.decisions.length})
          </h3>
          <div className="bg-[var(--lime-surface-2)] rounded-lg border border-[var(--lime-border)] px-3">
            {notes.decisions.map((item) => (
              <DecisionRow key={item.id} item={item} />
            ))}
          </div>
        </section>
      )}

      {/* Insights */}
      {notes.insights?.length > 0 && (
        <section>
          <h3 className="text-xs uppercase tracking-widest text-[var(--lime-text-dim)] mb-2">
            Insights
          </h3>
          <div className="space-y-2">
            {notes.insights.map((insight) => (
              <div
                key={insight.id}
                className="flex items-start gap-2.5 p-3 rounded-lg bg-[var(--accent-muted)] border border-[var(--accent)]/20"
              >
                <Lightbulb size={13} className="mt-0.5 shrink-0" style={{ color: "var(--accent)" }} />
                <p className="text-xs text-[var(--lime-text)] leading-relaxed">{insight.content}</p>
                <ConfidenceDot value={insight.confidence} />
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Connections */}
      {notes.connections?.length > 0 && (
        <section>
          <h3 className="flex items-center gap-2 text-xs uppercase tracking-widest text-[var(--lime-text-dim)] mb-2">
            <Network size={11} />
            Linked Meetings ({notes.connections.length})
          </h3>
          <div className="space-y-1.5">
            {/* Contradictions first */}
            {notes.connections
              .filter((c) => c.is_contradiction)
              .map((conn, i) => (
                <div
                  key={`contra-${i}`}
                  className="flex items-start gap-2.5 p-2.5 rounded-lg bg-red-500/5 border border-red-500/20 text-xs"
                >
                  <AlertTriangle size={12} className="text-red-400 mt-0.5 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-red-300 font-medium">
                        {conn.meeting_title ?? conn.meeting_id}
                      </span>
                      <span className="text-[10px] px-1 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20">
                        contradiction
                      </span>
                    </div>
                    <p className="text-[var(--lime-text-muted)] mt-0.5">
                      {conn.contradiction_detail ?? conn.relationship}
                    </p>
                  </div>
                </div>
              ))}
            {/* Normal connections */}
            {notes.connections
              .filter((c) => !c.is_contradiction)
              .map((conn, i) => (
                <ConnectionRow key={`conn-${i}`} conn={conn} />
              ))}
          </div>
        </section>
      )}
    </div>
  );
}
