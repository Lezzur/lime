import SwiftUI

/// Scrollable list of all past meetings with search and filter.
struct MeetingListView: View {
    @EnvironmentObject var appState: AppState
    @State private var meetings: [Meeting] = []
    @State private var searchText = ""
    @State private var isLoading = false

    var filteredMeetings: [Meeting] {
        if searchText.isEmpty { return meetings }
        return meetings.filter { meeting in
            meeting.title?.localizedCaseInsensitiveContains(searchText) == true ||
            meeting.participants.joined().localizedCaseInsensitiveContains(searchText)
        }
    }

    var body: some View {
        NavigationStack {
            Group {
                if isLoading && meetings.isEmpty {
                    ProgressView()
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if meetings.isEmpty {
                    ContentUnavailableView(
                        "No Meetings Yet",
                        systemImage: "mic.slash",
                        description: Text("Your recorded meetings will appear here.")
                    )
                } else {
                    List(filteredMeetings) { meeting in
                        NavigationLink(value: meeting.id) {
                            MeetingRow(meeting: meeting)
                        }
                    }
                    .listStyle(.plain)
                }
            }
            .navigationTitle("Meetings")
            .searchable(text: $searchText, prompt: "Search meetings...")
            .navigationDestination(for: String.self) { meetingID in
                MeetingDetailView(meetingID: meetingID)
            }
            .refreshable { await loadMeetings() }
            .task { await loadMeetings() }
        }
    }

    private func loadMeetings() async {
        isLoading = true
        defer { isLoading = false }
        do {
            meetings = try await appState.apiClient.listMeetings()
        } catch {
            print("[LIME] Failed to load meetings: \(error)")
        }
    }
}

struct MeetingRow: View {
    let meeting: Meeting

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(meeting.title ?? "Untitled Meeting")
                    .font(.headline)
                Spacer()
                StatusBadge(status: meeting.status)
            }

            HStack {
                Text(meeting.startedAt, style: .date)
                Text("·")
                if let duration = meeting.duration {
                    Text(formatDuration(duration))
                }
                if !meeting.participants.isEmpty {
                    Text("·")
                    Text(meeting.participants.joined(separator: ", "))
                        .lineLimit(1)
                }
            }
            .font(.caption)
            .foregroundStyle(.secondary)

            if !meeting.actionItems.isEmpty {
                Text("\(meeting.actionItems.count) action item\(meeting.actionItems.count == 1 ? "" : "s")")
                    .font(.caption2)
                    .foregroundStyle(.green)
            }
        }
        .padding(.vertical, 4)
    }

    private func formatDuration(_ interval: TimeInterval) -> String {
        let minutes = Int(interval) / 60
        if minutes < 60 { return "\(minutes)m" }
        return "\(minutes / 60)h \(minutes % 60)m"
    }
}

struct StatusBadge: View {
    let status: MeetingStatus

    var body: some View {
        Text(status.rawValue.capitalized)
            .font(.caption2.weight(.medium))
            .foregroundStyle(statusColor)
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(statusColor.opacity(0.15))
            .clipShape(Capsule())
    }

    private var statusColor: Color {
        switch status {
        case .recording: return .red
        case .processing: return .yellow
        case .ready: return .green
        case .failed: return .orange
        }
    }
}
