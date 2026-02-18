import SwiftUI

/// List of voice memos with quick recording access.
struct VoiceMemoListView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var capture = VoiceMemoCapture()
    @State private var memos: [VoiceMemo] = []
    @State private var isLoading = false

    var body: some View {
        NavigationStack {
            Group {
                if memos.isEmpty && !isLoading {
                    ContentUnavailableView(
                        "No Voice Memos",
                        systemImage: "waveform",
                        description: Text("Tap the record button to capture a thought.")
                    )
                } else {
                    List(memos) { memo in
                        VoiceMemoRow(memo: memo)
                    }
                    .listStyle(.plain)
                }
            }
            .navigationTitle("Voice Memos")
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        toggleRecording()
                    } label: {
                        Image(systemName: capture.isRecording ? "stop.circle.fill" : "mic.circle.fill")
                            .font(.title2)
                            .foregroundStyle(capture.isRecording ? .red : .green)
                    }
                }
            }
            .overlay(alignment: .bottom) {
                if capture.isRecording {
                    RecordingBanner(duration: capture.duration) {
                        capture.stopRecording()
                    }
                    .transition(.move(edge: .bottom))
                }
            }
            .refreshable { await loadMemos() }
            .task { await loadMemos() }
        }
    }

    private func toggleRecording() {
        if capture.isRecording {
            capture.stopRecording()
        } else {
            appState.hapticEngine.playRecordingStarted()
            capture.onComplete = { url in
                Task {
                    let data = (try? Data(contentsOf: url)) ?? Data()
                    _ = try? await appState.apiClient.uploadVoiceMemo(
                        audioData: data,
                        agentMode: appState.agentMode.rawValue
                    )
                    await loadMemos()
                }
            }
            try? capture.startRecording()
        }
    }

    private func loadMemos() async {
        isLoading = true
        defer { isLoading = false }
        do {
            memos = try await appState.apiClient.listVoiceMemos()
        } catch {
            print("[LIME] Failed to load voice memos: \(error)")
        }
    }
}

struct VoiceMemoRow: View {
    let memo: VoiceMemo

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(memo.createdAt, style: .date)
                    .font(.subheadline.weight(.medium))
                Text(memo.createdAt, style: .time)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Spacer()
                StatusBadge(status: memoStatus)
            }

            if let transcript = memo.rawTranscript {
                Text(transcript)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }

            if let structured = memo.structuredNote {
                Text(structured)
                    .font(.caption)
                    .lineLimit(3)
            }

            Text(formatDuration(memo.duration))
                .font(.caption2.monospacedDigit())
                .foregroundStyle(.secondary)
        }
        .padding(.vertical, 4)
    }

    private var memoStatus: MeetingStatus {
        switch memo.status {
        case .recorded, .queued: return .processing
        case .processing: return .processing
        case .ready: return .ready
        case .failed: return .failed
        }
    }

    private func formatDuration(_ interval: TimeInterval) -> String {
        let seconds = Int(interval)
        if seconds < 60 { return "\(seconds)s" }
        return "\(seconds / 60)m \(seconds % 60)s"
    }
}

struct RecordingBanner: View {
    let duration: TimeInterval
    let onStop: () -> Void

    var body: some View {
        HStack {
            Circle()
                .fill(Color.red)
                .frame(width: 10, height: 10)

            Text("Recording")
                .font(.subheadline.weight(.medium))

            Text(String(format: "%.1fs", duration))
                .font(.subheadline.monospacedDigit())
                .foregroundStyle(.secondary)

            Spacer()

            Button("Stop", action: onStop)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(.red)
        }
        .padding()
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .padding()
    }
}
