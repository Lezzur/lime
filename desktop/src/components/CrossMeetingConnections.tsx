import { useEffect, useState } from "react";
import {
  Link2,
  AlertTriangle,
  Users,
  FolderKanban,
  MessageSquare,
  ArrowRight,
  ChevronDown,
  ChevronRight,
  Loader2,
  Network,
  Zap,
} from "lucide-react";
import type { CrossMeetingData, CrossMeetingCluster, ConnectionType, SharedEntity } from "../lib/types";
import { api } from "../lib/api";
import { useMeetingStore } from "../stores/meetingStore";

const CONNECTION_TYPE_META: Record<
  ConnectionType,
  { label: string; color: string; icon: React.ElementType }
> = {
  shared_topic: { label: "Shared Topic", color: "#84cc16", icon: MessageSquare },
  shared_person: { label: "Shared Person", color: "#3b82f6", icon: Users },
  follow_up: { label: "Follow-up", color: "#8b5cf6", icon: ArrowRight },
  contradiction: { label: "Contradiction", color: "#ef4444", icon: AlertTriangle },
  decision_referenced: { label: "Decision Referenced", color: "#f59e0b", icon: Zap },
  action_dependency: { label: "Action Dependency", color: "#06b6d4", icon: FolderKanban },
  recurring_theme: { label: "Recurring Theme", color: "#ec4899", icon: Network },
};

function EntityBadge({ entity }: { entity: SharedEntity }) {
  const typeColors: Record<string, string> = {
    person: "text-blue-400 bg-blue-500/10 border-blue-500/20",
    project: "text-purple-400 bg-purple-500/10 border-purple-500/20",
    topic: "text-lime-400 bg-lime-500/10 border-lime-500/20",
    decision: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    action_item: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20",
  };

  return (
    <span
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] rounded border ${typeColors[entity.type] ?? "text-[var(--lime-text-muted)] bg-white/5 border-[var(--lime-border)]"}`}
      title={entity.context}
    >
      {entity.type === "person" && <Users size={8} />}
      {entity.type === "project" && <FolderKanban size={8} />}
      {entity.name}
    </span>
  );
}

function StrengthBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    value >= 0.7
      ? "bg-emerald-500"
      : value >= 0.4
        ? "bg-amber-500"
        : "bg-[var(--lime-border)]";

  return (
    <div className="flex items-center gap-2" title={`Connection strength: ${pct}%`}>
      <div className="w-16 h-1 rounded-full bg-[var(--lime-border)] overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] text-[var(--lime-text-dim)]">{pct}%</span>
    </div>
  );
}

function ClusterCard({ cluster }: { cluster: CrossMeetingCluster }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-[var(--lime-surface-2)] rounded-lg border border-[var(--lime-border)]">
      <button
        onClick={() => setExpanded((e) => !e)}
        className="w-full text-left p-3 hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <Network size={13} style={{ color: "var(--accent)" }} />
              <h4 className="text-sm font-medium text-[var(--lime-text)] truncate">
                {cluster.label}
              </h4>
              {expanded ? (
                <ChevronDown size={12} className="text-[var(--lime-text-dim)]" />
              ) : (
                <ChevronRight size={12} className="text-[var(--lime-text-dim)]" />
              )}
            </div>
            <p className="text-xs text-[var(--lime-text-muted)] mt-1">{cluster.theme}</p>
          </div>

          <div className="flex flex-col items-end gap-1 shrink-0">
            <span className="text-[10px] text-[var(--lime-text-dim)]">
              {cluster.meetings.length} meetings
            </span>
            <span className="text-[10px] text-[var(--lime-text-dim)]">
              {cluster.connection_count} links
            </span>
          </div>
        </div>

        {/* Shared entities preview */}
        {cluster.shared_entities.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {cluster.shared_entities.slice(0, 5).map((entity, i) => (
              <EntityBadge key={i} entity={entity} />
            ))}
            {cluster.shared_entities.length > 5 && (
              <span className="text-[10px] text-[var(--lime-text-dim)] self-center">
                +{cluster.shared_entities.length - 5} more
              </span>
            )}
          </div>
        )}
      </button>

      {expanded && (
        <div className="border-t border-[var(--lime-border)] px-3 py-2 space-y-2">
          <p className="text-[10px] uppercase tracking-widest text-[var(--lime-text-dim)]">
            Connected Meetings
          </p>
          {cluster.meetings.map((m) => (
            <div
              key={m.id}
              className="flex items-center gap-2 p-2 rounded bg-[var(--lime-surface)] text-xs"
            >
              <div className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: "var(--accent)" }} />
              <span className="text-[var(--lime-text)] flex-1 truncate">{m.title}</span>
              <span className="text-[var(--lime-text-dim)] shrink-0">{m.date}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ContradictionCard({
  item,
}: {
  item: CrossMeetingData["contradictions"][number];
}) {
  return (
    <div className="flex items-start gap-3 p-3 rounded-lg bg-red-500/5 border border-red-500/20">
      <AlertTriangle size={14} className="text-red-400 mt-0.5 shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-xs text-[var(--lime-text)] selectable">{item.detail}</p>
        <div className="flex items-center gap-2 mt-1.5 text-[10px]">
          <span className="text-red-300">{item.meeting_a_title ?? item.meeting_a_id}</span>
          <span className="text-[var(--lime-text-dim)]">vs</span>
          <span className="text-red-300">{item.meeting_b_title ?? item.meeting_b_id}</span>
          <span className="text-[var(--lime-text-dim)] ml-auto">
            {Math.round(item.confidence * 100)}%
          </span>
        </div>
      </div>
    </div>
  );
}

interface Props {
  meetingId?: string;
}

export default function CrossMeetingConnections({ meetingId }: Props) {
  const { crossMeetingData, crossMeetingLoading, setCrossMeetingData, setCrossMeetingLoading } =
    useMeetingStore();
  const [activeFilter, setActiveFilter] = useState<ConnectionType | "all">("all");

  useEffect(() => {
    setCrossMeetingLoading(true);
    api
      .getCrossMeetingConnections(meetingId)
      .then((data) => setCrossMeetingData(data))
      .catch((err) => {
        console.error("Cross-meeting connections load failed:", err);
        setCrossMeetingData(null);
      })
      .finally(() => setCrossMeetingLoading(false));
  }, [meetingId, setCrossMeetingData, setCrossMeetingLoading]);

  if (crossMeetingLoading) {
    return (
      <div className="flex items-center justify-center gap-2 p-12 text-[var(--lime-text-muted)] text-sm">
        <Loader2 size={16} className="animate-spin" />
        Analyzing connections…
      </div>
    );
  }

  if (!crossMeetingData) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-[var(--lime-text-muted)] text-sm">
        <Network size={32} className="mb-3 opacity-30" />
        <p>No cross-meeting connections found.</p>
        <p className="text-xs text-[var(--lime-text-dim)] mt-1">
          Connections appear after analyzing multiple meetings.
        </p>
      </div>
    );
  }

  const filteredConnections =
    activeFilter === "all"
      ? crossMeetingData.connections
      : crossMeetingData.connections.filter((c) => c.connection_type === activeFilter);

  // Count connection types for filter badges
  const typeCounts = crossMeetingData.connections.reduce(
    (acc, c) => {
      if (c.connection_type) acc[c.connection_type] = (acc[c.connection_type] ?? 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  return (
    <div className="p-6 space-y-6 overflow-y-auto">
      {/* Header stats */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Network size={16} style={{ color: "var(--accent)" }} />
          <span className="text-sm font-medium text-[var(--lime-text)]">
            Cross-Meeting Intelligence
          </span>
        </div>
        <span className="text-xs text-[var(--lime-text-dim)]">
          {crossMeetingData.total_meetings_analyzed} meetings analyzed
        </span>
      </div>

      {/* Connection type filters */}
      <div className="flex flex-wrap gap-1.5">
        <button
          onClick={() => setActiveFilter("all")}
          className={`px-2 py-1 rounded-md text-[10px] font-medium transition-colors border ${
            activeFilter === "all"
              ? "border-[var(--accent)] text-[var(--accent)]"
              : "border-[var(--lime-border)] text-[var(--lime-text-muted)] hover:border-[#404040]"
          }`}
        >
          All ({crossMeetingData.connections.length})
        </button>
        {(Object.keys(CONNECTION_TYPE_META) as ConnectionType[]).map((type) => {
          const count = typeCounts[type] ?? 0;
          if (count === 0) return null;
          const meta = CONNECTION_TYPE_META[type];
          const Icon = meta.icon;
          return (
            <button
              key={type}
              onClick={() => setActiveFilter(type)}
              className={`flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-medium transition-colors border ${
                activeFilter === type
                  ? "border-current"
                  : "border-[var(--lime-border)] hover:border-[#404040]"
              }`}
              style={{ color: activeFilter === type ? meta.color : undefined }}
            >
              <Icon size={9} />
              {meta.label} ({count})
            </button>
          );
        })}
      </div>

      {/* Contradictions (always shown at top if present) */}
      {crossMeetingData.contradictions.length > 0 && (
        <section>
          <h3 className="flex items-center gap-2 text-xs uppercase tracking-widest text-red-400 mb-2">
            <AlertTriangle size={11} />
            Contradictions ({crossMeetingData.contradictions.length})
          </h3>
          <div className="space-y-2">
            {crossMeetingData.contradictions.map((c, i) => (
              <ContradictionCard key={i} item={c} />
            ))}
          </div>
        </section>
      )}

      {/* Clusters */}
      {crossMeetingData.clusters.length > 0 && (
        <section>
          <h3 className="text-xs uppercase tracking-widest text-[var(--lime-text-dim)] mb-2">
            Meeting Clusters
          </h3>
          <div className="space-y-2">
            {crossMeetingData.clusters.map((cluster) => (
              <ClusterCard key={cluster.id} cluster={cluster} />
            ))}
          </div>
        </section>
      )}

      {/* Individual connections */}
      <section>
        <h3 className="text-xs uppercase tracking-widest text-[var(--lime-text-dim)] mb-2">
          Connections ({filteredConnections.length})
        </h3>
        <div className="space-y-1.5">
          {filteredConnections.map((conn, i) => {
            const meta = conn.connection_type
              ? CONNECTION_TYPE_META[conn.connection_type]
              : null;
            const Icon = meta?.icon ?? Link2;

            return (
              <div
                key={i}
                className="flex items-start gap-3 p-3 rounded-lg bg-[var(--lime-surface-2)] border border-[var(--lime-border)]"
              >
                <Icon
                  size={13}
                  className="mt-0.5 shrink-0"
                  style={{ color: meta?.color ?? "var(--lime-text-dim)" }}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs text-[var(--lime-text-muted)]">
                      {conn.source_meeting_title ?? conn.source_meeting_id}
                    </span>
                    <ArrowRight size={10} className="text-[var(--lime-text-dim)]" />
                    <span className="text-xs text-[var(--lime-text)]">
                      {conn.meeting_title ?? conn.meeting_id}
                    </span>
                  </div>
                  <p className="text-xs text-[var(--lime-text)] selectable">
                    {conn.relationship}
                  </p>

                  {conn.shared_entities && conn.shared_entities.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1.5">
                      {conn.shared_entities.map((entity, j) => (
                        <EntityBadge key={j} entity={entity} />
                      ))}
                    </div>
                  )}

                  <div className="flex items-center gap-3 mt-1.5">
                    {conn.strength != null && <StrengthBar value={conn.strength} />}
                    {meta && (
                      <span
                        className="text-[10px] font-medium"
                        style={{ color: meta.color }}
                      >
                        {meta.label}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}

          {filteredConnections.length === 0 && (
            <p className="text-xs text-[var(--lime-text-dim)] p-3">
              No connections match this filter.
            </p>
          )}
        </div>
      </section>
    </div>
  );
}
