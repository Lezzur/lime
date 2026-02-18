import CryptoKit
import Foundation

/// Zero-knowledge encryption for cloud storage.
/// User holds the key — server cannot read the data.
final class CryptoService {

    private static let keyTag = "com.lime.encryption.key"

    // MARK: - Key Management

    /// Generate a new symmetric key and store in Keychain.
    static func generateKey() throws -> SymmetricKey {
        let key = SymmetricKey(size: .bits256)
        try storeKeyInKeychain(key)
        return key
    }

    /// Retrieve the stored encryption key from Keychain.
    static func loadKey() -> SymmetricKey? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: keyTag,
            kSecReturnData as String: true
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        guard status == errSecSuccess, let data = result as? Data else {
            return nil
        }

        return SymmetricKey(data: data)
    }

    private static func storeKeyInKeychain(_ key: SymmetricKey) throws {
        let keyData = key.withUnsafeBytes { Data($0) }

        // Delete existing key if present
        let deleteQuery: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: keyTag
        ]
        SecItemDelete(deleteQuery as CFDictionary)

        // Store new key
        let addQuery: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: keyTag,
            kSecValueData as String: keyData,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        ]

        let status = SecItemAdd(addQuery as CFDictionary, nil)
        guard status == errSecSuccess else {
            throw CryptoError.keychainStoreFailed(status)
        }
    }

    // MARK: - Encryption

    /// Encrypt data using AES-GCM with the stored key.
    static func encrypt(_ data: Data) throws -> Data {
        guard let key = loadKey() else {
            throw CryptoError.noKeyAvailable
        }

        let sealedBox = try AES.GCM.seal(data, using: key)
        guard let combined = sealedBox.combined else {
            throw CryptoError.encryptionFailed
        }
        return combined
    }

    /// Decrypt data using AES-GCM with the stored key.
    static func decrypt(_ data: Data) throws -> Data {
        guard let key = loadKey() else {
            throw CryptoError.noKeyAvailable
        }

        let sealedBox = try AES.GCM.SealedBox(combined: data)
        return try AES.GCM.open(sealedBox, using: key)
    }

    // MARK: - Export / Import Key (for device transfer)

    /// Export key as a base64 string for backup or device transfer.
    static func exportKey() -> String? {
        guard let key = loadKey() else { return nil }
        return key.withUnsafeBytes { Data($0).base64EncodedString() }
    }

    /// Import a key from a base64 string.
    static func importKey(from base64: String) throws {
        guard let data = Data(base64Encoded: base64) else {
            throw CryptoError.invalidKeyData
        }
        let key = SymmetricKey(data: data)
        try storeKeyInKeychain(key)
    }
}

enum CryptoError: LocalizedError {
    case noKeyAvailable
    case encryptionFailed
    case keychainStoreFailed(OSStatus)
    case invalidKeyData

    var errorDescription: String? {
        switch self {
        case .noKeyAvailable: return "No encryption key found"
        case .encryptionFailed: return "Encryption failed"
        case .keychainStoreFailed(let status): return "Keychain store failed: \(status)"
        case .invalidKeyData: return "Invalid key data"
        }
    }
}
