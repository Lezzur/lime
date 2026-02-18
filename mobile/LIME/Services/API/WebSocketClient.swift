import Foundation
import Combine

/// WebSocket client for real-time transcription stream and active mode intelligence alerts.
final class WebSocketClient: ObservableObject {

    @Published var isConnected = false

    private var webSocketTask: URLWebSocketTask?
    private let session = URLSession.shared
    private let baseURL: URL

    var onTranscriptSegment: ((TranscriptSegment) -> Void)?
    var onIntelligenceAlert: ((IntelligenceAlert) -> Void)?

    init(baseURL: URL = URL(string: "ws://localhost:8000")!) {
        self.baseURL = baseURL
    }

    // MARK: - Live Transcription Stream

    func connectToLiveTranscript(meetingID: String) {
        let url = baseURL.appendingPathComponent("/ws/live/\(meetingID)")
        connect(to: url) { [weak self] message in
            if let segment = try? JSONDecoder.lime.decode(TranscriptSegment.self, from: message) {
                self?.onTranscriptSegment?(segment)
            }
        }
    }

    // MARK: - Active Mode Intelligence

    func connectToActiveMode(meetingID: String) {
        let url = baseURL.appendingPathComponent("/ws/active-mode/\(meetingID)")
        connect(to: url) { [weak self] message in
            if let alert = try? JSONDecoder.lime.decode(IntelligenceAlert.self, from: message) {
                self?.onIntelligenceAlert?(alert)
            }
        }
    }

    // MARK: - Connection

    func disconnect() {
        webSocketTask?.cancel(with: .goingAway, reason: nil)
        webSocketTask = nil
        isConnected = false
    }

    private func connect(to url: URL, handler: @escaping (Data) -> Void) {
        disconnect()

        webSocketTask = session.webSocketTask(with: url)
        webSocketTask?.resume()
        isConnected = true

        receiveLoop(handler: handler)
    }

    private func receiveLoop(handler: @escaping (Data) -> Void) {
        webSocketTask?.receive { [weak self] result in
            switch result {
            case .success(let message):
                switch message {
                case .data(let data):
                    handler(data)
                case .string(let text):
                    if let data = text.data(using: .utf8) {
                        handler(data)
                    }
                @unknown default:
                    break
                }
                // Continue listening
                self?.receiveLoop(handler: handler)

            case .failure(let error):
                print("[LIME] WebSocket error: \(error)")
                self?.isConnected = false
                // Auto-reconnect after 3 seconds
                DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
                    self?.webSocketTask?.resume()
                    self?.receiveLoop(handler: handler)
                }
            }
        }
    }
}

// MARK: - WebSocket Message Types

struct TranscriptSegment: Decodable {
    let text: String
    let speaker: String?
    let startTime: TimeInterval
    let endTime: TimeInterval
    let confidence: Double
    let language: String?
}

struct IntelligenceAlert: Identifiable, Decodable {
    let id: String
    let urgency: AlertUrgency
    let title: String
    let detail: String
    let type: InsightType
    let confidence: Double
}

enum AlertUrgency: String, Decodable {
    case low
    case medium
    case high
    case critical
}
