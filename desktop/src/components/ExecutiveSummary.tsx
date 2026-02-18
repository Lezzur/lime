import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import { useState } from "react";
import { CheckSquare, AlertCircle, Lightbulb, Link2, Edit2, Check, X } from "lucide-react";
import type { MeetingNotes, ActionItem, Decision } from "../lib/types";
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
          <h3 className="text-xs uppercase tracking-widest text-[var(--lime-text-dim)] mb-2">
            Linked Meetings
          </h3>
          <div className="space-y-1.5">
            {notes.connections.map((conn, i) => (
              <div
                key={i}
                className="flex items-center gap-2 p-2.5 rounded-lg bg-[var(--lime-surface-2)] border border-[var(--lime-border)] text-xs"
              >
                <Link2 size={11} className="text-[var(--lime-text-dim)] shrink-0" />
                <span className="text-[var(--lime-text)] font-medium">
                  {conn.meeting_title ?? conn.meeting_id}
                </span>
                <span className="text-[var(--lime-text-dim)]">—</span>
                <span className="text-[var(--lime-text-muted)]">{conn.relationship}</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
