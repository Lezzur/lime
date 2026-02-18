import SwiftUI

/// Full annotated transcript with speaker labels, topic markers, and intelligence overlays.
struct TranscriptView: View {
    let meetingID: String
    @State private var segments: [TranscriptSegment] = []
    @State private var expandedMarkerID: String?

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 0) {
                ForEach(Array(segments.enumerated()), id: \.offset) { index, segment in
                    TranscriptSegmentRow(
                        segment: segment,
                        isExpanded: expandedMarkerID == "\(index)",
                        onToggleMarker: {
                            withAnimation(.spring(response: 0.3)) {
                                expandedMarkerID = expandedMarkerID == "\(index)" ? nil : "\(index)"
                            }
                        }
                    )
                }
            }
            .padding()
        }
    }
}

struct TranscriptSegmentRow: View {
    let segment: TranscriptSegment
    let isExpanded: Bool
    let onToggleMarker: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(alignment: .top) {
                // Speaker label + timestamp
                VStack(alignment: .leading, spacing: 2) {
                    if let speaker = segment.speaker {
                        Text(speaker)
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.green)
                    }
                    Text(formatTime(segment.startTime))
                        .font(.caption2.monospacedDigit())
                        .foregroundStyle(.secondary)
                }
                .frame(width: 70, alignment: .leading)

                // Transcript text
                VStack(alignment: .leading, spacing: 4) {
                    Text(segment.text)
                        .font(.subheadline)

                    if segment.confidence < 0.7 {
                        ConfidenceBadge(confidence: segment.confidence)
                    }
                }

                Spacer()

                // Topic marker pin (like Google Maps marker)
                Button(action: onToggleMarker) {
                    Image(systemName: isExpanded ? "mappin.circle.fill" : "mappin.circle")
                        .foregroundStyle(isExpanded ? .green : .secondary)
                        .font(.body)
                }
            }

            // Expanded intelligence layer
            if isExpanded {
                MarkerIntelligenceView(segment: segment)
                    .padding(.leading, 70)
                    .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
        .padding(.vertical, 6)
    }

    private func formatTime(_ interval: TimeInterval) -> String {
        let m = Int(interval) / 60
        let s = Int(interval) % 60
        return String(format: "%d:%02d", m, s)
    }
}

/// Intelligence layer shown when tapping a transcript marker.
struct MarkerIntelligenceView: View {
    let segment: TranscriptSegment

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // Placeholder — populated from the intelligence layer
            Text("Agent observations for this segment")
                .font(.caption)
                .foregroundStyle(.secondary)
                .italic()
        }
        .padding(10)
        .background(Color.green.opacity(0.05))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }
}
