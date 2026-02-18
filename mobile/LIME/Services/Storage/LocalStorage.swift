import Foundation

/// Lightweight local persistence for offline queue and cached data.
/// Meetings and memos are synced from the backend; this stores pending uploads and cache.
final class LocalStorage {

    private let defaults = UserDefaults.standard
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    // MARK: - Offline Queue

    /// Audio files waiting to be uploaded to the backend when connectivity returns.
    func enqueuePendingUpload(_ item: PendingUpload) {
        var queue = pendingUploads()
        queue.append(item)
        save(queue, forKey: "pendingUploads")
    }

    func pendingUploads() -> [PendingUpload] {
        load(forKey: "pendingUploads") ?? []
    }

    func removePendingUpload(id: String) {
        var queue = pendingUploads()
        queue.removeAll { $0.id == id }
        save(queue, forKey: "pendingUploads")
    }

    // MARK: - Cached Meetings (for offline viewing)

    func cacheMeetings(_ meetings: [Meeting]) {
        save(meetings, forKey: "cachedMeetings")
    }

    func cachedMeetings() -> [Meeting] {
        load(forKey: "cachedMeetings") ?? []
    }

    // MARK: - Last Sync Timestamp

    var lastSyncDate: Date? {
        get { defaults.object(forKey: "lastSyncDate") as? Date }
        set { defaults.set(newValue, forKey: "lastSyncDate") }
    }

    // MARK: - Generic

    private func save<T: Encodable>(_ value: T, forKey key: String) {
        if let data = try? encoder.encode(value) {
            defaults.set(data, forKey: key)
        }
    }

    private func load<T: Decodable>(forKey key: String) -> T? {
        guard let data = defaults.data(forKey: key) else { return nil }
        return try? decoder.decode(T.self, from: data)
    }
}

struct PendingUpload: Codable, Identifiable {
    let id: String
    let type: UploadType
    let fileURL: String
    let createdAt: Date
    let agentMode: String

    enum UploadType: String, Codable {
        case meetingAudio
        case voiceMemo
    }
}
