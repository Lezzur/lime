import SwiftUI

struct MemoryView: View {
    @EnvironmentObject var appState: AppState

    enum Tier: String, CaseIterable, Identifiable {
        case longTerm = "long-term"
        case mediumTerm = "medium-term"
        case shortTerm = "short-term"

        var id: String { rawValue }

        var label: String {
            switch self {
            case .longTerm: return "Long-term"
            case .mediumTerm: return "Medium-term"
            case .shortTerm: return "Short-term"
            }
        }

        var description: String {
            switch self {
            case .longTerm: return "Confirmed truths — ground rules that shape all outputs"
            case .mediumTerm: return "Detected patterns — signals that appear multiple times"
            case .shortTerm: return "Raw signals — corrections, edits, preferences from recent sessions"
            }
        }

        var accentColor: Color {
            switch self {
            case .longTerm: return .green
            case .mediumTerm: return .yellow
            case .shortTerm: return .blue
            }
        }
    }

    @State private var activeTier: Tier = .longTerm
    @State private var contents: [String: String] = [:]
    @State private var loading = false
    @State private var saving = false
    @State private var consolidating = false
    @State private var saved = false
    @State private var errorMessage: String?
    @FocusState private var editorFocused: Bool

    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                // Tier picker
                Picker("Memory Tier", selection: $activeTier) {
                    ForEach(Tier.allCases) { tier in
                        Text(tier.label).tag(tier)
                    }
                }
                .pickerStyle(.segmented)
                .padding(.horizontal)
                .padding(.vertical, 12)

                Divider()

                // Description
                HStack {
                    Text(activeTier.description)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Spacer()
                }
                .padding(.horizontal)
                .padding(.top, 10)
                .padding(.bottom, 4)

                // Editor
                Group {
                    if loading {
                        ProgressView()
                            .frame(maxWidth: .infinity, maxHeight: .infinity)
                    } else {
                        TextEditor(text: Binding(
                            get: { contents[activeTier.rawValue] ?? "" },
                            set: { contents[activeTier.rawValue] = $0 }
                        ))
                        .font(.system(.caption, design: .monospaced))
                        .focused($editorFocused)
                        .overlay(alignment: .topLeading) {
                            if (contents[activeTier.rawValue] ?? "").isEmpty {
                                Text("No entries yet in this memory tier.")
                                    .font(.system(.caption, design: .monospaced))
                                    .foregroundStyle(.tertiary)
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 8)
                                    .allowsHitTesting(false)
                            }
                        }
                    }
                }
                .frame(maxHeight: .infinity)

                Divider()

                // Footer
                HStack(spacing: 12) {
                    if let error = errorMessage {
                        Text(error)
                            .font(.caption2)
                            .foregroundStyle(.red)
                            .lineLimit(1)
                    } else {
                        Text("Edits are high-priority learning signals")
                            .font(.caption2)
                            .foregroundStyle(.tertiary)
                    }

                    Spacer()

                    Button {
                        Task { await saveTier() }
                    } label: {
                        HStack(spacing: 4) {
                            if saving {
                                ProgressView().controlSize(.mini)
                            } else {
                                Image(systemName: saved ? "checkmark" : "square.and.arrow.down")
                            }
                            Text(saving ? "Saving…" : saved ? "Saved" : "Save")
                        }
                        .font(.caption.weight(.medium))
                    }
                    .buttonStyle(.bordered)
                    .tint(saved ? .green : activeTier.accentColor)
                    .disabled(saving)
                }
                .padding(.horizontal)
                .padding(.vertical, 10)
            }
            .navigationTitle("Memory")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        Task { await consolidate() }
                    } label: {
                        if consolidating {
                            ProgressView().controlSize(.small)
                        } else {
                            Label("Consolidate", systemImage: "arrow.triangle.2.circlepath")
                                .font(.caption.weight(.medium))
                        }
                    }
                    .disabled(consolidating)
                }

                ToolbarItemGroup(placement: .keyboard) {
                    Spacer()
                    Button("Done") { editorFocused = false }
                }
            }
            .onChange(of: activeTier) { _ in
                Task { await loadTier() }
            }
            .task {
                await loadTier()
            }
        }
    }

    // MARK: - Actions

    private func loadTier() async {
        loading = true
        errorMessage = nil
        defer { loading = false }
        do {
            let content = try await appState.apiClient.getMemory(tier: activeTier.rawValue)
            contents[activeTier.rawValue] = content
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func saveTier() async {
        saving = true
        errorMessage = nil
        defer { saving = false }
        do {
            try await appState.apiClient.updateMemory(
                tier: activeTier.rawValue,
                content: contents[activeTier.rawValue] ?? ""
            )
            saved = true
            try? await Task.sleep(nanoseconds: 2_000_000_000)
            saved = false
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func consolidate() async {
        consolidating = true
        errorMessage = nil
        defer { consolidating = false }
        do {
            try await appState.apiClient.triggerConsolidation()
            await loadTier()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
