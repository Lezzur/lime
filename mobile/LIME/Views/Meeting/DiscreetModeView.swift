import SwiftUI

/// Completely black screen for discreet recording during meetings.
/// Tap acknowledgment: small faint light under finger, fades out over 0.3 seconds.
/// Gestures: single tap (bookmark), double tap (priority), long press (voice capture).
struct DiscreetModeView: View {
    @EnvironmentObject var appState: AppState
    @State private var showVoiceAnnotation = false

    var body: some View {
        ZStack {
            // Pure black — no status bar, no indicators
            Color.black
                .ignoresSafeArea()

            // Gesture capture layer with faint light feedback
            CaptureGestureLayer { event in
                handleGesture(event)
            }

            // Voice annotation overlay (appears on long press)
            if showVoiceAnnotation {
                VoiceAnnotationOverlay(
                    isPresented: $showVoiceAnnotation,
                    meetingID: appState.currentMeetingID
                )
            }
        }
        .statusBarHidden(true)
        .persistentSystemOverlays(.hidden)
    }

    private func handleGesture(_ event: GestureEvent) {
        switch event.kind {
        case .singleTap:
            appState.addBookmark()

        case .doubleTap:
            appState.addPriorityFlag()

        case .longPress:
            appState.hapticEngine.playLongPress()
            showVoiceAnnotation = true
        }
    }
}

/// Overlay for recording voice annotations during a meeting.
/// Listens to user's voice specifically for a personal annotation,
/// captured separately from the meeting transcript.
struct VoiceAnnotationOverlay: View {
    @Binding var isPresented: Bool
    let meetingID: String?
    @StateObject private var capture = VoiceMemoCapture()

    var body: some View {
        VStack {
            Spacer()

            // Minimal indicator — just a small red dot to confirm recording
            Circle()
                .fill(Color.red.opacity(0.6))
                .frame(width: 12, height: 12)
                .scaleEffect(capture.isRecording ? 1.0 : 0.5)
                .animation(.easeInOut(duration: 0.8).repeatForever(), value: capture.isRecording)

            Spacer()
                .frame(height: 40)
        }
        .background(Color.black.opacity(0.95))
        .ignoresSafeArea()
        .onAppear {
            try? capture.startRecording()
            capture.onComplete = { _ in
                isPresented = false
            }
        }
        .onTapGesture {
            capture.stopRecording()
            isPresented = false
        }
    }
}
