import Foundation

@MainActor
public final class AppSettings: ObservableObject {
    private let userDefaults: UserDefaults
    private let apiBaseURLKey = "kyulai.ddLaminate.apiBaseURL"
    private let languageCodeKey = "kyulai.ddLaminate.languageCode"

    @Published public var apiBaseURL: String {
        didSet { userDefaults.set(apiBaseURL, forKey: apiBaseURLKey) }
    }

    @Published public var languageCode: String {
        didSet { userDefaults.set(languageCode, forKey: languageCodeKey) }
    }

    public init(userDefaults: UserDefaults = .standard) {
        self.userDefaults = userDefaults
        let storedValue = userDefaults.string(forKey: apiBaseURLKey)
        let initialValue = storedValue.flatMap(Self.publicURLIfStoredValueIsLocal) ?? DDLaminateDefaults.fallbackBaseURL
        self.apiBaseURL = initialValue
        self.languageCode = Self.normalizedLanguageCode(userDefaults.string(forKey: languageCodeKey))
        userDefaults.set(initialValue, forKey: apiBaseURLKey)
        userDefaults.set(languageCode, forKey: languageCodeKey)
    }

    public var parsedBaseURL: URL? {
        try? BaseURLValidator.parse(apiBaseURL)
    }

    public func toggleLanguage() {
        languageCode = languageCode == "ko" ? "en" : "ko"
    }

    private static func publicURLIfStoredValueIsLocal(_ value: String) -> String? {
        guard let url = URL(string: value), let host = url.host else {
            return DDLaminateDefaults.fallbackBaseURL
        }
        if host == "127.0.0.1" || host == "localhost" || host.hasPrefix("172.") || host.hasPrefix("192.168.") || host.hasPrefix("10.") {
            return DDLaminateDefaults.fallbackBaseURL
        }
        return value
    }

    private static func normalizedLanguageCode(_ value: String?) -> String {
        guard value == "ko" || value == "en" else {
            return Locale.current.language.languageCode?.identifier == "ko" ? "ko" : "en"
        }
        return value ?? "en"
    }
}
