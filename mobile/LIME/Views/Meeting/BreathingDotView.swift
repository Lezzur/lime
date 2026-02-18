import SwiftUI

/// Animated breathing dot that serves as the primary UI element during active recording.
/// - Calm state: slow, rhythmic pulsing like a person breathing at rest
/// - Escalating: faster, more intense pulsing proportional to urgency
/// - Maximum: intense pulsing (haptic handled separately)
struct BreathingDotView: View {
    let urgency: AlertUrgency

    @State private var scale: CGFloat = 1.0
    @State private var glowOpacity: Double = 0.3

    private var dotColor: Color {
        switch urgency {
        case .low: return .green
        case .medium: return .yellow
        case .high: return .orange
        case .critical: return .red
        }
    }

    private var breathDuration: Double {
        switch urgency {
        case .low: return 4.0      // Calm breathing (~15 bpm)
        case .medium: return 2.5   // Slightly elevated
        case .high: return 1.5     // Noticeably faster
        case .critical: return 0.6 // Urgent pulsing
        }
    }

    private var scaleRange: CGFloat {
        switch urgency {
        case .low: return 0.15
        case .medium: return 0.2
        case .high: return 0.3
        case .critical: return 0.4
        }
    }

    private var dotSize: CGFloat {
        switch urgency {
        case .low: return 40
        case .medium: return 44
        case .high: return 48
        case .critical: return 52
        }
    }

    var body: some View {
        ZStack {
            // Outer glow
            Circle()
                .fill(dotColor.opacity(glowOpacity * 0.3))
                .frame(width: dotSize * 3, height: dotSize * 3)
                .scaleEffect(scale * 1.2)

            // Middle glow
            Circle()
                .fill(dotColor.opacity(glowOpacity * 0.5))
                .frame(width: dotSize * 1.8, height: dotSize * 1.8)
                .scaleEffect(scale * 1.1)

            // Core dot
            Circle()
                .fill(
                    RadialGradient(
                        colors: [dotColor, dotColor.opacity(0.7)],
                        center: .center,
                        startRadius: 0,
                        endRadius: dotSize / 2
                    )
                )
                .frame(width: dotSize, height: dotSize)
                .scaleEffect(scale)
        }
        .onAppear { startBreathing() }
        .onChange(of: urgency) { _, _ in startBreathing() }
    }

    private func startBreathing() {
        // Reset
        scale = 1.0
        glowOpacity = 0.3

        // Breathing animation: inhale → exhale cycle
        withAnimation(
            .easeInOut(duration: breathDuration)
            .repeatForever(autoreverses: true)
        ) {
            scale = 1.0 + scaleRange
            glowOpacity = 0.6 + Double(scaleRange)
        }
    }
}

// MARK: - Error State Variants

/// Red breathing dot shown when recording has a problem.
struct ErrorDotView: View {
    @State private var isFlashing = false

    var body: some View {
        Circle()
            .fill(Color.red)
            .frame(width: 40, height: 40)
            .opacity(isFlashing ? 1.0 : 0.3)
            .onAppear {
                withAnimation(.easeInOut(duration: 0.5).repeatForever()) {
                    isFlashing = true
                }
            }
    }
}

/// Amber flash shown briefly when connectivity is lost.
struct ConnectivityLostFlash: View {
    @State private var opacity: Double = 1.0

    var body: some View {
        Circle()
            .fill(Color.orange)
            .frame(width: 40, height: 40)
            .opacity(opacity)
            .onAppear {
                withAnimation(.easeOut(duration: 1.5)) {
                    opacity = 0
                }
            }
    }
}
