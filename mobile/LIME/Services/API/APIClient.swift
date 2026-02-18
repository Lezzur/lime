import Foundation

/// HTTP + WebSocket client for communicating with the LIME backend.
final class APIClient {

    private let baseURL: URL
    private let session: URLSession
    private var authToken: String?

    init(baseURL: URL = URL(string: "http://localhost:8000")!) {
        self.baseURL = baseURL
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        self.session = URLSession(configuration: config)
    }

    // MARK: - Auth

    func setAuthToken(_ token: String) {
        self.authToken = token
    }

    // MARK: - Meetings

    func startMeeting() async throws -> String {
        let response: StartMeetingResponse = try await post("/api/meetings/start", body: [:])
        return response.meetingID
    }

    func stopMeeting(id: String) async throws {
        let _: EmptyResponse = try await post("/api/meetings/\(id)/stop", body: [:])
    }

    func getMeeting(id: String) async throws -> Meeting {
        try await get("/api/meetings/\(id)")
    }

    func listMeetings(limit: Int = 20, offset: Int = 0) async throws -> [Meeting] {
        try await get("/api/meetings?limit=\(limit)&offset=\(offset)")
    }

    func getNotes(meetingID: String) async throws -> MeetingNotes {
        try await get("/api/meetings/\(meetingID)/notes")
    }

    func addBookmark(meetingID: String, timestamp: TimeInterval, priority: BookmarkPriority) async throws {
        let body: [String: Any] = [
            "timestamp": timestamp,
            "priority": priority.rawValue
        ]
        let _: EmptyResponse = try await post("/api/meetings/\(meetingID)/bookmarks", body: body)
    }

    func getBriefing(meetingID: String) async throws -> Briefing {
        try await post("/api/meetings/\(meetingID)/briefing", body: [:])
    }

    // MARK: - Voice Memos

    func uploadVoiceMemo(audioData: Data, agentMode: String) async throws -> String {
        let url = baseURL.appendingPathComponent("/api/voice-memo")
        var request = makeRequest(url: url, method: "POST")
        request.setValue("audio/wav", forHTTPHeaderField: "Content-Type")
        request.setValue(agentMode, forHTTPHeaderField: "X-Agent-Mode")

        let (data, response) = try await session.upload(for: request, from: audioData)
        try validateResponse(response)

        let decoded = try JSONDecoder().decode(VoiceMemoUploadResponse.self, from: data)
        return decoded.memoID
    }

    func listVoiceMemos() async throws -> [VoiceMemo] {
        try await get("/api/voice-memos")
    }

    // MARK: - Search

    func search(query: String) async throws -> SearchResults {
        let encoded = query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? query
        return try await get("/api/search?q=\(encoded)")
    }

    // MARK: - Sync

    func triggerSync() async throws {
        let _: EmptyResponse = try await post("/api/sync", body: [:])
    }

    // MARK: - Audio Upload

    func uploadAudio(meetingID: String, fileURL: URL) async throws {
        let url = baseURL.appendingPathComponent("/api/meetings/\(meetingID)/audio")
        var request = makeRequest(url: url, method: "POST")
        request.setValue("application/octet-stream", forHTTPHeaderField: "Content-Type")

        let data = try Data(contentsOf: fileURL)
        let (_, response) = try await session.upload(for: request, from: data)
        try validateResponse(response)
    }

    // MARK: - Generic HTTP

    private func get<T: Decodable>(_ path: String) async throws -> T {
        let url = baseURL.appendingPathComponent(path)
        let request = makeRequest(url: url, method: "GET")
        let (data, response) = try await session.data(for: request)
        try validateResponse(response)
        return try JSONDecoder.lime.decode(T.self, from: data)
    }

    private func post<T: Decodable>(_ path: String, body: [String: Any]) async throws -> T {
        let url = baseURL.appendingPathComponent(path)
        var request = makeRequest(url: url, method: "POST")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await session.data(for: request)
        try validateResponse(response)
        return try JSONDecoder.lime.decode(T.self, from: data)
    }

    private func makeRequest(url: URL, method: String) -> URLRequest {
        var request = URLRequest(url: url)
        request.httpMethod = method
        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        return request
    }

    private func validateResponse(_ response: URLResponse) throws {
        guard let http = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200...299).contains(http.statusCode) else {
            throw APIError.httpError(statusCode: http.statusCode)
        }
    }
}

// MARK: - Response Types

struct StartMeetingResponse: Decodable { let meetingID: String }
struct VoiceMemoUploadResponse: Decodable { let memoID: String }
struct EmptyResponse: Decodable {}

struct MeetingNotes: Decodable {
    let summary: ExecutiveSummary
    let actionItems: [ActionItem]
    let topics: [TopicSegment]
}

struct Briefing: Decodable {
    let context: String
    let openThreads: [String]
    let suggestedFollowUps: [String]
}

struct SearchResults: Decodable {
    let results: [SearchResult]
}

struct SearchResult: Identifiable, Decodable {
    let id: String
    let type: String // "meeting" | "voice_memo"
    let title: String
    let excerpt: String
    let timestamp: Date
}

// MARK: - Errors

enum APIError: LocalizedError {
    case invalidResponse
    case httpError(statusCode: Int)

    var errorDescription: String? {
        switch self {
        case .invalidResponse: return "Invalid server response"
        case .httpError(let code): return "HTTP error: \(code)"
        }
    }
}

// MARK: - JSON Decoder

extension JSONDecoder {
    static let lime: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }()
}
