import LocalAuthentication

/// Face ID / Touch ID authentication for app access.
final class BiometricAuth {

    enum BiometricType {
        case faceID, touchID, none
    }

    var availableBiometric: BiometricType {
        let context = LAContext()
        var error: NSError?
        guard context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) else {
            return .none
        }
        switch context.biometryType {
        case .faceID: return .faceID
        case .touchID: return .touchID
        default: return .none
        }
    }

    func authenticate() async -> Bool {
        let context = LAContext()
        context.localizedFallbackTitle = "Enter Passcode"

        var error: NSError?
        guard context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) else {
            // Fall back to device passcode
            return await authenticateWithPasscode()
        }

        do {
            return try await context.evaluatePolicy(
                .deviceOwnerAuthenticationWithBiometrics,
                localizedReason: "Unlock LIME to access your meetings"
            )
        } catch {
            print("[LIME] Biometric auth failed: \(error)")
            return false
        }
    }

    private func authenticateWithPasscode() async -> Bool {
        let context = LAContext()
        do {
            return try await context.evaluatePolicy(
                .deviceOwnerAuthentication,
                localizedReason: "Unlock LIME to access your meetings"
            )
        } catch {
            print("[LIME] Passcode auth failed: \(error)")
            return false
        }
    }
}
