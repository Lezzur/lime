import type { AudioDevice, Meeting, MeetingNotes, TranscriptSegment, AppSettings } from "./types";

const API_BASE = "http://127.0.0.1:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "Unknown error");
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

export const api = {
  // Audio devices
  getDevices: () => request<AudioDevice[]>("/api/devices"),

  // Meetings CRUD
  startMeeting: (deviceIndex?: number, title?: string) =>
    request<{ id: string }>("/api/meetings/start", {
      method: "POST",
      body: JSON.stringify({ device_index: deviceIndex, title }),
    }),
  stopMeeting: (id: string) =>
    request<{ id: string }>(`/api/meetings/${id}/stop`, { method: "POST" }),
  getMeetings: (page = 1, limit = 20, search?: string) => {
    const params = new URLSearchParams({ page: String(page), limit: String(limit) });
    if (search) params.set("q", search);
    return request<Meeting[]>(`/api/meetings?${params}`);
  },
  getMeeting: (id: string) => request<Meeting>(`/api/meetings/${id}`),

  // Notes & Analysis
  getMeetingNotes: (id: string) => request<MeetingNotes>(`/api/meetings/${id}/notes`),
  patchMeetingNotes: (id: string, data: Partial<MeetingNotes>) =>
    request<MeetingNotes>(`/api/meetings/${id}/notes`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  // Transcript
  getMeetingTranscript: (id: string) =>
    request<TranscriptSegment[]>(`/api/meetings/${id}/transcript`),
  patchTranscriptSegment: (meetingId: string, segmentId: string, text: string) =>
    request<TranscriptSegment>(`/api/meetings/${meetingId}/transcript/${segmentId}`, {
      method: "PATCH",
      body: JSON.stringify({ text }),
    }),

  // Search
  search: (q: string) => request<{ results: unknown[] }>(`/api/search?q=${encodeURIComponent(q)}`),

  // Settings
  getSettings: () => request<AppSettings>("/api/settings"),
  patchSettings: (data: Partial<AppSettings>) =>
    request<AppSettings>("/api/settings", { method: "PATCH", body: JSON.stringify(data) }),

  // Memory
  getMemory: (tier: "short-term" | "medium-term" | "long-term") =>
    request<{ content: string }>(`/api/memory/${tier}`),
  consolidateMemory: () =>
    request<{ status: string }>("/api/memory/consolidate", { method: "POST" }),
};
