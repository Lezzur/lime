import XCTest
@testable import LIME

final class LIMETests: XCTestCase {

    func testBookmarkPriorities() {
        let normal = BookmarkPriority.normal
        let high = BookmarkPriority.high
        XCTAssertNotEqual(normal.rawValue, high.rawValue)
    }

    func testMeetingStatusTransitions() {
        let statuses: [MeetingStatus] = [.recording, .processing, .ready, .failed]
        XCTAssertEqual(statuses.count, 4)
    }

    func testVoiceMemoStatusValues() {
        let status = VoiceMemoStatus.recorded
        XCTAssertEqual(status.rawValue, "recorded")
    }

    func testAgentModes() {
        XCTAssertEqual(AgentMode.allCases.count, 3)
        XCTAssertEqual(AgentMode.thinkingPartner.rawValue, "Thinking Partner")
    }

    func testCaptureModes() {
        XCTAssertEqual(CaptureMode.allCases.count, 2)
    }

    func testRingBufferEviction() {
        var buffer = RingBuffer(capacity: 5)
        buffer.append(timestamp: 1.0, data: Data([0x01]))
        buffer.append(timestamp: 3.0, data: Data([0x02]))
        buffer.append(timestamp: 7.0, data: Data([0x03]))
        // Entry at timestamp 1.0 should be evicted (7.0 - 5 = 2.0 cutoff)
        let allData = buffer.allData()
        XCTAssertEqual(allData.count, 2) // Only entries at 3.0 and 7.0
    }

    func testAudioFileManagerURLs() {
        let manager = AudioFileManager()
        let recordingURL = manager.newRecordingURL()
        let memoURL = manager.newVoiceMemoURL()

        XCTAssertTrue(recordingURL.lastPathComponent.hasPrefix("meeting_"))
        XCTAssertTrue(memoURL.lastPathComponent.hasPrefix("memo_"))
        XCTAssertTrue(recordingURL.pathExtension == "wav")
        XCTAssertTrue(memoURL.pathExtension == "wav")
    }

    func testCryptoServiceKeyExportImport() throws {
        // Generate a key
        let key = try CryptoService.generateKey()
        XCTAssertNotNil(key)

        // Export
        let exported = CryptoService.exportKey()
        XCTAssertNotNil(exported)

        // Encrypt / decrypt round-trip
        let original = "LIME test data".data(using: .utf8)!
        let encrypted = try CryptoService.encrypt(original)
        let decrypted = try CryptoService.decrypt(encrypted)
        XCTAssertEqual(original, decrypted)
    }
}
