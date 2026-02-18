import SwiftUI

/// Active recording mode with breathing dot that escalates based on urgency.
/// Agent surfaces real-time intelligence: contradictions, connections, references.
struct ActiveModeView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var wsClient = WebSocketClient()
    @State private var alerts: [IntelligenceAlert] = []
    @State private var showAlerts = false
    @State private var currentUrgency: AlertUrgency = .low
    @State private var showVoiceAnnotation = false

    var body: some View {
        ZStack {
            Color.black
                .ignoresSafeArea()

            // Gesture capture layer
            CaptureGestureLayer { event in
                handleGesture(event)
            }

            // Breathing dot — the primary UI element
            VStack {
                Spacer()

                BreathingDotView(urgency: currentUrgency)
                    .onTapGesture {
                        withAnimation(.spring(response: 0.3)) {
                            showAlerts.toggle()
                        }
                    }

                Spacer()

                // Recording duration
                if appState.isRecording {
                    Text(formatDuration(appState.recordingDuration))
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(.white.opacity(0.3))
                        .padding(.bottom, 40)
                }
            }

            // Intelligence alerts panel (swipe up or tap dot)
            if showAlerts {
                AlertsPanel(alerts: alerts) {
                    withAnimation {
                        showAlerts = false
                    }
                }
            }

            // Voice annotation overlay
            if showVoiceAnnotation {
                VoiceAnnotationOverlay(
                    isPresented: $showVoiceAnnotation,
                    meetingID: appState.currentMeetingID
                )
            }
        }
        .statusBarHidden(true)
        .persistentSystemOverlays(.hidden)
        .onAppear { connectWebSocket() }
        .onDisappear { wsClient.disconnect() }
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

    private func connectWebSocket() {
        guard let meetingID = appState.currentMeetingID else { return }

        wsClient.onIntelligenceAlert = { alert in
            DispatchQueue.main.async {
                alerts.insert(alert, at: 0)
                currentUrgency = alert.urgency

                // Haptic buzz for high/critical urgency
                if alert.urgency == .high || alert.urgency == .critical {
                    appState.hapticEngine.playUrgentAlert()
                }
            }
        }

        wsClient.connectToActiveMode(meetingID: meetingID)
    }

    private func formatDuration(_ interval: TimeInterval) -> String {
        let minutes = Int(interval) / 60
        let seconds = Int(interval) % 60
        return String(format: "%d:%02d", minutes, seconds)
    }
}

// MARK: - Alerts Panel

struct AlertsPanel: View {
    let alerts: [IntelligenceAlert]
    let onDismiss: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            // Drag handle
            Capsule()
                .fill(Color.white.opacity(0.3))
                .frame(width: 40, height: 4)
                .padding(.top, 12)
                .padding(.bottom, 8)

            ScrollView {
                LazyVStack(spacing: 12) {
                    ForEach(alerts) { alert in
                        AlertCard(alert: alert)
                    }
                }
                .padding(.horizontal, 16)
                .padding(.bottom, 20)
            }
        }
        .frame(maxHeight: UIScreen.main.bounds.height * 0.4)
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 20))
        .frame(maxHeight: .infinity, alignment: .bottom)
        .ignoresSafeArea(edges: .bottom)
        .onTapGesture { /* prevent pass-through */ }
        .gesture(
            DragGesture()
                .onEnded { value in
                    if value.translation.height > 50 { onDismiss() }
                }
        )
    }
}

struct AlertCard: View {
    let alert: IntelligenceAlert

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Circle()
                    .fill(urgencyColor)
                    .frame(width: 8, height: 8)
                Text(alert.title)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.white)
                Spacer()
                if alert.confidence < 0.7 {
                    ConfidenceBadge(confidence: alert.confidence)
                }
            }
            Text(alert.detail)
                .font(.caption)
                .foregroundStyle(.white.opacity(0.7))
                .lineLimit(3)
        }
        .padding(12)
        .background(Color.white.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private var urgencyColor: Color {
        switch alert.urgency {
        case .low: return .gray
        case .medium: return .yellow
        case .high: return .orange
        case .critical: return .red
        }
    }
}
