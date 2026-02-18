import UserNotifications

/// Push notification handling for processed meetings and sync events.
final class NotificationService {

    static let shared = NotificationService()
    private init() {}

    // MARK: - Local Notifications

    /// Notify user that a meeting has been processed.
    func notifyMeetingProcessed(
        meetingID: String,
        actionItemCount: Int,
        captureCount: Int,
        connectionSummary: String?
    ) {
        let content = UNMutableNotificationContent()
        content.title = "Meeting Processed"

        var body = "\(actionItemCount) action item\(actionItemCount == 1 ? "" : "s")"
        if captureCount > 0 {
            body += ", \(captureCount) capture\(captureCount == 1 ? "" : "s")"
        }
        if let connection = connectionSummary {
            body += ", \(connection)"
        }
        body += ". Ready when you are."

        content.body = body
        content.sound = .default
        content.userInfo = ["meetingID": meetingID]

        let request = UNNotificationRequest(
            identifier: "meeting-\(meetingID)",
            content: content,
            trigger: nil // Deliver immediately
        )

        UNUserNotificationCenter.current().add(request) { error in
            if let error {
                print("[LIME] Notification failed: \(error)")
            }
        }
    }

    /// Notify user of a processing error with their audio safe.
    func notifyProcessingError(meetingID: String) {
        let content = UNMutableNotificationContent()
        content.title = "Processing Issue"
        content.body = "Processing encountered an issue. Retrying. Your audio is safe."
        content.sound = .default
        content.userInfo = ["meetingID": meetingID]

        let request = UNNotificationRequest(
            identifier: "error-\(meetingID)",
            content: content,
            trigger: nil
        )

        UNUserNotificationCenter.current().add(request)
    }

    /// Notify user of a voice memo processed.
    func notifyVoiceMemoProcessed(memoID: String) {
        let content = UNMutableNotificationContent()
        content.title = "Voice Memo Ready"
        content.body = "Your voice memo has been transcribed and structured."
        content.sound = .default
        content.userInfo = ["memoID": memoID]

        let request = UNNotificationRequest(
            identifier: "memo-\(memoID)",
            content: content,
            trigger: nil
        )

        UNUserNotificationCenter.current().add(request)
    }
}
