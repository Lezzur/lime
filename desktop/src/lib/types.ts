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
}

export interface Decision {
  id: string;
  description: string;
  context?: string;
  participants?: string[];
  confidence: number;
  source_quote?: string;
}

export interface Insight {
  id: string;
  type: string;
  content: string;
  confidence: number;
}

export interface Connection {
  meeting_id: string;
  meeting_title?: string;
  relationship: string;
  confidence: number;
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
  executive_summary?: string;
  sentiment?: string;
  action_items: ActionItem[];
  decisions: Decision[];
  topics: TopicSegment[];
  connections: Connection[];
  insights: Insight[];
}

export type PersonalityMode = "neutral" | "strategist" | "analyst" | "coach";

export interface AppSettings {
  llm_provider: "ollama" | "claude" | "openai";
  llm_model: string;
  transcription_provider: "whisper" | "deepgram" | "assemblyai";
  confidence_threshold: number;
  wake_word_enabled: boolean;
  wake_word: string;
  auto_analyze: boolean;
  audio_source: "microphone" | "system" | "both";
}
