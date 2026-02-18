import Foundation
import Combine
import Network

/// Bidirectional sync engine: phone <-> backend <-> desktop/cloud.
/// Handles offline queue, connectivity monitoring, and conflict resolution.
final class SyncEngine: ObservableObject {

    @Published var isSyncing = false
    @Published var isOnline = true
    @Published var lastSyncDate: Date?

    private let apiClient: APIClient
    private let localStorage = LocalStorage()
    private let monitor = NWPathMonitor()
    private let monitorQueue = DispatchQueue(label: "com.lime.network-monitor")

    init(apiClient: APIClient) {
        self.apiClient = apiClient
        self.lastSyncDate = localStorage.lastSyncDate
        startNetworkMonitoring()
    }

    deinit {
        monitor.cancel()
    }

    // MARK: - Network Monitoring

    private func startNetworkMonitoring() {
        monitor.pathUpdateHandler = { [weak self] path in
            DispatchQueue.main.async {
                let wasOffline = !(self?.isOnline ?? true)
                self?.isOnline = path.status == .satisfied

                // Came back online — flush pending uploads
                if wasOffline && path.status == .satisfied {
                    Task { await self?.flushPendingUploads() }
                }
            }
        }
        monitor.start(queue: monitorQueue)
    }

    // MARK: - Sync

    func sync() async {
        guard isOnline, !isSyncing else { return }

        await MainActor.run { isSyncing = true }
        defer { Task { @MainActor in isSyncing = false } }

        do {
            // Upload pending audio files
            await flushPendingUploads()

            // Trigger server-side sync
            try await apiClient.triggerSync()

            // Cache latest meetings locally for offline viewing
            let meetings = try await apiClient.listMeetings()
            localStorage.cacheMeetings(meetings)

            let now = Date()
            localStorage.lastSyncDate = now
            await MainActor.run { lastSyncDate = now }

            print("[LIME] Sync completed successfully")
        } catch {
            print("[LIME] Sync failed: \(error)")
        }
    }

    // MARK: - Offline Queue

    func enqueuePendingUpload(type: PendingUpload.UploadType, fileURL: URL, agentMode: String) {
        let item = PendingUpload(
            id: UUID().uuidString,
            type: type,
            fileURL: fileURL.absoluteString,
            createdAt: Date(),
            agentMode: agentMode
        )
        localStorage.enqueuePendingUpload(item)

        if isOnline {
            Task { await flushPendingUploads() }
        }
    }

    private func flushPendingUploads() async {
        let pending = localStorage.pendingUploads()
        guard !pending.isEmpty else { return }

        print("[LIME] Flushing \(pending.count) pending uploads")

        for item in pending {
            do {
                guard let url = URL(string: item.fileURL) else { continue }
                let data = try Data(contentsOf: url)

                switch item.type {
                case .meetingAudio:
                    try await apiClient.uploadAudio(meetingID: item.id, fileURL: url)
                case .voiceMemo:
                    _ = try await apiClient.uploadVoiceMemo(audioData: data, agentMode: item.agentMode)
                }

                localStorage.removePendingUpload(id: item.id)
            } catch {
                print("[LIME] Failed to upload \(item.id): \(error)")
                // Keep in queue for retry
            }
        }
    }
}
