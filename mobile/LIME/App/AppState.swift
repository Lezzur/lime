import SwiftUI
import Combine

enum AppTab: Hashable {
    case capture, meetings, memos, memory, settings
}

enum CaptureMode: String, CaseIterable {
    case discreet
    case active
}

enum AgentMode: String, CaseIterable {
    case scribe = "Scribe"
    case thinkingPartner = "Thinking Partner"
    case sparringPartner = "Sparring Partner"
}

@MainActor
final class AppState: ObservableObject {

    // MARK: - Navigation
    @Published var selectedTab: AppTab = .capture

    // MARK: - Auth
    @Published var isAuthenticated = false
    @Published var hasCompletedOnboarding: Bool

    // MARK: - Recording
    @Published var isRecording = false
    @Published var captureMode: CaptureMode = .discreet
    @Published var currentMeetingID: String?
    @Published var recordingDuration: TimeInterval = 0

    // MARK: - Agent
    @Published var agentMode: AgentMode = .thinkingPartner

    // MARK: - Settings
    @Published var wakeWord: String
    @Published var confidenceThreshold: Double
    @Published var useCloudLLM: Bool
    @Published var useCloudTranscription: Bool

    // MARK: - Services
    let audioEngine: AudioEngine
    let apiClient: APIClient
    let biometricAuth: BiometricAuth
    let hapticEngine: HapticEngine
    let syncEngine: SyncEngine

    private var cancellables = Set<AnyCancellable>()

    init() {
        let defaults = UserDefaults.standard
        self.hasCompletedOnboarding = defaults.bool(forKey: "hasCompletedOnboarding")
        self.wakeWord = defaults.string(forKey: "wakeWord") ?? "Hey Lime"
        self.confidenceThreshold = defaults.double(forKey: "confidenceThreshold").nonZero ?? 0.7
        self.useCloudLLM = defaults.bool(forKey: "useCloudLLM")
        self.useCloudTranscription = defaults.bool(forKey: "useCloudTranscription")

        self.audioEngine = AudioEngine()
        self.apiClient = APIClient()
        self.biometricAuth = BiometricAuth()
        self.hapticEngine = HapticEngine()
        self.syncEngine = SyncEngine(apiClient: APIClient())

        bindAudioEngine()
    }

    // MARK: - Auth

    func authenticate() async {
        let success = await biometricAuth.authenticate()
        isAuthenticated = success
    }

    // MARK: - Recording Control

    func startRecording() async throws {
        let meetingID = try await apiClient.startMeeting()
        currentMeetingID = meetingID
        try audioEngine.startCapture()
        isRecording = true
    }

    func stopRecording() async throws {
        audioEngine.stopCapture()
        isRecording = false
        recordingDuration = 0

        if let meetingID = currentMeetingID {
            try await apiClient.stopMeeting(id: meetingID)
            currentMeetingID = nil
        }
    }

    func addBookmark() {
        guard isRecording, let meetingID = currentMeetingID else { return }
        let timestamp = audioEngine.currentTimestamp
        hapticEngine.playTap()

        Task {
            try? await apiClient.addBookmark(
                meetingID: meetingID,
                timestamp: timestamp,
                priority: .normal
            )
        }
    }

    func addPriorityFlag() {
        guard isRecording, let meetingID = currentMeetingID else { return }
        let timestamp = audioEngine.currentTimestamp
        hapticEngine.playDoubleTap()

        Task {
            try? await apiClient.addBookmark(
                meetingID: meetingID,
                timestamp: timestamp,
                priority: .high
            )
        }
    }

    // MARK: - Persistence

    func completeOnboarding() {
        hasCompletedOnboarding = true
        UserDefaults.standard.set(true, forKey: "hasCompletedOnboarding")
    }

    func saveSettings() {
        let defaults = UserDefaults.standard
        defaults.set(wakeWord, forKey: "wakeWord")
        defaults.set(confidenceThreshold, forKey: "confidenceThreshold")
        defaults.set(useCloudLLM, forKey: "useCloudLLM")
        defaults.set(useCloudTranscription, forKey: "useCloudTranscription")
    }

    // MARK: - Private

    private func bindAudioEngine() {
        audioEngine.$currentTimestamp
            .receive(on: DispatchQueue.main)
            .assign(to: &$recordingDuration)
    }
}

private extension Double {
    var nonZero: Double? {
        self == 0 ? nil : self
    }
}
