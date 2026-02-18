import SwiftUI
import AVFoundation

/// First-run onboarding: name, language, wake word, gesture walkthrough, voice sample, audio setup, LLM preference.
/// Goal: user in their first meeting within 5 minutes of installing.
struct OnboardingFlow: View {
    @EnvironmentObject var appState: AppState
    @State private var step = 0
    @State private var userName = ""
    @State private var wakeWord = "Hey Lime"
    @State private var useCloudLLM = false

    private let totalSteps = 5

    var body: some View {
        VStack {
            // Progress indicator
            ProgressView(value: Double(step + 1), total: Double(totalSteps))
                .tint(.green)
                .padding(.horizontal)
                .padding(.top, 8)

            Spacer()

            Group {
                switch step {
                case 0: nameStep
                case 1: wakeWordStep
                case 2: gestureWalkthrough
                case 3: llmPreferenceStep
                case 4: completeStep
                default: EmptyView()
                }
            }
            .transition(.asymmetric(
                insertion: .move(edge: .trailing).combined(with: .opacity),
                removal: .move(edge: .leading).combined(with: .opacity)
            ))

            Spacer()

            // Navigation
            HStack {
                if step > 0 {
                    Button("Back") {
                        withAnimation { step -= 1 }
                    }
                    .foregroundStyle(.secondary)
                }

                Spacer()

                if step < totalSteps - 1 {
                    Button("Next") {
                        withAnimation { step += 1 }
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.green)
                    .disabled(step == 0 && userName.isEmpty)
                }
            }
            .padding()
        }
    }

    // MARK: - Steps

    private var nameStep: some View {
        VStack(spacing: 20) {
            Image(systemName: "person.crop.circle")
                .font(.system(size: 60))
                .foregroundStyle(.green)

            Text("What should I call you?")
                .font(.title2.weight(.medium))

            TextField("Your name", text: $userName)
                .textFieldStyle(.roundedBorder)
                .frame(maxWidth: 280)
                .multilineTextAlignment(.center)
        }
    }

    private var wakeWordStep: some View {
        VStack(spacing: 20) {
            Image(systemName: "waveform.circle")
                .font(.system(size: 60))
                .foregroundStyle(.green)

            Text("Choose your wake word")
                .font(.title2.weight(.medium))

            Text("Say this to give voice commands during meetings.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)

            TextField("Wake word", text: $wakeWord)
                .textFieldStyle(.roundedBorder)
                .frame(maxWidth: 280)
                .multilineTextAlignment(.center)

            Text("Default: \"Hey Lime\"")
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
    }

    private var gestureWalkthrough: some View {
        VStack(spacing: 24) {
            Text("Meeting Gestures")
                .font(.title2.weight(.medium))

            VStack(alignment: .leading, spacing: 16) {
                GestureRow(
                    icon: "hand.tap",
                    title: "Single Tap",
                    description: "Bookmark this moment"
                )
                GestureRow(
                    icon: "hand.tap.fill",
                    title: "Double Tap",
                    description: "Flag as high priority"
                )
                GestureRow(
                    icon: "hand.raised",
                    title: "Long Press",
                    description: "Record a voice annotation"
                )
            }
            .padding(.horizontal, 40)

            // Practice area
            ZStack {
                RoundedRectangle(cornerRadius: 16)
                    .fill(Color.black)
                    .frame(height: 120)

                Text("Try it here")
                    .font(.caption)
                    .foregroundStyle(.white.opacity(0.3))
            }
            .frame(maxWidth: 280)
            .overlay {
                CaptureGestureLayer { _ in
                    // Practice only — visual feedback is built in
                }
            }
            .clipShape(RoundedRectangle(cornerRadius: 16))
        }
    }

    private var llmPreferenceStep: some View {
        VStack(spacing: 20) {
            Image(systemName: "brain")
                .font(.system(size: 60))
                .foregroundStyle(.green)

            Text("AI Processing")
                .font(.title2.weight(.medium))

            VStack(alignment: .leading, spacing: 16) {
                PreferenceCard(
                    title: "Local (Free)",
                    description: "Processes on your computer. Good quality, no cost.",
                    isSelected: !useCloudLLM
                ) {
                    useCloudLLM = false
                }

                PreferenceCard(
                    title: "Cloud (Paid)",
                    description: "Better quality analysis. ~$0.35-0.75 per meeting.",
                    isSelected: useCloudLLM
                ) {
                    useCloudLLM = true
                }
            }
            .frame(maxWidth: 300)

            Text("You can change this anytime in Settings.")
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
    }

    private var completeStep: some View {
        VStack(spacing: 20) {
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 60))
                .foregroundStyle(.green)

            Text("Ready, \(userName).")
                .font(.title2.weight(.medium))

            Text("Start your first meeting whenever you want.")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            Button("Let's Go") {
                appState.wakeWord = wakeWord
                appState.useCloudLLM = useCloudLLM
                appState.saveSettings()
                appState.completeOnboarding()
            }
            .buttonStyle(.borderedProminent)
            .tint(.green)
            .controlSize(.large)
        }
    }
}

// MARK: - Supporting Views

struct GestureRow: View {
    let icon: String
    let title: String
    let description: String

    var body: some View {
        HStack(spacing: 16) {
            Image(systemName: icon)
                .font(.title3)
                .foregroundStyle(.green)
                .frame(width: 30)

            VStack(alignment: .leading) {
                Text(title)
                    .font(.subheadline.weight(.medium))
                Text(description)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }
}

struct PreferenceCard: View {
    let title: String
    let description: String
    let isSelected: Bool
    let onSelect: () -> Void

    var body: some View {
        Button(action: onSelect) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(title)
                        .font(.subheadline.weight(.medium))
                    Text(description)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                    .foregroundStyle(isSelected ? .green : .secondary)
            }
            .padding()
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(isSelected ? Color.green : Color.secondary.opacity(0.3), lineWidth: 1.5)
            )
        }
        .buttonStyle(.plain)
    }
}
