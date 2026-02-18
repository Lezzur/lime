import Foundation

struct Meeting: Identifiable, Codable {
    let id: String
    var title: String?
    var participants: [String]
    var startedAt: Date
    var endedAt: Date?
    var duration: TimeInterval?
    var audioFileURL: String?
    var status: MeetingStatus
    var captureMode: String // "discreet" | "active"
    var agentMode: String   // "scribe" | "thinkingPartner" | "sparringPartner"

    // Post-processing results
    var summary: ExecutiveSummary?
    var actionItems: [ActionItem]
    var topics: [TopicSegment]
    var bookmarks: [Bookmark]
    var connections: [Connection]
}

enum MeetingStatus: String, Codable {
    case recording
    case processing
    case ready
    case failed
}

struct ExecutiveSummary: Codable {
    let overview: String
    let outcome: String
    let keyDecisions: [String]
    let unresolvedQuestions: [String]
}

struct ActionItem: Identifiable, Codable {
    let id: String
    let description: String
    var owner: String?
    var deadline: String?
    var completed: Bool
    let timestamp: TimeInterval?
}

struct TopicSegment: Identifiable, Codable {
    let id: String
    let label: String
    let startTime: TimeInterval
    let endTime: TimeInterval
    let summary: String
    let confidence: Double
    var insights: [Insight]
}

struct Insight: Identifiable, Codable {
    let id: String
    let content: String
    let type: InsightType
    let confidence: Double
    let relatedMeetingIDs: [String]
}

enum InsightType: String, Codable {
    case connection
    case contradiction
    case implication
    case pattern
    case suggestion
}

struct Bookmark: Identifiable, Codable {
    let id: String
    let timestamp: TimeInterval
    let priority: BookmarkPriority
    var annotation: String?
    var audioAnnotationURL: String?
}

enum BookmarkPriority: String, Codable {
    case normal
    case high
}

struct Connection: Identifiable, Codable {
    let id: String
    let relatedMeetingID: String
    let description: String
    let confidence: Double
}

struct Speaker: Identifiable, Codable {
    let id: String
    var name: String
    var voiceProfileID: String?
    var role: String?
    var team: String?
}
