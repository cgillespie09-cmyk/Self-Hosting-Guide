import SwiftUI

struct RootView: View {
    enum Route: Hashable {
        case game
        case store
    }

    @State private var path: [Route] = []

    var body: some View {
        NavigationStack(path: $path) {
            MainMenuView(path: $path)
                .navigationDestination(for: Route.self) { route in
                    switch route {
                    case .game:
                        GameView()
                    case .store:
                        StoreView()
                    }
                }
        }
    }
}
