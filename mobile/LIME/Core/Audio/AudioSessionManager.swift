import AVFoundation

/// Manages AVAudioSession configuration and interruption handling.
/// Ensures recording continues in background and survives interruptions.
final class AudioSessionManager {

    static let shared = AudioSessionManager()
    private let session = AVAudioSession.sharedInstance()

    private init() {
        observeInterruptions()
        observeRouteChanges()
    }

    // MARK: - Configuration

    func configureForRecording() throws {
        try session.setCategory(
            .playAndRecord,
            mode: .default,
            options: [
                .defaultToSpeaker,
                .allowBluetooth,
                .mixWithOthers
            ]
        )
        try session.setActive(true, options: .notifyOthersOnDeactivation)
    }

    func deactivate() {
        try? session.setActive(false, options: .notifyOthersOnDeactivation)
    }

    var currentInputDevice: String {
        session.currentRoute.inputs.first?.portName ?? "Unknown"
    }

    var availableInputs: [AVAudioSessionPortDescription] {
        session.availableInputs ?? []
    }

    func selectInput(_ port: AVAudioSessionPortDescription) throws {
        try session.setPreferredInput(port)
    }

    // MARK: - Interruption Handling

    private func observeInterruptions() {
        NotificationCenter.default.addObserver(
            forName: AVAudioSession.interruptionNotification,
            object: session,
            queue: .main
        ) { [weak self] notification in
            self?.handleInterruption(notification)
        }
    }

    private func handleInterruption(_ notification: Notification) {
        guard let info = notification.userInfo,
              let typeValue = info[AVAudioSessionInterruptionTypeKey] as? UInt,
              let type = AVAudioSession.InterruptionType(rawValue: typeValue) else {
            return
        }

        switch type {
        case .began:
            print("[LIME] Audio session interrupted")
        case .ended:
            let optionsValue = info[AVAudioSessionInterruptionOptionKey] as? UInt ?? 0
            let options = AVAudioSession.InterruptionOptions(rawValue: optionsValue)
            if options.contains(.shouldResume) {
                try? session.setActive(true)
                print("[LIME] Audio session resumed after interruption")
            }
        @unknown default:
            break
        }
    }

    // MARK: - Route Changes (headphones, bluetooth, etc.)

    private func observeRouteChanges() {
        NotificationCenter.default.addObserver(
            forName: AVAudioSession.routeChangeNotification,
            object: session,
            queue: .main
        ) { notification in
            guard let info = notification.userInfo,
                  let reasonValue = info[AVAudioSessionRouteChangeReasonKey] as? UInt,
                  let reason = AVAudioSession.RouteChangeReason(rawValue: reasonValue) else {
                return
            }
            print("[LIME] Audio route changed: \(reason.rawValue)")
        }
    }
}
