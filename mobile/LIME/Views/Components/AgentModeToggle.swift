import SwiftUI

/// Quick toggle between agent personality modes.
/// Sparring partner has a prominent dial-back control per spec.
struct AgentModeToggle: View {
    @Binding var mode: AgentMode

    var body: some View {
        HStack(spacing: 0) {
            ForEach(AgentMode.allCases, id: \.self) { agentMode in
                Button {
                    withAnimation(.spring(response: 0.3)) {
                        mode = agentMode
                    }
                } label: {
                    VStack(spacing: 2) {
                        Image(systemName: icon(for: agentMode))
                            .font(.body)
                        Text(agentMode.rawValue)
                            .font(.caption2)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 8)
                    .foregroundStyle(mode == agentMode ? .white : .secondary)
                    .background(
                        mode == agentMode ? modeColor(agentMode).opacity(0.8) : Color.clear
                    )
                }
            }
        }
        .background(Color(.systemGray6))
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }

    private func icon(for mode: AgentMode) -> String {
        switch mode {
        case .scribe: return "pencil.line"
        case .thinkingPartner: return "brain.head.profile"
        case .sparringPartner: return "bolt.fill"
        }
    }

    private func modeColor(_ mode: AgentMode) -> Color {
        switch mode {
        case .scribe: return .blue
        case .thinkingPartner: return .green
        case .sparringPartner: return .red
        }
    }
}
