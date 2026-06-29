import Foundation

enum L10n {
    static func t(_ key: String) -> String {
        NSLocalizedString(key, bundle: bundle, comment: "")
    }

    static func f(_ key: String, _ arguments: CVarArg...) -> String {
        String(format: t(key), locale: .current, arguments: arguments)
    }

    private static var bundle: Bundle {
        let baseBundle: Bundle
        #if SWIFT_PACKAGE
        baseBundle = .module
        #else
        baseBundle = .main
        #endif
        let languageCode = UserDefaults.standard.string(forKey: "kyulai.injection.languageCode")
            ?? (Locale.current.language.languageCode?.identifier == "ko" ? "ko" : "en")
        if let path = baseBundle.path(forResource: languageCode, ofType: "lproj"),
           let languageBundle = Bundle(path: path) {
            return languageBundle
        }
        return baseBundle
    }
}
