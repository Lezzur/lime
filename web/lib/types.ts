// Shared TypeScript types for LIME web app

export interface Meeting {
  id: string;
  title: string | null;
  status: "recording" | "processing" | "completed" | "failed";
  audio_source: "microphone" | "system";
  started_at: string;
  ended_at: string | null;
  duration_seconds: number | null;
  segment_count: number;
}

export interface TranscriptSegment {
  id: string;
  start_time: number;
  end_time: number;
  text: string;
  language: string | null;
  confidence: number | null;
  is_low_confidence: boolean;
  speaker: string | null;
  transcription_source: string;
}

export interface ActionItem {
  id: string;
  description: string;
  owner: string | null;
  deadline: string | null;
  priority: string;
  confidence: number;
  below_threshold: boolean;
  source_quote: string | null;
  source_start_time: number | null;
  source_end_time: number | null;
}

export interface Decision {
  id: string;
  description: string;
  context: string | null;
  participants: string[] | null;
  confidence: number;
  below_threshold: boolean;
  source_quote: string | null;
  source_start_time: number | null;
  source_end_time: number | null;
}

export interface TopicSegment {
  id: string;
  title: string;
  summary: string | null;
  start_time: number;
  end_time: number;
  order_index: number;
  confidence: number;
  below_threshold: boolean;
}

export interface Insight {
  type: string;
  title: string;
  description: string;
  reasoning: string | null;
  related_to: string | null;
  priority: string;
  confidence: number;
  below_threshold: boolean;
}

export interface Connections {
  people_referenced: Array<{ name: string; role?: string }>;
  projects_referenced: Array<{ name: string; status?: string }>;
  topics_referenced: Array<{ name: string }>;
  past_meeting_links: Array<{ meeting_id: string; title: string; relevance: string }>;
  contradictions: Array<{ description: string; context: string }>;
  open_threads: Array<{ description: string; from_meeting?: string }>;
}

export interface MeetingNotes {
  analysis_id: string;
  meeting_id: string;
  executive_summary: string;
  meeting_type: string | null;
  sentiment: string | null;
  overall_confidence: number;
  confidence_threshold: number;
  llm_provider: string | null;
  processed_at: string;
  processing_duration_seconds: number | null;
  action_items: ActionItem[];
  decisions: Decision[];
  topics: TopicSegment[];
  connections: Connections | null;
  insights: Insight[];
}

export interface SearchResult {
  query: string;
  segments: Array<{
    id: string;
    meeting_id: string;
    text: string;
    start_time: number;
    end_time: number;
    speaker: string | null;
    distance: number;
  }>;
  summaries: Array<{
    meeting_id: string;
    summary: string;
    distance: number;
  }>;
}

export interface VoiceMemo {
  id: string;
  created_at: string;
  duration_seconds: number;
  status: "pending" | "processing" | "completed";
  transcript?: string;
  structured?: string;
}

// Capture mode types
export type CaptureMode = "discreet" | "active";
export type GestureType = "single_tap" | "double_tap" | "long_press";
export type UrgencyLevel = 0 | 1 | 2 | 3; // 0=idle, 1=calm, 2=alert, 3=urgent

export interface CaptureAlert {
  id: string;
  timestamp: number;
  type: "contradiction" | "connection" | "action_item" | "insight";
  message: string;
  urgency: UrgencyLevel;
}

// Offline queue types
export interface OfflineRecording {
  id: string;
  created_at: number;
  blob: Blob;
  meeting_title?: string;
  type: "meeting" | "voice_memo";
  status: "queued" | "uploading" | "done" | "failed";
}

export type PersonalityMode = "scribe" | "thinking_partner" | "sparring_partner";
