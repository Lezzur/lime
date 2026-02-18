import SwiftUI

/// Three-view meeting detail: Executive Summary (default), Timeline, Annotated Transcript.
struct MeetingDetailView: View {
    let meetingID: String
    @EnvironmentObject var appState: AppState
    @State private var meeting: Meeting?
    @State private var notes: MeetingNotes?
    @State private var selectedView: MeetingViewType = .summary
    @State private var isLoading = true

    var body: some View {
        Group {
            if isLoading {
                ProgressView("Loading meeting...")
            } else if let meeting, let notes {
                VStack(spacing: 0) {
                    // View switcher
                    Picker("View", selection: $selectedView) {
                        ForEach(MeetingViewType.allCases, id: \.self) { type in
                            Text(type.rawValue).tag(type)
                        }
                    }
                    .pickerStyle(.segmented)
                    .padding()

                    // Selected view content
                    switch selectedView {
                    case .summary:
                        ExecutiveSummaryView(meeting: meeting, notes: notes)
                    case .timeline:
                        TimelineView(topics: notes.topics)
                    case .transcript:
                        TranscriptView(meetingID: meetingID)
                    }
                }
            } else {
                ContentUnavailableView(
                    "Meeting Not Found",
                    systemImage: "exclamationmark.triangle"
                )
            }
        }
        .navigationTitle(meeting?.title ?? "Meeting")
        .navigationBarTitleDisplayMode(.inline)
        .task { await loadMeeting() }
    }

    private func loadMeeting() async {
        defer { isLoading = false }
        do {
            meeting = try await appState.apiClient.getMeeting(id: meetingID)
            notes = try await appState.apiClient.getNotes(meetingID: meetingID)
        } catch {
            print("[LIME] Failed to load meeting: \(error)")
        }
    }
}

enum MeetingViewType: String, CaseIterable {
    case summary = "Summary"
    case timeline = "Timeline"
    case transcript = "Transcript"
}
