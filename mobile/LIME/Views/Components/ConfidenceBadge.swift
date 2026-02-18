import SwiftUI

/// Visual badge showing confidence percentage for low-confidence items.
/// Appears on any AI-generated content below the user's confidence threshold (default 70%).
struct ConfidenceBadge: View {
    let confidence: Double

    private var color: Color {
        switch confidence {
        case 0..<0.4: return .red
        case 0.4..<0.6: return .orange
        default: return .yellow
        }
    }

    var body: some View {
        Text("\(Int(confidence * 100))%")
            .font(.caption2.weight(.semibold).monospacedDigit())
            .foregroundStyle(color)
            .padding(.horizontal, 5)
            .padding(.vertical, 1)
            .background(color.opacity(0.15))
            .clipShape(Capsule())
    }
}
