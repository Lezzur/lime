import AVFoundation
import Combine

/// Handles voice memo recording with auto-end on 15 seconds of silence.
final class VoiceMemoCapture: ObservableObject {

    @Published var isRecording = false
    @Published var duration: TimeInterval = 0

    private var audioRecorder: AVAudioRecorder?
    private var silenceTimer: Timer?
    private var durationTimer: Timer?
    private var startTime: Date?
    private let fileManager = AudioFileManager()

    /// Consecutive seconds of silence detected
    private var silentSeconds: Double = 0

    /// Threshold in dB below which audio is considered silence
    private let silenceThreshold: Float = -40.0

    /// Seconds of continuous silence before auto-ending
    private let silenceTimeout: TimeInterval = 15.0

    var onComplete: ((URL) -> Void)?

    // MARK: - Control

    func startRecording() throws {
        let url = fileManager.newVoiceMemoURL()

        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatLinearPCM),
            AVSampleRateKey: 44100.0,
            AVNumberOfChannelsKey: 1,
            AVLinearPCMBitDepthKey: 16,
            AVLinearPCMIsFloatKey: false
        ]

        audioRecorder = try AVAudioRecorder(url: url, settings: settings)
        audioRecorder?.isMeteringEnabled = true
        audioRecorder?.record()

        isRecording = true
        startTime = Date()
        silentSeconds = 0

        startSilenceDetection()
        startDurationTracking()

        print("[LIME] Voice memo started: \(url.lastPathComponent)")
    }

    func stopRecording() {
        guard isRecording else { return }

        let url = audioRecorder?.url
        audioRecorder?.stop()
        audioRecorder = nil
        isRecording = false
        silenceTimer?.invalidate()
        durationTimer?.invalidate()
        duration = 0

        print("[LIME] Voice memo stopped")

        if let url {
            onComplete?(url)
        }
    }

    // MARK: - Silence Detection

    private func startSilenceDetection() {
        silenceTimer = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] _ in
            guard let self, let recorder = self.audioRecorder else { return }
            recorder.updateMeters()

            let level = recorder.averagePower(forChannel: 0)

            if level < self.silenceThreshold {
                self.silentSeconds += 0.5
                if self.silentSeconds >= self.silenceTimeout {
                    DispatchQueue.main.async {
                        self.stopRecording()
                    }
                }
            } else {
                self.silentSeconds = 0
            }
        }
    }

    private func startDurationTracking() {
        durationTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
            guard let self, let start = self.startTime else { return }
            DispatchQueue.main.async {
                self.duration = Date().timeIntervalSince(start)
            }
        }
    }
}
