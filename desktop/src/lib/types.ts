export interface AudioDevice {
  id: number;
  name: string;
  channels: number;
  is_default: boolean;
  direction: "input" | "output";
}

export interface Meeting {
  id: string;
  title?: string;
  status: "recording" | "processing" | "completed" | "failed";
  started_at: string;
  ended_at?: string;
  duration_seconds?: number;
  audio_source: string;
}

export interface TranscriptSegment {
  id: string;
  speaker_id?: string;
  speaker_label?: string;
  speaker_name?: string;
  start_time: number;
  end_time: number;
  text: string;
  confidence?: number;
}

export interface ActionItem {
  id: string;
  description: string;
  owner?: string;
  deadline?: string;
  priority: "high" | "medium" | "low";
  confidence: number;
  source_quote?: string;
  below_threshold?: boolean;
  source_start_time?: number;
  source_end_time?: number;
}

export interface Decision {
  id: string;
  description: string;
  context?: string;
  participants?: string[];
  confidence: number;
  source_quote?: string;
  below_threshold?: boolean;
  source_start_time?: number;
  source_end_time?: number;
}

export interface Insight {
  id: string;
  type: string;
  title?: string;
  description?: string;
  content: string;
  priority?: "high" | "medium" | "low";
  reasoning?: string;
  confidence: number;
}

export type ConnectionType =
  | "shared_topic"
  | "shared_person"
  | "follow_up"
  | "contradiction"
  | "decision_referenced"
  | "action_dependency"
  | "recurring_theme";

export interface SharedEntity {
  type: "person" | "project" | "topic" | "decision" | "action_item";
  name: string;
  context?: string;
}

export interface Connection {
  meeting_id: string;
  meeting_title?: string;
  meeting_date?: string;
  relationship: string;
  connection_type?: ConnectionType;
  shared_entities?: SharedEntity[];
  strength?: number; // 0-1
  confidence: number;
  is_contradiction?: boolean;
  contradiction_detail?: string;
}

export interface CrossMeetingCluster {
  id: string;
  label: string;
  theme: string;
  meeting_ids: string[];
  meetings: { id: string; title: string; date: string }[];
  shared_entities: SharedEntity[];
  connection_count: number;
  strongest_link: number;
}

export interface CrossMeetingData {
  clusters: CrossMeetingCluster[];
  connections: (Connection & { source_meeting_id: string; source_meeting_title?: string })[];
  total_meetings_analyzed: number;
  contradictions: {
    meeting_a_id: string;
    meeting_a_title?: string;
    meeting_b_id: string;
    meeting_b_title?: string;
    detail: string;
    confidence: number;
  }[];
}

export interface TopicSegment {
  id: string;
  title: string;
  summary: string;
  start_time: number;
  end_time: number;
  order_index: number;
  confidence: number;
  insights?: Insight[];
  connections?: Connection[];
  action_items?: ActionItem[];
}

export interface MeetingNotes {
  analysis_id?: string;
  executive_summary?: string;
  sentiment?: string;
  overall_confidence?: number;
  action_items: ActionItem[];
  decisions: Decision[];
  topics: TopicSegment[];
  connections: Connection[];
  insights: Insight[];
}

export interface ConnectionsData {
  meeting_id: string;
  meeting_title?: string;
  connections: Connection[];
}

export type PersonalityMode = "scribe" | "thinking-partner" | "sparring";

export interface SparringConfig {
  intensity: number; // 1-10
  focus_areas: ("logic" | "assumptions" | "feasibility" | "risks" | "alternatives")[];
}

export interface AppSettings {
  llm_provider: "ollama" | "claude" | "openai";
  llm_model: string;
  transcription_provider: "whisper" | "deepgram" | "assemblyai";
  confidence_threshold: number;
  wake_word_enabled: boolean;
  wake_word: string;
  auto_analyze: boolean;
  audio_source: "microphone" | "system" | "both";
  personality_mode: PersonalityMode;
  sparring_config: SparringConfig;
}
