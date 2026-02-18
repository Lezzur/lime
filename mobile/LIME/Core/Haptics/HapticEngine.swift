import CoreHaptics
import UIKit

/// Custom haptic patterns for meeting capture gestures.
final class HapticEngine {

    private var engine: CHHapticEngine?

    init() {
        prepareEngine()
    }

    private func prepareEngine() {
        guard CHHapticEngine.capabilitiesForHardware().supportsHaptics else { return }
        do {
            engine = try CHHapticEngine()
            engine?.resetHandler = { [weak self] in
                try? self?.engine?.start()
            }
            try engine?.start()
        } catch {
            print("[LIME] Haptic engine failed to start: \(error)")
        }
    }

    // MARK: - Gesture Feedback

    /// Single tap bookmark — light, short tap
    func playTap() {
        let generator = UIImpactFeedbackGenerator(style: .light)
        generator.impactOccurred()
    }

    /// Double tap priority flag — two medium impacts
    func playDoubleTap() {
        let generator = UIImpactFeedbackGenerator(style: .medium)
        generator.impactOccurred()
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
            generator.impactOccurred()
        }
    }

    /// Long press voice capture — sustained heavy impact
    func playLongPress() {
        let generator = UIImpactFeedbackGenerator(style: .heavy)
        generator.impactOccurred()
    }

    /// Urgent alert from active mode — escalating pattern
    func playUrgentAlert() {
        guard let engine else {
            let generator = UINotificationFeedbackGenerator()
            generator.notificationOccurred(.warning)
            return
        }

        do {
            let sharpness = CHHapticEventParameter(parameterID: .hapticSharpness, value: 0.8)
            let intensity = CHHapticEventParameter(parameterID: .hapticIntensity, value: 1.0)

            let events = [
                CHHapticEvent(eventType: .hapticTransient, parameters: [sharpness, intensity],
                              relativeTime: 0),
                CHHapticEvent(eventType: .hapticTransient, parameters: [sharpness, intensity],
                              relativeTime: 0.15),
                CHHapticEvent(eventType: .hapticTransient, parameters: [sharpness, intensity],
                              relativeTime: 0.3),
            ]

            let pattern = try CHHapticPattern(events: events, parameters: [])
            let player = try engine.makePlayer(with: pattern)
            try player.start(atTime: CHHapticTimeImmediate)
        } catch {
            print("[LIME] Haptic pattern playback failed: \(error)")
        }
    }

    /// Recording started confirmation
    func playRecordingStarted() {
        let generator = UINotificationFeedbackGenerator()
        generator.notificationOccurred(.success)
    }

    /// Recording stopped confirmation
    func playRecordingStopped() {
        let generator = UINotificationFeedbackGenerator()
        generator.notificationOccurred(.warning)
    }
}
