import SwiftUI

/// Default meeting view — what it was about, how it ended, key decisions, action items.
struct ExecutiveSummaryView: View {
    let meeting: Meeting
    let notes: MeetingNotes

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {

                // Overview + outcome
                Section {
                    Text(notes.summary.overview)
                        .font(.body)

                    if !notes.summary.outcome.isEmpty {
                        Label {
                            Text(notes.summary.outcome)
                                .font(.subheadline)
                        } icon: {
                            Image(systemName: "flag.fill")
                                .foregroundStyle(.green)
                        }
                    }
                } header: {
                    SectionHeader(title: "Overview", icon: "doc.text")
                }

                // Key decisions
                if !notes.summary.keyDecisions.isEmpty {
                    Section {
                        ForEach(notes.summary.keyDecisions, id: \.self) { decision in
                            HStack(alignment: .top, spacing: 10) {
                                Image(systemName: "checkmark.diamond.fill")
                                    .foregroundStyle(.blue)
                                    .font(.caption)
                                    .padding(.top, 2)
                                Text(decision)
                                    .font(.subheadline)
                            }
                        }
                    } header: {
                        SectionHeader(title: "Key Decisions", icon: "arrow.triangle.branch")
                    }
                }

                // Action items
                if !notes.actionItems.isEmpty {
                    Section {
                        ForEach(notes.actionItems) { item in
                            ActionItemRow(item: item)
                        }
                    } header: {
                        SectionHeader(title: "Action Items", icon: "checklist")
                    }
                }

                // Bookmarks
                if !meeting.bookmarks.isEmpty {
                    Section {
                        ForEach(meeting.bookmarks) { bookmark in
                            BookmarkRow(bookmark: bookmark)
                        }
                    } header: {
                        SectionHeader(title: "Your Captures", icon: "bookmark.fill")
                    }
                }

                // Insights & connections
                if !meeting.connections.isEmpty {
                    Section {
                        ForEach(meeting.connections) { connection in
                            HStack(alignment: .top, spacing: 10) {
                                Image(systemName: "link")
                                    .foregroundStyle(.purple)
                                    .font(.caption)
                                    .padding(.top, 2)
                                VStack(alignment: .leading) {
                                    Text(connection.description)
                                        .font(.subheadline)
                                    if connection.confidence < 0.7 {
                                        ConfidenceBadge(confidence: connection.confidence)
                                    }
                                }
                            }
                        }
                    } header: {
                        SectionHeader(title: "Connections", icon: "point.3.connected.trianglepath.dotted")
                    }
                }

                // Unresolved questions
                if !notes.summary.unresolvedQuestions.isEmpty {
                    Section {
                        ForEach(notes.summary.unresolvedQuestions, id: \.self) { question in
                            HStack(alignment: .top, spacing: 10) {
                                Image(systemName: "questionmark.circle")
                                    .foregroundStyle(.orange)
                                    .font(.caption)
                                    .padding(.top, 2)
                                Text(question)
                                    .font(.subheadline)
                            }
                        }
                    } header: {
                        SectionHeader(title: "Open Questions", icon: "questionmark.bubble")
                    }
                }
            }
            .padding()
        }
    }
}

// MARK: - Supporting Views

struct SectionHeader: View {
    let title: String
    let icon: String

    var body: some View {
        Label(title, systemImage: icon)
            .font(.headline)
            .foregroundStyle(.primary)
    }
}

struct ActionItemRow: View {
    let item: ActionItem

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: item.completed ? "checkmark.circle.fill" : "circle")
                .foregroundStyle(item.completed ? .green : .secondary)
                .font(.body)

            VStack(alignment: .leading, spacing: 2) {
                Text(item.description)
                    .font(.subheadline)
                    .strikethrough(item.completed)

                HStack(spacing: 8) {
                    if let owner = item.owner {
                        Text(owner)
                            .font(.caption)
                            .foregroundStyle(.blue)
                    }
                    if let deadline = item.deadline {
                        Text(deadline)
                            .font(.caption)
                            .foregroundStyle(.orange)
                    }
                }
            }
        }
    }
}

struct BookmarkRow: View {
    let bookmark: Bookmark

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: bookmark.priority == .high ? "flag.fill" : "bookmark.fill")
                .foregroundStyle(bookmark.priority == .high ? .red : .yellow)

            VStack(alignment: .leading) {
                Text(formatTimestamp(bookmark.timestamp))
                    .font(.subheadline.monospacedDigit())
                if let annotation = bookmark.annotation {
                    Text(annotation)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            Spacer()

            if bookmark.audioAnnotationURL != nil {
                Image(systemName: "waveform")
                    .foregroundStyle(.green)
                    .font(.caption)
            }
        }
    }

    private func formatTimestamp(_ interval: TimeInterval) -> String {
        let minutes = Int(interval) / 60
        let seconds = Int(interval) % 60
        return String(format: "%d:%02d", minutes, seconds)
    }
}
