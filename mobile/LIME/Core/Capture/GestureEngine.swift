import SwiftUI

/// Handles single tap, double tap, and long press gestures on the capture screen.
/// Reports gesture events along with their screen position for visual feedback.
struct GestureEvent {
    enum Kind {
        case singleTap   // Bookmark
        case doubleTap   // Priority flag
        case longPress   // Voice annotation
    }

    let kind: Kind
    let location: CGPoint
    let timestamp: Date
}

/// A transparent view that captures all three gesture types used during recording.
/// Overlaid on both discreet and active mode screens.
struct CaptureGestureLayer: View {
    let onGesture: (GestureEvent) -> Void

    @State private var tapLocation: CGPoint = .zero
    @State private var showFeedback = false

    var body: some View {
        GeometryReader { geometry in
            Color.clear
                .contentShape(Rectangle())
                .simultaneousGesture(doubleTapGesture(in: geometry))
                .simultaneousGesture(longPressGesture(in: geometry))
                .simultaneousGesture(singleTapGesture(in: geometry))
                .overlay {
                    if showFeedback {
                        TapFeedbackView(position: tapLocation)
                    }
                }
        }
    }

    // MARK: - Gestures

    private func singleTapGesture(in geometry: GeometryProxy) -> some Gesture {
        SpatialTapGesture(count: 1)
            .onEnded { value in
                let location = value.location
                emitGesture(.singleTap, at: location)
            }
    }

    private func doubleTapGesture(in geometry: GeometryProxy) -> some Gesture {
        SpatialTapGesture(count: 2)
            .onEnded { value in
                let location = value.location
                emitGesture(.doubleTap, at: location)
            }
    }

    private func longPressGesture(in geometry: GeometryProxy) -> some Gesture {
        LongPressGesture(minimumDuration: 0.5)
            .onEnded { _ in
                emitGesture(.longPress, at: tapLocation)
            }
    }

    // MARK: - Feedback

    private func emitGesture(_ kind: GestureEvent.Kind, at location: CGPoint) {
        let event = GestureEvent(kind: kind, location: location, timestamp: Date())
        tapLocation = location
        onGesture(event)

        // Show faint light feedback (0.3s fade per spec)
        withAnimation(.easeOut(duration: 0.05)) {
            showFeedback = true
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) {
            withAnimation(.easeOut(duration: 0.3)) {
                showFeedback = false
            }
        }
    }
}

/// Small faint light that appears under the finger and fades out over 0.3 seconds.
/// Per spec: Discreet mode tap acknowledgment.
struct TapFeedbackView: View {
    let position: CGPoint

    var body: some View {
        Circle()
            .fill(
                RadialGradient(
                    colors: [
                        Color.white.opacity(0.15),
                        Color.white.opacity(0)
                    ],
                    center: .center,
                    startRadius: 0,
                    endRadius: 40
                )
            )
            .frame(width: 80, height: 80)
            .position(position)
            .allowsHitTesting(false)
    }
}
