import type {
  Meeting,
  TranscriptSegment,
  MeetingNotes,
  SearchResult,
} from "./types";

const BASE = "/api/lime";

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ── Meetings ─────────────────────────────────────────────────────────────────

export const getMeetings = (limit = 50, offset = 0) =>
  request<Meeting[]>(`/meetings?limit=${limit}&offset=${offset}`);

export const getMeeting = (id: string) =>
  request<Meeting>(`/meetings/${id}`);

export const getTranscript = (id: string) =>
  request<TranscriptSegment[]>(`/meetings/${id}/transcript`);

export const getMeetingNotes = (id: string) =>
  request<MeetingNotes>(`/meetings/${id}/notes`);

export const editMeetingNotes = (
  id: string,
  data: Partial<{ executive_summary: string; action_items: object[]; decisions: object[] }>
) =>
  request<{ status: string }>(`/meetings/${id}/notes`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const startMeeting = (source: "microphone" | "system", title?: string) =>
  request<{ meeting_id: string; status: string }>("/meetings/start", {
    method: "POST",
    body: JSON.stringify({ source, title }),
  });

export const stopMeeting = (id: string) =>
  request<{ meeting_id: string; duration_seconds: number; status: string }>(
    `/meetings/${id}/stop`,
    { method: "POST" }
  );

export const analyzeMeeting = (id: string) =>
  request<{ meeting_id: string; status: string }>(`/meetings/${id}/analyze`, {
    method: "POST",
  });

export const correctTranscript = (
  meetingId: string,
  segmentId: string,
  correctedText: string
) =>
  request<{ status: string }>(
    `/meetings/${meetingId}/transcript/${segmentId}`,
    {
      method: "PATCH",
      body: JSON.stringify({ segment_id: segmentId, corrected_text: correctedText }),
    }
  );

export const generateBriefing = (
  meetingId: string,
  participants: string[],
  purpose: string
) =>
  request<{ briefing: string }>(`/meetings/${meetingId}/briefing`, {
    method: "POST",
    body: JSON.stringify({ participants, purpose }),
  });

// ── Search ────────────────────────────────────────────────────────────────────

export const search = (q: string, nResults = 10) =>
  request<SearchResult>(`/search?q=${encodeURIComponent(q)}&n_results=${nResults}`);

// ── Memory ────────────────────────────────────────────────────────────────────

export const getMemory = (tier: "short-term" | "medium-term" | "long-term") =>
  request<{ tier: string; content: string }>(`/memory/${tier}`);

export const updateMemory = (
  tier: "short-term" | "medium-term" | "long-term",
  content: string
) =>
  request<{ status: string }>(`/memory/${tier}`, {
    method: "PATCH",
    body: JSON.stringify({ content }),
  });

export const triggerConsolidation = () =>
  request<{ status: string }>("/memory/consolidate", { method: "POST" });

// ── Knowledge ─────────────────────────────────────────────────────────────────

export const getPeople = () =>
  request<Array<{ id: string; name: string; role?: string; org?: string }>>(
    "/knowledge/people"
  );

// ── Audio ─────────────────────────────────────────────────────────────────────

export function getAudioUrl(meetingId: string): string {
  return `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/meetings/${meetingId}/audio`;
}
