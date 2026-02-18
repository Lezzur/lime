import { create } from "zustand";
import type { AudioDevice, Meeting, MeetingNotes, PersonalityMode, SparringConfig, CrossMeetingData } from "../lib/types";

export type ActiveView = "meetings" | "memos" | "search" | "memory" | "settings";
export type MeetingSubView = "summary" | "timeline" | "transcript" | "topics" | "connections";

interface MeetingState {
  // Navigation
  activeView: ActiveView;
  setActiveView: (view: ActiveView) => void;

  // Recording
  isRecording: boolean;
  activeMeetingId: string | null;
  selectedDeviceId: number | null;
  audioDevices: AudioDevice[];
  startRecording: (meetingId: string) => void;
  stopRecording: () => void;
  setSelectedDevice: (id: number | null) => void;
  setAudioDevices: (devices: AudioDevice[]) => void;

  // Meeting list & detail
  meetings: Meeting[];
  selectedMeetingId: string | null;
  selectedMeetingNotes: MeetingNotes | null;
  meetingSubView: MeetingSubView;
  selectedTopicId: string | null;
  setMeetings: (meetings: Meeting[]) => void;
  selectMeeting: (id: string | null) => void;
  setMeetingNotes: (notes: MeetingNotes | null) => void;
  setMeetingSubView: (view: MeetingSubView) => void;
  setSelectedTopicId: (id: string | null) => void;

  // Cross-meeting connections
  crossMeetingData: CrossMeetingData | null;
  crossMeetingLoading: boolean;
  setCrossMeetingData: (data: CrossMeetingData | null) => void;
  setCrossMeetingLoading: (loading: boolean) => void;

  // Personality
  personalityMode: PersonalityMode;
  sparringConfig: SparringConfig;
  setPersonalityMode: (mode: PersonalityMode) => void;
  setSparringIntensity: (intensity: number) => void;
  setSparringFocusAreas: (areas: SparringConfig["focus_areas"]) => void;
  quickExitSparring: () => void;
}

export const useMeetingStore = create<MeetingState>((set) => ({
  activeView: "meetings",
  setActiveView: (view) => set({ activeView: view }),

  isRecording: false,
  activeMeetingId: null,
  selectedDeviceId: null,
  audioDevices: [],
  startRecording: (meetingId) => set({ isRecording: true, activeMeetingId: meetingId }),
  stopRecording: () => set({ isRecording: false, activeMeetingId: null }),
  setSelectedDevice: (id) => set({ selectedDeviceId: id }),
  setAudioDevices: (devices) => set({ audioDevices: devices }),

  meetings: [],
  selectedMeetingId: null,
  selectedMeetingNotes: null,
  meetingSubView: "summary",
  selectedTopicId: null,
  setMeetings: (meetings) => set({ meetings }),
  selectMeeting: (id) => set({ selectedMeetingId: id, selectedMeetingNotes: null, selectedTopicId: null, meetingSubView: "summary", crossMeetingData: null }),
  setMeetingNotes: (notes) => set({ selectedMeetingNotes: notes }),
  setMeetingSubView: (view) => set({ meetingSubView: view }),
  setSelectedTopicId: (id) => set({ selectedTopicId: id }),

  crossMeetingData: null,
  crossMeetingLoading: false,
  setCrossMeetingData: (data) => set({ crossMeetingData: data }),
  setCrossMeetingLoading: (loading) => set({ crossMeetingLoading: loading }),

  personalityMode: "thinking-partner",
  sparringConfig: { intensity: 5, focus_areas: ["logic", "assumptions"] },
  setPersonalityMode: (mode) => set({ personalityMode: mode }),
  setSparringIntensity: (intensity) =>
    set((state) => ({ sparringConfig: { ...state.sparringConfig, intensity: Math.max(1, Math.min(10, intensity)) } })),
  setSparringFocusAreas: (areas) =>
    set((state) => ({ sparringConfig: { ...state.sparringConfig, focus_areas: areas } })),
  quickExitSparring: () => set({ personalityMode: "thinking-partner" }),
}));
