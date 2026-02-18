import Speech
import AVFoundation
import Combine

/// Listens for the user's configured wake word to trigger commands.
/// Uses on-device speech recognition to avoid sending audio to the cloud.
final class WakeWordDetector: ObservableObject {

    @Published var isListening = false
    @Published var lastDetectedCommand: String?

    private let speechRecognizer: SFSpeechRecognizer
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?
    private let audioEngine = AVAudioEngine()

    var wakeWord: String = "Hey Lime"
    var onCommand: ((String) -> Void)?

    init(locale: Locale = .current) {
        self.speechRecognizer = SFSpeechRecognizer(locale: locale) ?? SFSpeechRecognizer()!
    }

    // MARK: - Authorization

    static func requestPermission() async -> Bool {
        await withCheckedContinuation { continuation in
            SFSpeechRecognizer.requestAuthorization { status in
                continuation.resume(returning: status == .authorized)
            }
        }
    }

    // MARK: - Detection

    func startListening() throws {
        guard speechRecognizer.isAvailable else {
            print("[LIME] Speech recognizer not available")
            return
        }

        stopListening()

        let request = SFSpeechAudioBufferRecognitionRequest()
        request.shouldReportPartialResults = true
        request.requiresOnDeviceRecognition = true // Privacy: stay on-device

        let inputNode = audioEngine.inputNode
        let format = inputNode.outputFormat(forBus: 0)

        inputNode.installTap(onBus: 0, bufferSize: 1024, format: format) { [weak self] buffer, _ in
            self?.recognitionRequest?.append(buffer)
        }

        recognitionTask = speechRecognizer.recognitionTask(with: request) { [weak self] result, error in
            guard let self else { return }

            if let result {
                let text = result.bestTranscription.formattedString.lowercased()
                let wake = self.wakeWord.lowercased()

                if text.contains(wake) {
                    // Extract command after the wake word
                    if let range = text.range(of: wake) {
                        let command = String(text[range.upperBound...]).trimmingCharacters(in: .whitespaces)
                        if !command.isEmpty {
                            DispatchQueue.main.async {
                                self.lastDetectedCommand = command
                                self.onCommand?(command)
                            }
                        }
                    }
                }
            }

            if error != nil || (result?.isFinal ?? false) {
                // Restart recognition to keep listening
                self.restartListening()
            }
        }

        self.recognitionRequest = request
        audioEngine.prepare()
        try audioEngine.start()
        isListening = true

        print("[LIME] Wake word detection started for: \(wakeWord)")
    }

    func stopListening() {
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        recognitionRequest?.endAudio()
        recognitionTask?.cancel()
        recognitionRequest = nil
        recognitionTask = nil
        isListening = false
    }

    private func restartListening() {
        stopListening()
        try? startListening()
    }
}
