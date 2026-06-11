import Foundation

@MainActor
public final class AppSettings: ObservableObject {
    private let userDefaults: UserDefaults
    private let key = "kyulai.injection.apiBaseURL"

    @Published public var apiBaseURL: String {
        didSet { userDefaults.set(apiBaseURL, forKey: key) }
    }

    public init(userDefaults: UserDefaults = .standard) {
        self.userDefaults = userDefaults
        let storedValue = userDefaults.string(forKey: key)
        let initialValue = storedValue.flatMap(Self.publicURLIfStoredValueIsLocal) ?? InjectionDefaults.fallbackBaseURL
        self.apiBaseURL = initialValue
        userDefaults.set(initialValue, forKey: key)
    }

    public var parsedBaseURL: URL? {
        try? BaseURLValidator.parse(apiBaseURL)
    }

    private static func publicURLIfStoredValueIsLocal(_ value: String) -> String? {
        guard let url = URL(string: value), let host = url.host else {
            return InjectionDefaults.fallbackBaseURL
        }
        if host == "127.0.0.1" || host == "localhost" || host.hasPrefix("172.") || host.hasPrefix("192.168.") || host.hasPrefix("10.") {
            return InjectionDefaults.fallbackBaseURL
        }
        return value
    }
}
