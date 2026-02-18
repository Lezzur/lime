import SwiftUI

/// Visual horizontal representation of the meeting across time.
/// Topic segments shown as blocks with labels, importance clusters visible.
struct TimelineView: View {
    let topics: [TopicSegment]
    @State private var selectedTopic: TopicSegment?

    var totalDuration: TimeInterval {
        topics.map(\.endTime).max() ?? 0
    }

    var body: some View {
        VStack(spacing: 0) {
            // Timeline bar
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 2) {
                    ForEach(topics) { topic in
                        TopicBlock(
                            topic: topic,
                            totalDuration: totalDuration,
                            isSelected: selectedTopic?.id == topic.id
                        )
                        .onTapGesture {
                            withAnimation(.spring(response: 0.3)) {
                                selectedTopic = selectedTopic?.id == topic.id ? nil : topic
                            }
                        }
                    }
                }
                .padding(.horizontal)
                .padding(.vertical, 20)
            }
            .frame(height: 100)

            Divider()

            // Selected topic detail
            if let topic = selectedTopic {
                TopicDetailPanel(topic: topic)
                    .transition(.move(edge: .bottom).combined(with: .opacity))
            } else {
                Spacer()
                Text("Tap a segment to view details")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Spacer()
            }
        }
    }
}

struct TopicBlock: View {
    let topic: TopicSegment
    let totalDuration: TimeInterval
    let isSelected: Bool

    private var widthFraction: CGFloat {
        guard totalDuration > 0 else { return 1 }
        return CGFloat((topic.endTime - topic.startTime) / totalDuration)
    }

    private var intensity: Double {
        // Higher confidence + more insights = more "heat"
        let insightCount = Double(topic.insights.count)
        return min(1.0, (topic.confidence + insightCount * 0.1) / 2)
    }

    var body: some View {
        VStack(spacing: 4) {
            RoundedRectangle(cornerRadius: 6)
                .fill(
                    LinearGradient(
                        colors: [
                            Color.green.opacity(0.3 + intensity * 0.5),
                            Color.green.opacity(0.1 + intensity * 0.3)
                        ],
                        startPoint: .top,
                        endPoint: .bottom
                    )
                )
                .frame(
                    width: max(50, widthFraction * UIScreen.main.bounds.width * 0.8),
                    height: isSelected ? 50 : 40
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 6)
                        .stroke(isSelected ? Color.green : Color.clear, lineWidth: 2)
                )

            Text(topic.label)
                .font(.caption2)
                .lineLimit(1)
                .foregroundStyle(isSelected ? .primary : .secondary)
        }
    }
}

struct TopicDetailPanel: View {
    let topic: TopicSegment

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                // Header
                VStack(alignment: .leading, spacing: 4) {
                    Text(topic.label)
                        .font(.headline)
                    HStack {
                        Text(formatRange(topic.startTime, topic.endTime))
                            .font(.caption.monospacedDigit())
                            .foregroundStyle(.secondary)
                        if topic.confidence < 0.7 {
                            ConfidenceBadge(confidence: topic.confidence)
                        }
                    }
                }

                // Summary
                Text(topic.summary)
                    .font(.subheadline)

                // Insights
                if !topic.insights.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Insights")
                            .font(.subheadline.weight(.semibold))

                        ForEach(topic.insights) { insight in
                            HStack(alignment: .top, spacing: 8) {
                                Image(systemName: insightIcon(insight.type))
                                    .foregroundStyle(insightColor(insight.type))
                                    .font(.caption)
                                VStack(alignment: .leading) {
                                    Text(insight.content)
                                        .font(.caption)
                                    if insight.confidence < 0.7 {
                                        ConfidenceBadge(confidence: insight.confidence)
                                    }
                                }
                            }
                        }
                    }
                }
            }
            .padding()
        }
    }

    private func formatRange(_ start: TimeInterval, _ end: TimeInterval) -> String {
        "\(formatTime(start)) - \(formatTime(end))"
    }

    private func formatTime(_ interval: TimeInterval) -> String {
        let m = Int(interval) / 60
        let s = Int(interval) % 60
        return String(format: "%d:%02d", m, s)
    }

    private func insightIcon(_ type: InsightType) -> String {
        switch type {
        case .connection: return "link"
        case .contradiction: return "exclamationmark.triangle"
        case .implication: return "arrow.right.circle"
        case .pattern: return "repeat"
        case .suggestion: return "lightbulb"
        }
    }

    private func insightColor(_ type: InsightType) -> Color {
        switch type {
        case .connection: return .purple
        case .contradiction: return .red
        case .implication: return .blue
        case .pattern: return .cyan
        case .suggestion: return .yellow
        }
    }
}
