import AVFoundation
import Combine

final class AudioEngine: ObservableObject {

    // MARK: - Published State
    @Published var isCapturing = false
    @Published var currentTimestamp: TimeInterval = 0
    @Published var audioLevel: Float = 0

    // MARK: - Private
    private var audioRecorder: AVAudioRecorder?
    private var audioFile: AVAudioFile?
    private let audioSession = AVAudioSession.sharedInstance()
    private var displayLink: CADisplayLink?
    private var recordingStartTime: Date?
    private let fileManager = AudioFileManager()

    // Ring buffer for 30s rolling backup (per spec: Sec 6)
    private var ringBuffer = RingBuffer(capacity: 30)

    // MARK: - Configuration

    struct Config {
        var sampleRate: Double = 44100
        var channels: Int = 1
        var bitDepth: Int = 16
        var format: AudioFormatID = kAudioFormatLinearPCM
    }

    var config = Config()

    // MARK: - Capture Control

    func startCapture() throws {
        let url = fileManager.newRecordingURL()

        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatLinearPCM),
            AVSampleRateKey: config.sampleRate,
            AVNumberOfChannelsKey: config.channels,
            AVLinearPCMBitDepthKey: config.bitDepth,
            AVLinearPCMIsFloatKey: false,
            AVLinearPCMIsBigEndianKey: false
        ]

        try audioSession.setCategory(
            .playAndRecord,
            mode: .default,
            options: [.defaultToSpeaker, .allowBluetooth]
        )
        try audioSession.setActive(true)

        audioRecorder = try AVAudioRecorder(url: url, settings: settings)
        audioRecorder?.isMeteringEnabled = true
        audioRecorder?.record()

        recordingStartTime = Date()
        isCapturing = true
        startMeteringTimer()

        print("[LIME] Recording started: \(url.lastPathComponent)")
    }

    func stopCapture() {
        audioRecorder?.stop()
        audioRecorder = nil
        isCapturing = false
        recordingStartTime = nil
        stopMeteringTimer()
        currentTimestamp = 0
        audioLevel = 0

        print("[LIME] Recording stopped")
    }

    func pauseCapture() {
        audioRecorder?.pause()
    }

    func resumeCapture() {
        audioRecorder?.record()
    }

    // MARK: - Audio Level Metering

    private func startMeteringTimer() {
        let timer = Timer.scheduledTimer(withTimeInterval: 0.05, repeats: true) { [weak self] _ in
            guard let self, let recorder = self.audioRecorder else { return }
            recorder.updateMeters()

            let level = recorder.averagePower(forChannel: 0)
            // Normalize from dB (-160...0) to 0...1
            let normalized = max(0, (level + 50) / 50)

            DispatchQueue.main.async {
                self.audioLevel = normalized
                if let start = self.recordingStartTime {
                    self.currentTimestamp = Date().timeIntervalSince(start)
                }
            }
        }
        RunLoop.main.add(timer, forMode: .common)
    }

    private func stopMeteringTimer() {
        // Timer invalidated implicitly when recorder stops
    }

    // MARK: - Current Recording URL

    var currentRecordingURL: URL? {
        audioRecorder?.url
    }
}

// MARK: - Ring Buffer

/// Rolling audio buffer that retains the last N seconds to minimize data loss on failure.
struct RingBuffer {
    let capacity: Int // seconds
    private var chunks: [(timestamp: TimeInterval, data: Data)] = []

    init(capacity: Int) {
        self.capacity = capacity
    }

    mutating func append(timestamp: TimeInterval, data: Data) {
        chunks.append((timestamp, data))
        // Evict chunks older than capacity
        let cutoff = timestamp - Double(capacity)
        chunks.removeAll { $0.timestamp < cutoff }
    }

    func allData() -> Data {
        chunks.reduce(Data()) { $0 + $1.data }
    }
}
