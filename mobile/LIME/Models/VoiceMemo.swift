import Foundation

struct VoiceMemo: Identifiable, Codable {
    let id: String
    var createdAt: Date
    var duration: TimeInterval
    var audioFileURL: String
    var status: VoiceMemoStatus

    // Processing results
    var rawTranscript: String?
    var structuredNote: String?
    var agentResponse: String? // Varies by agent mode
    var agentMode: String      // Mode active when memo was captured
}

enum VoiceMemoStatus: String, Codable {
    case recorded       // Audio captured, not yet processed
    case queued         // Waiting for processing (offline)
    case processing     // Being transcribed + analyzed
    case ready          // Complete
    case failed         // Processing failed, audio preserved
}
