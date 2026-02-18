import SwiftUI

@main
struct LIMEApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(appState)
                .preferredColorScheme(.dark)
        }
    }
}

struct RootView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        Group {
            if !appState.hasCompletedOnboarding {
                OnboardingFlow()
            } else if !appState.isAuthenticated {
                BiometricPromptView()
            } else {
                MainTabView()
            }
        }
    }
}

struct MainTabView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        TabView(selection: $appState.selectedTab) {
            MeetingControlsView()
                .tabItem {
                    Image(systemName: "mic.fill")
                    Text("Capture")
                }
                .tag(AppTab.capture)

            MeetingListView()
                .tabItem {
                    Image(systemName: "list.bullet")
                    Text("Meetings")
                }
                .tag(AppTab.meetings)

            VoiceMemoListView()
                .tabItem {
                    Image(systemName: "waveform")
                    Text("Memos")
                }
                .tag(AppTab.memos)

            MemoryView()
                .tabItem {
                    Image(systemName: "brain")
                    Text("Memory")
                }
                .tag(AppTab.memory)

            SettingsView()
                .tabItem {
                    Image(systemName: "gear")
                    Text("Settings")
                }
                .tag(AppTab.settings)
        }
        .tint(.green)
    }
}

struct BiometricPromptView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        VStack(spacing: 24) {
            Image(systemName: "faceid")
                .font(.system(size: 64))
                .foregroundStyle(.secondary)

            Text("Unlock LIME")
                .font(.title2.weight(.medium))

            Button("Authenticate") {
                Task {
                    await appState.authenticate()
                }
            }
            .buttonStyle(.borderedProminent)
            .tint(.green)
        }
        .task {
            await appState.authenticate()
        }
    }
}
