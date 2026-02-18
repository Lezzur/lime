import SwiftUI

/// App settings: LLM provider, confidence threshold, wake word, capture preferences.
struct SettingsView: View {
    @EnvironmentObject var appState: AppState
    @State private var storageUsed: String = "Calculating..."

    var body: some View {
        NavigationStack {
            Form {
                // Agent
                Section("Agent") {
                    Picker("Default Mode", selection: $appState.agentMode) {
                        ForEach(AgentMode.allCases, id: \.self) { mode in
                            Text(mode.rawValue).tag(mode)
                        }
                    }

                    HStack {
                        Text("Wake Word")
                        Spacer()
                        TextField("Wake word", text: $appState.wakeWord)
                            .multilineTextAlignment(.trailing)
                            .foregroundStyle(.secondary)
                    }
                }

                // AI Processing
                Section("AI Processing") {
                    Toggle("Use Cloud LLM", isOn: $appState.useCloudLLM)
                    Toggle("Use Cloud Transcription", isOn: $appState.useCloudTranscription)

                    VStack(alignment: .leading, spacing: 4) {
                        HStack {
                            Text("Confidence Threshold")
                            Spacer()
                            Text("\(Int(appState.confidenceThreshold * 100))%")
                                .foregroundStyle(.secondary)
                        }
                        Slider(value: $appState.confidenceThreshold, in: 0.3...0.95, step: 0.05)
                            .tint(.green)
                        Text("Items below this threshold show a confidence badge.")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }

                // Capture
                Section("Capture") {
                    Picker("Default Mode", selection: $appState.captureMode) {
                        Text("Discreet").tag(CaptureMode.discreet)
                        Text("Active").tag(CaptureMode.active)
                    }
                }

                // Storage
                Section("Storage") {
                    HStack {
                        Text("Audio Files")
                        Spacer()
                        Text(storageUsed)
                            .foregroundStyle(.secondary)
                    }
                }

                // Security
                Section("Security") {
                    HStack {
                        Text("Authentication")
                        Spacer()
                        Text(biometricLabel)
                            .foregroundStyle(.secondary)
                    }
                }

                // About
                Section("About") {
                    HStack {
                        Text("Version")
                        Spacer()
                        Text("1.0.0")
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .navigationTitle("Settings")
            .onChange(of: appState.useCloudLLM) { _, _ in appState.saveSettings() }
            .onChange(of: appState.useCloudTranscription) { _, _ in appState.saveSettings() }
            .onChange(of: appState.confidenceThreshold) { _, _ in appState.saveSettings() }
            .onChange(of: appState.wakeWord) { _, _ in appState.saveSettings() }
            .task { calculateStorage() }
        }
    }

    private var biometricLabel: String {
        switch appState.biometricAuth.availableBiometric {
        case .faceID: return "Face ID"
        case .touchID: return "Touch ID"
        case .none: return "Passcode"
        }
    }

    private func calculateStorage() {
        let bytes = AudioFileManager().totalStorageUsed()
        let formatter = ByteCountFormatter()
        formatter.countStyle = .file
        storageUsed = formatter.string(fromByteCount: bytes)
    }
}
