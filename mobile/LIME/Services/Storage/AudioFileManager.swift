import Foundation

/// Manages local audio file storage for recordings and voice memos.
final class AudioFileManager {

    private let fileManager = FileManager.default

    private var audioDirectory: URL {
        let docs = fileManager.urls(for: .documentDirectory, in: .userDomainMask).first!
        let dir = docs.appendingPathComponent("audio", isDirectory: true)
        try? fileManager.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir
    }

    private var memoDirectory: URL {
        let docs = fileManager.urls(for: .documentDirectory, in: .userDomainMask).first!
        let dir = docs.appendingPathComponent("memos", isDirectory: true)
        try? fileManager.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir
    }

    // MARK: - File Creation

    func newRecordingURL() -> URL {
        let filename = "meeting_\(timestamp()).wav"
        return audioDirectory.appendingPathComponent(filename)
    }

    func newVoiceMemoURL() -> URL {
        let filename = "memo_\(timestamp()).wav"
        return memoDirectory.appendingPathComponent(filename)
    }

    // MARK: - File Management

    func recordingURLs() -> [URL] {
        (try? fileManager.contentsOfDirectory(at: audioDirectory, includingPropertiesForKeys: [.creationDateKey]))
            ?? []
    }

    func memoURLs() -> [URL] {
        (try? fileManager.contentsOfDirectory(at: memoDirectory, includingPropertiesForKeys: [.creationDateKey]))
            ?? []
    }

    func deleteFile(at url: URL) throws {
        try fileManager.removeItem(at: url)
    }

    func fileSize(at url: URL) -> Int64 {
        let attrs = try? fileManager.attributesOfItem(atPath: url.path)
        return attrs?[.size] as? Int64 ?? 0
    }

    /// Total storage used by audio files in bytes.
    func totalStorageUsed() -> Int64 {
        let recordings = recordingURLs().reduce(Int64(0)) { $0 + fileSize(at: $1) }
        let memos = memoURLs().reduce(Int64(0)) { $0 + fileSize(at: $1) }
        return recordings + memos
    }

    // MARK: - Private

    private func timestamp() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyyMMdd_HHmmss"
        return formatter.string(from: Date())
    }
}
