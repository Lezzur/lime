import { create } from "zustand";
import type { AudioDevice, Meeting, MeetingNotes, PersonalityMode } from "../lib/types";

export type ActiveView = "meetings" | "memos" | "search" | "memory" | "settings";
export type MeetingSubView = "summary" | "timeline" | "transcript" | "topics";

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

  // Personality
  personalityMode: PersonalityMode;
  setPersonalityMode: (mode: PersonalityMode) => void;
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
  selectMeeting: (id) => set({ selectedMeetingId: id, selectedMeetingNotes: null, selectedTopicId: null, meetingSubView: "summary" }),
  setMeetingNotes: (notes) => set({ selectedMeetingNotes: notes }),
  setMeetingSubView: (view) => set({ meetingSubView: view }),
  setSelectedTopicId: (id) => set({ selectedTopicId: id }),

  personalityMode: "neutral",
  setPersonalityMode: (mode) => set({ personalityMode: mode }),
}));
