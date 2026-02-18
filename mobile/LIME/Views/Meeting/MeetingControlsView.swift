import SwiftUI

/// Main capture tab — start/stop recording with mode selection.
struct MeetingControlsView: View {
    @EnvironmentObject var appState: AppState
    @State private var showError: String?

    var body: some View {
        if appState.isRecording {
            // During recording: show the selected capture mode
            Group {
                switch appState.captureMode {
                case .discreet:
                    DiscreetModeView()
                case .active:
                    ActiveModeView()
                }
            }
            .gesture(
                // Triple tap to stop recording (emergency exit)
                TapGesture(count: 3).onEnded {
                    Task { try? await appState.stopRecording() }
                }
            )
        } else {
            // Pre-recording: mode selection and start button
            preRecordingView
        }
    }

    private var preRecordingView: some View {
        NavigationStack {
            VStack(spacing: 32) {
                Spacer()

                // Mode selector
                VStack(spacing: 16) {
                    Text("Capture Mode")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)

                    Picker("Mode", selection: $appState.captureMode) {
                        ForEach(CaptureMode.allCases, id: \.self) { mode in
                            Text(mode.rawValue.capitalized).tag(mode)
                        }
                    }
                    .pickerStyle(.segmented)
                    .frame(maxWidth: 240)
                }

                // Agent mode
                VStack(spacing: 16) {
                    Text("Agent Mode")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)

                    Picker("Agent", selection: $appState.agentMode) {
                        ForEach(AgentMode.allCases, id: \.self) { mode in
                            Text(mode.rawValue).tag(mode)
                        }
                    }
                    .pickerStyle(.segmented)
                    .frame(maxWidth: 320)
                }

                Spacer()

                // Record button
                Button {
                    startRecording()
                } label: {
                    ZStack {
                        Circle()
                            .fill(Color.green.opacity(0.15))
                            .frame(width: 120, height: 120)

                        Circle()
                            .fill(Color.green)
                            .frame(width: 80, height: 80)

                        Image(systemName: "mic.fill")
                            .font(.system(size: 32))
                            .foregroundStyle(.black)
                    }
                }

                Text("Tap to start recording")
                    .font(.caption)
                    .foregroundStyle(.secondary)

                Spacer()
                    .frame(height: 60)
            }
            .padding()
            .navigationTitle("LIME")
            .alert("Recording Error", isPresented: .init(
                get: { showError != nil },
                set: { if !$0 { showError = nil } }
            )) {
                Button("OK") { showError = nil }
            } message: {
                Text(showError ?? "")
            }
        }
    }

    private func startRecording() {
        Task {
            do {
                appState.hapticEngine.playRecordingStarted()
                try await appState.startRecording()
            } catch {
                showError = error.localizedDescription
                print("[LIME] Failed to start recording: \(error)")
            }
        }
    }
}
