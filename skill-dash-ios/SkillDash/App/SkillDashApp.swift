import SwiftUI

@main
struct SkillDashApp: App {
    @StateObject private var store = StoreManager()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(store)
                .preferredColorScheme(.light)
                .onAppear {
                    GameCenterManager.shared.authenticate()
                }
        }
    }
}
